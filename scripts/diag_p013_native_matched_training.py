"""Use the normal TinyLM trainer for a controlled, synthetic GPU experiment."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
TAG = "p013_native_mconstant_matched_synthetic_v2_20261118"
OUT = ROOT/"test_result/evidence"/TAG
PROFILE = OUT/"profile.json"
CUTOFF = datetime.fromisoformat("2026-11-18T16:30:00+09:00").timestamp()
STEPS, MICRO, ACCUM, SEQ, POOL = 18, 8, 16, 1024, 5_000_000
MAX_ARM = 900
ARMS = {
    "fixed": ("18:1024", "muon_matched"),
    "curriculum": ("6:256,12:512,18:1024", "muon_matched"),
    "normuon": ("18:1024", "normuon_author_fp32"),
    "adamuon": ("18:1024", "adamuon_author_bf16"),
}
SOURCES = (
    "scripts/diag_p013_native_matched_training.py", "scripts/interactive_research_infer.py",
    "tinylm/cli.py", "tinylm/paths.py", "tinylm/config.py", "tinylm/training_defaults.py",
    "tinylm/data/prepare.py", "tinylm/data/loader.py", "tinylm/model/transformer.py",
    "tinylm/model/modules.py", "tinylm/model/ternary.py", "tinylm/train/trainer.py",
    "tinylm/train/context_curriculum.py", "tinylm/train/context_micro_tokens.py",
    "tinylm/train/context_training_state.py", "tinylm/train/anneal_schedule.py",
    "tinylm/train/experimental_optimizers.py", "tinylm/train/muon.py",
    "tinylm/train/normuon_author.py", "tinylm/train/adamuon_author.py",
)


def write(path,value):
    with path.open("x",encoding="utf-8") as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False)
        print(file=stream)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda:stream.read(1024**2),b""):
            h.update(part)
    return h.hexdigest().upper()


def source_pins():
    return {name:digest(ROOT/name) for name in SOURCES}


def train_args(arm):
    context, optimizer = ARMS[arm]
    return ["train","--preset","m100s10","--arch","dense","--data","synthetic","--tokens","2.359296M",
        "--pool-tokens","5M","--exact-cache","--steps",str(STEPS),"--micro-bs",str(MICRO),"--accum",str(ACCUM),
        "--seq",str(SEQ),"--lr","0.0006","--sched","cosine","--seed","1337","--eval-every","6",
        "--save-every","6","--context-curriculum",context,"--optimizer",optimizer,"--matrix-lr-mult","1.0",
        "--tag",TAG+"_"+arm]


def check_cli_arguments(name):
    from unittest.mock import patch
    from tinylm import cli
    import tinylm.train as trainer_package

    with patch.object(sys,"argv",["tinylm",*train_args(name)]), patch.object(trainer_package,"train") as called:
        cli.main()
    called.assert_called_once()
    args, kwargs = called.call_args
    assert args == ("m100s10","dense","synthetic",STEPS*MICRO*ACCUM*SEQ,STEPS,MICRO,SEQ,ACCUM,.0006,6,False,True,False)
    assert kwargs["pool_tokens"] == POOL and kwargs["exact_cache"] and kwargs["seed"] == 1337
    assert (kwargs["context_curriculum"],kwargs["optimizer"]) == ARMS[name]
    assert kwargs["matrix_lr_mult"]==1. and kwargs["init_from"] is None and kwargs["kd"] is False
    return dict(command_tokens=args[3],pool_tokens=kwargs["pool_tokens"],trainer_mocked=True)


def prepare():
    assert os.environ.get("CUDA_VISIBLE_DEVICES")==""
    OUT.mkdir(exist_ok=False)
    os.environ["TINYLM_DIR"] = str(OUT/"preflight")
    os.environ["TINYLM_HF"] = str(OUT/"preflight/HF")
    from tinylm.config import build_config
    from tinylm.train.context_micro_tokens import parse_context_plan, layout_summary
    from tinylm.train.experimental_optimizers import validate_options
    import torch

    cfg = build_config("m100s10","dense",SEQ,True)
    assert cfg.n_layers==14 and cfg.dim==768 and cfg.vocab_size==32768 and cfg.max_seq_len==SEQ and not cfg.tie_mlp
    assert POOL>=2*STEPS*MICRO*ACCUM*SEQ
    definitions = {}
    for name, (schedule,optimizer) in ARMS.items():
        plan = parse_context_plan(schedule,micro_bs=MICRO,accum=ACCUM,seq=SEQ,steps=STEPS)
        summary = layout_summary(plan)
        assert plan.tokens_per_update==131072
        assert all(row["active_accum"]==ACCUM and row["active_micro_tokens"]==8192 for row in summary["stages"])
        validate_options(optimizer,1.0)
        definitions[name] = dict(args=train_args(name),schedule=summary,cli=check_cli_arguments(name))
    assert not torch.cuda.is_initialized()
    write(PROFILE,dict(schema="P013_NATIVE_MATCHED_SYNTHETIC_PROFILE_V2",tag=TAG,
        source_pins=source_pins(), python=sys.executable,torch_version=str(torch.__version__),
        deadline_KST="2026-11-18 16:30",arms=definitions, exact_draw=STEPS*MICRO*ACCUM*SEQ,
        new_model_loads=0, GPU_calls=0, data="BUILT_IN_SYNTHETIC_GENERATOR_ONLY"))
    print("NATIVE_TRAINING_PREPARED",digest(PROFILE),flush=True)


def verify():
    profile = json.loads(PROFILE.read_bytes())
    assert profile["source_pins"]==source_pins() and profile["python"]==sys.executable
    for name in ARMS:
        assert profile["arms"][name]["args"]==train_args(name)
        assert profile["arms"][name]["cli"]["pool_tokens"]==POOL
        assert profile["arms"][name]["cli"]["command_tokens"]==STEPS*MICRO*ACCUM*SEQ
    return profile


def reserve_device():
    from scripts.interactive_research_infer import require_idle_gpu
    point = require_idle_gpu()
    reply = subprocess.check_output(["nvidia-smi","--query-gpu=memory.free","--format=csv,noheader,nounits"],
        text=True,timeout=10)
    free = int(reply.strip())
    if free < 12*1024:
        raise RuntimeError("less than the declared 12 GiB of free VRAM")
    return dict(**point,free_MiB=free)


def worker(name):
    profile = verify()
    directory = OUT/name
    assert os.environ.get("TINYLM_DIR")==str(directory)
    assert os.environ.get("TINYLM_HF")==str(directory/"HF")
    assert os.environ.get("CUDA_VISIBLE_DEVICES")=="0"
    assert not directory.exists() and time.time()+MAX_ARM+30<CUTOFF
    device = reserve_device()
    import torch
    from tinylm.cli import main

    assert profile["torch_version"]==str(torch.__version__) and torch.cuda.is_available()
    assert torch.cuda.get_device_properties(0).total_memory >= 15*1024**3
    begun = time.monotonic()
    sys.argv = ["tinylm",*train_args(name)]
    main()
    assert torch.cuda.is_initialized()
    torch.cuda.synchronize()
    logs = list((directory/"runs/logs").glob("*.json"))
    assert len(logs)==1
    result = json.loads(logs[0].read_bytes())
    limit = profile["exact_draw"]
    assert result["data"]=="synthetic" and result["n_layers"]==14 and result["params"]>50_000_000
    assert result["steps"]==STEPS and result["seq"]==SEQ and result["optimizer"]==ARMS[name][1]
    assert result["context_curriculum"] == profile["arms"][name]["schedule"]
    assert result["t1_phase_wall"]["checkpoint_writes"]>0
    cursor = result["context_source_cursor"]
    assert math.isfinite(result["final"]["val_loss"]) and result["vram_alloc_gb"]>0
    checkpoints = sorted((directory/"runs/ckpt").glob("*.pt"))
    assert len(checkpoints)==2 and sum(file.stat().st_size for file in checkpoints)<3_400_000_000
    assert source_pins()==profile["source_pins"]
    write(directory/"receipt.json",dict(tag=TAG,arm=name,exit=0,gpu_entry=device,
        profile_sha256=digest(PROFILE), training_result=str(logs[0].relative_to(ROOT)),
        result_sha256=digest(logs[0]),cursor=cursor,expected_draw=limit, steps=STEPS,
        checkpoint_bytes={file.name:file.stat().st_size for file in checkpoints},
        process_wall_seconds=time.monotonic()-begun))
    print("NATIVE_TRAINING_ARM_COMPLETE",name,result["final"]["val_loss"],result["wall_sec"],flush=True)


def run():
    profile = verify()
    assert time.time()+len(ARMS)*MAX_ARM+120<CUTOFF
    if shutil.disk_usage(OUT).free < 12*1024**3:
        raise RuntimeError("declared training output space unavailable")
    root = OUT/"actual"
    root.mkdir(exist_ok=False)
    rows = {}
    for name in ARMS:
        if time.time()+MAX_ARM+30>=CUTOFF or (OUT/"STOP").exists():
            break
        env = dict(os.environ,TINYLM_DIR=str(OUT/name),TINYLM_HF=str(OUT/name/"HF"),
            HF_HUB_OFFLINE="1",HF_DATASETS_OFFLINE="1",TRANSFORMERS_OFFLINE="1",
            WANDB_MODE="disabled",TL_WANDB_AUTO="0")
        started = time.monotonic()
        try:
            proc = subprocess.run([sys.executable,"-B","-u","-m","scripts.diag_p013_native_matched_training","worker",name],
                env=env,cwd=ROOT,timeout=MAX_ARM)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            code = 124
        path = OUT/name/"receipt.json"
        rows[name] = dict(exit=code,seconds=time.monotonic()-started,receipt_exists=path.is_file())
        print("NATIVE_TRAINING_ARM_TERMINAL",name,rows[name],flush=True)
    done = set(rows)==set(ARMS) and all(r["exit"]==0 and r["receipt_exists"] for r in rows.values())
    verify()
    write(root/"report.json",dict(tag=TAG,profile_sha256=digest(PROFILE),arms=rows,
        status="COMPLETE" if done else "PARTIAL",ended_UTC=datetime.now(timezone.utc).isoformat()))
    return 0 if done else 8


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("prepare","check","run","worker"))
    parser.add_argument("arm",nargs="?",choices=tuple(ARMS))
    args = parser.parse_args()
    if args.action=="prepare":
        prepare()
    elif args.action=="check":
        print("NATIVE_TRAINING_CHECK",len(verify()["arms"]),digest(PROFILE),flush=True)
    elif args.action=="worker":
        worker(args.arm)
    else:
        raise SystemExit(run())
