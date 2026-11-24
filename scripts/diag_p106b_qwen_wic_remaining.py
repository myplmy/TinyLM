"""Run only the missing official WiC task with the already pinned Qwen HF route."""

import argparse
from datetime import datetime, timezone
import gc
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

from scripts import diag_p013_native_matched_training as training
from scripts import diag_p106b_kobest_exact_followups as exact
from scripts import diag_p106b_kobest_two_remaining as previous


ROOT = previous.ROOT
TAG = "p106b_qwen_hf_kobest_wic_remaining_v1_20261118"
OUT = ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
TASK, MODEL, CAP = "kobest_wic", "qwen3508", 1130
IO = previous.IO
SHA = exact.native.digest
RAW = ROOT / "test_result/101_log_20261118_P106B_Stage8pr6Wg_two_kobest_GPU.txt"
READBACK = ROOT / "handoff/audit/research_20261118_01a1e647/KOBEST_REMAINING_CLOSED_READBACK_v1.json"


def frozen_inputs():
    profile = previous.verify()
    parent = previous.OUT / "actual.json"
    last = IO.read(parent)
    readback = IO.read(READBACK)
    assert readback["process_exit"] == 8 and not last["complete"]
    assert [line.split()[2] for line in RAW.read_text().splitlines() if line.startswith("[runlog] 종료코드 ")] == ["8"]
    assert last["models"]["gemma1b"]["accepted"] and not last["models"][MODEL]["accepted"]
    required = set(profile["native_complete_tasks"])
    pinned = {}
    for name, state in last["models"].items():
        base = previous.OUT / name / "actual"
        root = IO.read(base / "report.json")
        assert not Path(f"/proc/{root['PID']}").exists() and root["original_inputs_unchanged"]
        assert state["gpu_after_process_exit"]["competing_compute_pids"] == []
        path = base / name / "report.json"
        assert SHA(path) == state["report_sha256"]
        artifact = IO.read(path)
        done = {k: v for k,v in artifact["tasks"].items() if v["status"] == "COMPLETE"}
        assert set(done) == (required - {TASK} if name==MODEL else required)
        for task in done.values():
            exact.verify_shards(base / name, task["manifest"])
        pinned[name] = dict(report=SHA(path), tasks={k:v["manifest"]["concat_sha256"] for k,v in done.items()})
        if name==MODEL:
            missing = artifact["tasks"][TASK]
            assert missing["status"] == "COST_HOLD" and missing["rows"] == 0
            assert missing["cost"]["remaining_seconds"] < missing["cost"]["forecast_seconds"] < CAP-120
    return dict(tag=TAG,task=TASK,model=MODEL,cap=CAP,script_sha256=SHA(Path(__file__)),
        parent_profile=SHA(exact.PROFILE),partial_profile=SHA(previous.PROFILE),partial_report=SHA(parent),
        partial_raw=SHA(RAW),partial_readback=SHA(READBACK),preserved=pinned,
        native_complete_tasks=profile["native_complete_tasks"],prep_gpu_calls=0)


def verify():
    profile = IO.read(PROFILE)
    assert profile == frozen_inputs()
    return profile


def prepare():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    profile = frozen_inputs()
    exact_profile,_ = previous.original_verify()
    tasks,items,meta = exact.inputs()
    assert exact.canonical(meta) == exact.canonical(exact_profile["tasks"])
    assert TASK in tasks and len(items[TASK]) == 1260
    OUT.mkdir(exist_ok=False)
    IO.write(PROFILE,profile)
    print("QWEN_WIC_ONLY_PREPARED",SHA(PROFILE),len(items[TASK]),flush=True)


def worker():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "0"
    verify()
    profile,qp = previous.original_verify()
    tasks,items,meta = exact.inputs()
    assert exact.canonical(meta) == exact.canonical(profile["tasks"])
    entry = training.reserve_device()
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel

    output = OUT / "actual" / MODEL
    output.mkdir(exist_ok=False)
    report = dict(model=MODEL,task=TASK,pid=os.getpid(),gpu_entry=entry,training_steps=0,checkpoint_writes=0)
    torch.set_num_threads(4)
    torch.manual_seed(1337)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.cuda.reset_peak_memory_stats()
    stop = min(time.time()+CAP, exact.CUTOFF-45)
    started = time.monotonic()

    def check():
        if time.time()+18>=stop or (OUT / "STOP").exists():
            raise TimeoutError("WiC authorized window or owned STOP")

    lm = None
    try:
        with (torch.no_grad(), sdpa_kernel(SDPBackend.MATH), patch.object(exact,"TAG",TAG),
              exact.runtime(MODEL,torch,profile,qp,output,check,report) as lm):
            case = exact.evaluate(lm,TASK,tasks[TASK],items[TASK],output,check,stop)
        report.update(task_result=case,status=case["status"])
    except Exception as error:
        report.update(status="ERROR",error=dict(type=type(error).__name__,message=str(error)[:1400]))
    finally:
        lm = None
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        report.update(wall_seconds=time.monotonic()-started,allocated_bytes=torch.cuda.max_memory_allocated(),
            reserved_bytes=torch.cuda.max_memory_reserved(),allocated_before_process_exit=torch.cuda.memory_allocated(),
            reserved_before_process_exit=torch.cuda.memory_reserved())
        IO.write(output / "report.json",report)
    verify()
    print("QWEN_WIC_ONLY_WORKER",report["status"],report.get("task_result",{}).get("metrics"),flush=True)
    return 0 if report["status"] == "COMPLETE" and report["task_result"]["rows"] == 1260 else 8


def run():
    from scripts.interactive_research_infer import require_idle_gpu

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "0" and time.time()+CAP+120<exact.CUTOFF
    verify()
    entry = require_idle_gpu()
    stage = OUT / "actual"
    stage.mkdir(exist_ok=False)
    try:
        child = subprocess.run([sys.executable,"-B","-u","-m","scripts.diag_p106b_qwen_wic_remaining","worker"],
            cwd=ROOT,timeout=CAP+50)
        code = child.returncode
    except subprocess.TimeoutExpired:
        code = 124
    freed = require_idle_gpu()
    path = stage / MODEL / "report.json"
    observed = IO.read(path) if path.is_file() else None
    gone = observed is not None and not Path(f"/proc/{observed['pid']}").exists()
    complete = code==0 and gone and observed["task_result"]["rows"]==1260
    verify()
    IO.write(stage / "report.json",dict(tag=TAG,complete=complete,child_exit=code,child_gone=gone,
        child_sha256=SHA(path) if observed else None,gpu_entry=entry,gpu_after_child=freed,
        unchanged_previous_tasks=True,ended_UTC=datetime.now(timezone.utc).isoformat()))
    return 0 if complete else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","check","run","worker"))
    phase = parser.parse_args().phase
    if phase=="prepare":
        prepare()
    elif phase=="check":
        verify()
        print("QWEN_WIC_ONLY_CHECK",SHA(PROFILE),flush=True)
    else:
        raise SystemExit(worker() if phase=="worker" else run())


if __name__=="__main__":
    main()
