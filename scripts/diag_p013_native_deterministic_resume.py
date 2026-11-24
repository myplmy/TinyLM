"""Compare strict deterministic CUDA training with and without a process restart."""

import argparse
import importlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from unittest.mock import patch

from scripts import diag_p013_native_resume_split as experiment


reference = experiment.reference
TAG = "p013_native_curriculum_cuda_deterministic_resume_v1_20261118"
OUT = reference.OUT.parent / TAG
CONTINUOUS = OUT / "continuous"
PHASES = ("continuous", "boundary", "resume")
WORKSPACE = ":4096:8"
STAGE_SECONDS = 240

original_pins = experiment.pins
experiment.TAG = TAG
experiment.OUT = OUT
experiment.WORK = OUT / "split"
experiment.PROFILE = OUT / "profile.json"
experiment.BOUNDARY = OUT / "step06.pt"


def pins():
    name = "scripts/diag_p013_native_deterministic_resume.py"
    return {**original_pins(), name: reference.digest(reference.ROOT / name)}


experiment.pins = pins


def args_continuous():
    args = experiment.args_for("boundary")
    args[args.index("--tag") + 1] = TAG.replace("_resume_", "_continuous_")
    return args


def prepare():
    experiment.prepare()
    reference.write(OUT / "deterministic.json", dict(profile_sha256=reference.digest(experiment.PROFILE),
        tag=TAG, continuous_arguments=args_continuous(), phase_order=PHASES,
        deterministic_algorithms=True, warn_only=False, cudnn_benchmark=False,
        cudnn_sdpa=False, cublas_workspace=WORKSPACE, minimum_disk_gib=7, gpu_calls=0))
    print("P013_DETERMINISTIC_PREFLIGHT", reference.digest(OUT / "deterministic.json"), flush=True)


def verify():
    profile = experiment.checked_profile()
    mode = experiment.read(OUT / "deterministic.json")
    assert mode["profile_sha256"] == reference.digest(experiment.PROFILE)
    assert mode["continuous_arguments"] == args_continuous() and mode["cublas_workspace"] == WORKSPACE
    assert mode["phase_order"] == list(PHASES)
    assert profile["source_pins"] == pins()
    return mode


def continuous(mode, torch):
    from tinylm.cli import main

    assert os.environ["TINYLM_DIR"] == str(CONTINUOUS)
    print(f"P013_RESUME_WORKER continuous pid={os.getpid()}", flush=True)
    device = reference.reserve_device()
    start = time.monotonic()
    sys.argv = ["tinylm", *mode["continuous_arguments"]]
    main()
    torch.cuda.synchronize()
    (path,) = (CONTINUOUS / "runs/logs").glob("*.json")
    data = experiment.read(path)
    assert data["steps"] == 18 and data["context_resume_start_step"] == 0 and data["n_skip"] == 0
    assert data["context_source_cursor"]["cursor"]["optimizer_updates"] == 18
    reference.write(OUT / "continuous.json", dict(result=str(path.relative_to(reference.ROOT)),
        sha256=reference.digest(path), updates=18, seconds=time.monotonic()-start, gpu_entry=device))
    print("P013_DETERMINISTIC_CONTINUOUS_FINISHED", data["final"]["val_loss"], flush=True)


def worker(phase):
    mode = verify()
    assert os.environ["CUBLAS_WORKSPACE_CONFIG"] == WORKSPACE
    import torch

    trainer = importlib.import_module("tinylm.train.trainer")
    build = trainer.build_config
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.enable_cudnn_sdp(False)

    def configure(*args, **kwargs):
        # The common trainer enables benchmark mode before it builds the model.
        torch.backends.cudnn.benchmark = False
        assert torch.are_deterministic_algorithms_enabled()
        assert torch.backends.cudnn.deterministic and not torch.backends.cuda.cudnn_sdp_enabled()
        return build(*args, **kwargs)

    with patch.object(trainer, "build_config", configure):
        if phase == "continuous":
            continuous(mode, torch)
        else:
            experiment.worker(phase)


def run():
    verify()
    assert not (experiment.WORK.exists() or CONTINUOUS.exists())
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0"
    assert time.time() + len(PHASES) * STAGE_SECONDS + 60 < reference.CUTOFF
    assert shutil.disk_usage(OUT).free >= 7 * 1024**3
    codes = {}
    for phase in PHASES:
        if (OUT / "STOP").exists():
            break
        work = CONTINUOUS if phase == "continuous" else experiment.WORK
        env = dict(os.environ, TINYLM_DIR=str(work), TINYLM_HF=str(work / "HF"),
                   HF_HUB_OFFLINE="1", HF_DATASETS_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                   WANDB_MODE="disabled", TL_WANDB_AUTO="0", CUBLAS_WORKSPACE_CONFIG=WORKSPACE)
        try:
            codes[phase] = subprocess.run([sys.executable, "-B", "-u", "-m",
                "scripts.diag_p013_native_deterministic_resume", phase], cwd=reference.ROOT,
                env=env, timeout=STAGE_SECONDS).returncode
        except subprocess.TimeoutExpired:
            codes[phase] = 124
        print("P013_RESUME_PHASE_TERMINAL", phase, codes[phase], flush=True)
        if codes[phase]:
            break
    verify()
    complete = codes == dict.fromkeys(PHASES, 0)
    reference.write(OUT / "terminal.json", dict(phase_exits=codes, complete=complete,
        deterministic_profile_sha256=reference.digest(OUT / "deterministic.json")))
    return 0 if complete else 8


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", *PHASES))
    phase = parser.parse_args().phase
    if phase == "prepare":
        prepare()
    elif phase == "run":
        raise SystemExit(run())
    else:
        worker(phase)
