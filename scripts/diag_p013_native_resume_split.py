"""Exercise ordinary TinyLM CUDA checkpoint resume across two processes."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from unittest.mock import patch

from scripts import diag_p013_native_matched_training as reference


TAG = "p013_native_curriculum_cuda_resume_v1_20261118"
OUT = reference.OUT.parent / TAG
WORK = OUT / "split"
PROFILE = OUT / "profile.json"
BOUNDARY = OUT / "step06.pt"
STAGE_TIMEOUT = 240
SPLIT_STEP = 6


class SavedBoundary(Exception):
    """The test's planned exit after the native model and best saves finish."""


def read(path):
    return json.loads(path.read_bytes())


def args_for(phase):
    args = reference.train_args("curriculum")
    args[args.index("--tag") + 1] = TAG
    return args + (["--resume"] if phase == "resume" else [])


def pins():
    return {**reference.source_pins(),
            "scripts/diag_p013_native_resume_split.py": reference.digest(Path(__file__))}


def prepare():
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "" and not OUT.exists()
    prior = reference.verify()
    baseline_receipt = read(reference.OUT / "curriculum/receipt.json")
    baseline = reference.ROOT / baseline_receipt["training_result"]
    assert reference.digest(baseline) == baseline_receipt["result_sha256"]
    control = read(baseline)
    assert control["steps"] == 18 and control["context_resume_start_step"] == 0
    assert control["context_curriculum"] == prior["arms"]["curriculum"]["schedule"]
    OUT.mkdir()
    os.environ["TINYLM_DIR"] = str(OUT / "preflight")
    os.environ["TINYLM_HF"] = str(OUT / "preflight/HF")
    from tinylm import cli
    import tinylm.train as trainer_package
    import torch

    for phase, resume in (("boundary", False), ("resume", True)):
        with patch.object(sys, "argv", ["tinylm", *args_for(phase)]), \
                patch.object(trainer_package, "train") as train:
            cli.main()
        train.assert_called_once()
        assert train.call_args.args[3:11] == (2359296, 18, 8, 1024, 16, .0006, 6, resume)
        kwargs = train.call_args.kwargs
        assert kwargs["exact_cache"] and kwargs["pool_tokens"] == 5000000 and kwargs["seed"] == 1337
        assert kwargs["optimizer"] == "muon_matched" and kwargs["context_curriculum"] == "6:256,12:512,18:1024"
    assert not torch.cuda.is_initialized()
    reference.write(PROFILE, dict(tag=TAG, source_pins=pins(), baseline=str(baseline),
        baseline_sha256=baseline_receipt["result_sha256"],
        arguments={phase: args_for(phase) for phase in ("boundary", "resume")},
        split_step=SPLIT_STEP, steps=18, expected_updates=[6, 12],
        targets_per_update=131072, targets=2359296, pool_tokens=5000000, seed=1337,
        device="single CUDA", each_stage_timeout_seconds=STAGE_TIMEOUT,
        data="BUILT_IN_SYNTHETIC_GENERATOR_ONLY", python=sys.executable,
        torch_version=str(torch.__version__), new_model_loads=0, GPU_calls=0))
    print("P013_RESUME_PREFLIGHT_OK", reference.digest(PROFILE), flush=True)


def checked_profile():
    profile = read(PROFILE)
    assert profile["source_pins"] == pins() and profile["python"] == sys.executable
    assert reference.digest(Path(profile["baseline"])) == profile["baseline_sha256"]
    return profile


def worker(phase):
    profile = checked_profile()
    from tinylm.cli import main
    import torch

    assert os.environ["TINYLM_DIR"] == str(WORK)
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0" and profile["torch_version"] == str(torch.__version__)
    print(f"P013_RESUME_WORKER {phase} pid={os.getpid()}", flush=True)
    device = reference.reserve_device()
    assert torch.cuda.is_available()
    started = time.monotonic()
    sys.argv = ["tinylm", *profile["arguments"][phase]]
    if phase == "boundary":
        save = torch.save

        def save_and_stop(blob, path, *args, **kwargs):
            save(blob, path, *args, **kwargs)
            if blob["step"] == SPLIT_STEP and str(path).endswith("_best.pt"):
                checkpoint = path.with_name(path.name.removesuffix("_best.pt") + ".pt")
                assert checkpoint.is_file() and checkpoint.stat().st_size > 0
                with BOUNDARY.open("xb") as stream, checkpoint.open("rb") as source:
                    shutil.copyfileobj(source, stream, 8 * 1024**2)
                assert BOUNDARY.stat().st_size == checkpoint.stat().st_size
                raise SavedBoundary

        with patch.object(torch, "save", save_and_stop):
            try:
                main()
            except SavedBoundary:
                assert torch.cuda.is_initialized()
            else:
                raise RuntimeError("the planned step-six checkpoint boundary was missed")
        reference.write(OUT / "boundary.json", dict(step=SPLIT_STEP,
            retained_checkpoint=BOUNDARY.name, bytes=BOUNDARY.stat().st_size,
            sha256=reference.digest(BOUNDARY), seconds=time.monotonic()-started, gpu_entry=device))
        print("P013_RESUME_BOUNDARY_SAVED", SPLIT_STEP, flush=True)
    else:
        main()
        assert torch.cuda.is_initialized()
        torch.cuda.synchronize()
        (result_path,) = (WORK / "runs/logs").glob("*.json")
        result = read(result_path)
        assert result["context_resume_start_step"] == SPLIT_STEP
        assert result["steps"] == 18 and result["n_skip"] == 0
        assert result["context_source_cursor"]["cursor"]["optimizer_updates"] == 18
        reference.write(OUT / "resumed.json", dict(
            result=str(result_path.relative_to(reference.ROOT)), sha256=reference.digest(result_path),
            start_step=SPLIT_STEP, end_step=18, updates=12,
            seconds=time.monotonic()-started, gpu_entry=device))
        print("P013_RESUME_FINISHED", 18, result["final"]["val_loss"], flush=True)


def run():
    checked_profile()
    assert not WORK.exists() and not BOUNDARY.exists()
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0"
    assert time.time() + 2 * STAGE_TIMEOUT + 45 < reference.CUTOFF
    assert shutil.disk_usage(OUT).free >= 6 * 1024**3
    if (OUT / "STOP").exists():
        return 8
    env = dict(os.environ, TINYLM_DIR=str(WORK), TINYLM_HF=str(WORK / "HF"),
               HF_HUB_OFFLINE="1", HF_DATASETS_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
               WANDB_MODE="disabled", TL_WANDB_AUTO="0")
    codes = {}
    for phase in ("boundary", "resume"):
        if (OUT / "STOP").exists():
            break
        try:
            codes[phase] = subprocess.run([sys.executable, "-B", "-u", "-m",
                "scripts.diag_p013_native_resume_split", phase], cwd=reference.ROOT,
                env=env, timeout=STAGE_TIMEOUT).returncode
        except subprocess.TimeoutExpired:
            codes[phase] = 124
        print("P013_RESUME_PHASE_TERMINAL", phase, codes[phase], flush=True)
        if codes[phase]:
            break
    checked_profile()
    complete = codes == {"boundary": 0, "resume": 0}
    reference.write(OUT / "terminal.json", dict(phase_exits=codes, complete=complete,
        profile_sha256=reference.digest(PROFILE)))
    return 0 if complete else 8


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", "boundary", "resume"))
    phase = parser.parse_args().phase
    if phase == "prepare":
        prepare()
    elif phase == "run":
        raise SystemExit(run())
    else:
        worker(phase)
