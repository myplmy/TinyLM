"""Execute this authorized pair of preflighted experiments on one CUDA device."""

import argparse
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
import time

from scripts import diag_p013_native_matched_training as contract


ROOT = contract.ROOT
OUT = ROOT / "handoff/audit/research_20261118_01a1e647"
PROFILE = OUT / "GPU_SERIAL_P013_P014E_PROFILE_v1.json"
TERMINAL = OUT / "GPU_SERIAL_P013_P014E_TERMINAL_v1.json"
STOP = OUT / "GPU_SERIAL_P013_P014E_STOP"
DAY = "20261118"
JOBS = (
    ("106", "P013_Stage5We_determinism_switch_GPU", "scripts.diag_p013_native_determinism_switch",
     "p013_native_curriculum_cuda_repro_resume_v1_20261118", ("profile.json","switch.json"), 760),
    ("99", "P014E_Stage6Wl_g270_paired_head_GPU", "scripts.diag_p014e_g270_paired_head_cost",
     "p014e_g270_paired_head_cost_v1_20261118", ("profile.json",), 150),
)


def now():
    return datetime.now(timezone.utc).isoformat()


def job_specs():
    specs = []
    for num,name,module,tag,files,seconds in JOBS:
        stage = ROOT / "test_result/evidence" / tag
        assert not (stage/"terminal.json").exists()
        raw = ROOT / "test_result" / f"{num}_log_{DAY}_{name}.txt"
        assert not raw.exists()
        pins = {str(stage/f):contract.digest(stage/f) for f in files}
        argv = [sys.executable,"-B","-X","utf8","scripts/runlog.py","--num",num,"--name",name,
                "--","timeout","--signal=INT","--kill-after=20s",f"{seconds}s",
                sys.executable,"-B","-u","-X","utf8","-m",module,"run"]
        specs.append(dict(tag=tag,module=module,profile_pins=pins,timeout_seconds=seconds,
            raw=str(raw),state=str(stage/"terminal.json"),argv=argv))
    return specs


def prepare():
    assert os.environ["CUDA_VISIBLE_DEVICES"]==""
    assert not TERMINAL.exists() and not STOP.exists()
    contract.write(PROFILE,dict(jobs=job_specs(),own_sha256=contract.digest(ROOT/
        "scripts/run_p013_p014e_gpu_followups_20261118.py"), KST_cutoff="2026-11-18T16:30:00+09:00",
        launched_GPU_jobs=0, single_GPU=True, retries=0, concurrent_GPU=0))
    print("GPU_SERIAL_READY",contract.digest(PROFILE),flush=True)


def safe_device():
    deadline = time.monotonic()+20
    while True:
        try:
            return contract.reserve_device()
        except RuntimeError:
            if STOP.exists() or time.monotonic()>=deadline:
                raise
            time.sleep(1)


def run():
    assert os.environ["CUDA_VISIBLE_DEVICES"]=="0"
    assert not TERMINAL.exists() and not STOP.exists()
    p = json.loads(PROFILE.read_bytes())
    name = ROOT / "scripts/run_p013_p014e_gpu_followups_20261118.py"
    assert contract.digest(name)==p["own_sha256"] and job_specs()==p["jobs"]
    start = now()
    rows=[]
    failure=None
    print(f"GPU_SERIAL_PARENT pid={os.getpid()}",flush=True)
    try:
        for index,job in enumerate(p["jobs"]):
            remaining = p["jobs"][index:]
            if STOP.exists() or time.time()+sum(x["timeout_seconds"]+22 for x in remaining)+40>=contract.CUTOFF:
                failure="STOP_OR_CUTOFF"
                break
            device=safe_device()
            if STOP.exists():
                failure="STOP"
                break
            row=dict(tag=job["tag"],started_UTC=now(),entry=device,raw=job["raw"],state=job["state"])
            rows.append(row)
            print("GPU_SERIAL_START",job["tag"],row["started_UTC"],flush=True)
            proc=subprocess.run(job["argv"],cwd=ROOT)
            row.update(exit=proc.returncode,ended_UTC=now())
            print("GPU_SERIAL_TERMINAL",job["tag"],row["exit"],row["ended_UTC"],flush=True)
        release=safe_device()
    except (RuntimeError,OSError,KeyboardInterrupt) as exc:
        failure=f"{type(exc).__name__}: {exc}"
        release=None
    complete=failure is None and len(rows)==len(p["jobs"]) and all(r["exit"]==0 for r in rows)
    contract.write(TERMINAL,dict(complete=complete,exit=0 if complete else 8,rows=rows,
        start_UTC=start,end_UTC=now(),failure=failure,last_release=release,
        profile_sha256=contract.digest(PROFILE)))
    return 0 if complete else 8


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("prepare","run"))
    if parser.parse_args().action=="prepare":
        prepare()
    else:
        raise SystemExit(run())
