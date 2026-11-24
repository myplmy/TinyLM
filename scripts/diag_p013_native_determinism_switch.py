"""Isolate the strict PyTorch determinism switch in the P013 CUDA resume pair."""

import argparse
import importlib
import os
import shutil
import subprocess
import sys
import time
from unittest.mock import patch

from scripts import diag_p013_native_deterministic_resume as strict


split = strict.experiment
reference = strict.reference
TAG = "p013_native_curriculum_cuda_repro_resume_v1_20261118"
OUT = strict.OUT.parent / TAG
CONTINUOUS = OUT / "continuous"
MODE = OUT / "switch.json"
STRICT_RESULT = strict.OUT / "readback.json"
CAP = strict.STAGE_SECONDS

strict.TAG = TAG
strict.OUT = OUT
strict.CONTINUOUS = CONTINUOUS
split.TAG = TAG
split.OUT = OUT
split.WORK = OUT / "split"
split.BOUNDARY = OUT / "step06.pt"
split.PROFILE = OUT / "profile.json"


def pins():
    name = "scripts/diag_p013_native_determinism_switch.py"
    return {**strict.pins(), name: reference.digest(reference.ROOT / name)}


split.pins = pins


def prepare():
    control = split.read(STRICT_RESULT)
    assert control["bitwise_model_equal"] and not any(
        group["tensors_bit_different"] for group in control["group_comparison"].values())
    split.prepare()
    reference.write(MODE, dict(profile_sha256=reference.digest(split.PROFILE),
        strict_control_sha256=reference.digest(STRICT_RESULT), continuous_arguments=strict.args_continuous(),
        cublas_workspace=strict.WORKSPACE, cudnn_benchmark=False, cudnn_sdpa=False,
        cudnn_deterministic=True, deterministic_algorithms=False,
        phase_order=strict.PHASES, stage_wall_cap=CAP))
    print("P013_DETERMINISM_SWITCH_READY",reference.digest(MODE),flush=True)


def verify():
    split.checked_profile()
    mode=split.read(MODE)
    assert mode["profile_sha256"]==reference.digest(split.PROFILE)
    assert mode["strict_control_sha256"]==reference.digest(STRICT_RESULT)
    assert mode["continuous_arguments"]==strict.args_continuous()
    assert mode["phase_order"]==list(strict.PHASES)
    return mode


def worker(phase):
    mode=verify()
    assert os.environ["CUBLAS_WORKSPACE_CONFIG"]==strict.WORKSPACE
    import torch

    trainer=importlib.import_module("tinylm.train.trainer")
    build=trainer.build_config
    torch.use_deterministic_algorithms(False)
    torch.backends.cudnn.deterministic=True
    torch.backends.cuda.enable_cudnn_sdp(False)

    def configure(*args,**kwargs):
        torch.backends.cudnn.benchmark=False
        assert not torch.are_deterministic_algorithms_enabled()
        assert torch.backends.cudnn.deterministic and not torch.backends.cuda.cudnn_sdp_enabled()
        return build(*args,**kwargs)

    with patch.object(trainer,"build_config",configure):
        if phase=="continuous":
            strict.continuous(mode,torch)
        else:
            split.worker(phase)


def run():
    verify()
    assert os.environ["CUDA_VISIBLE_DEVICES"]=="0"
    assert not CONTINUOUS.exists() and not split.WORK.exists()
    assert shutil.disk_usage(OUT).free>=7*1024**3
    assert time.time()+len(strict.PHASES)*CAP+60<reference.CUTOFF
    codes={}
    for phase in strict.PHASES:
        if (OUT/"STOP").exists():
            break
        scope=CONTINUOUS if phase=="continuous" else split.WORK
        env=dict(os.environ,TINYLM_DIR=str(scope),TINYLM_HF=str(scope/"HF"),WANDB_MODE="disabled",
            HF_HUB_OFFLINE="1",HF_DATASETS_OFFLINE="1",TRANSFORMERS_OFFLINE="1",
            CUBLAS_WORKSPACE_CONFIG=strict.WORKSPACE)
        try:
            codes[phase]=subprocess.run([sys.executable,"-B","-u","-m",
                "scripts.diag_p013_native_determinism_switch",phase],
                env=env,cwd=reference.ROOT,timeout=CAP).returncode
        except subprocess.TimeoutExpired:
            codes[phase]=124
        print("P013_RESUME_PHASE_TERMINAL",phase,codes[phase],flush=True)
        if codes[phase]:
            break
    verify()
    complete=codes==dict.fromkeys(strict.PHASES,0)
    reference.write(OUT/"terminal.json",dict(phase_exits=codes,complete=complete,switch_sha256=reference.digest(MODE)))
    return 0 if complete else 8


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","run",*strict.PHASES))
    phase=parser.parse_args().phase
    if phase=="prepare":
        prepare()
    elif phase=="run":
        raise SystemExit(run())
    else:
        worker(phase)
