"""Fill the gap between the observed 8x16 and 32x4 warm P109 batches."""

import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import torch

from scripts import diag_p102a_p109_warm32k_device_batch as previous

TAG = "p102a_p109_warm32k_micro16_v1_20261119"
OUT = previous.OUT.with_name(TAG)
ARM = "micro16"
read, write, sha = previous.read, previous.write, previous.sha
device = previous.sampler


def current():
    profile = previous.OUT / "profile.json"
    parent_report = previous.OUT / "report.json"
    original, earlier = read(profile), read(parent_report)
    assert original["source_pins"] == previous.pins() and sha(previous.PARENT) == original["parent_sha256"]
    assert earlier["exits"] == {"micro8": 0, "micro32": 0, "micro64": None}
    assert earlier["gpu_returned"] and earlier["same_initial"] and earlier["sources_and_parent_unchanged"]
    argv = list(original["args"]["micro8"])
    for flag, value in (("--tag", TAG), ("--micro-bs", "16"), ("--accum", "8")):
        argv[argv.index(flag)+1] = value
    return dict(tag=TAG, prior_profile_sha256=sha(profile), prior_report_sha256=sha(parent_report),
                source_sha256=sha(Path(__file__)), worker=dict(original, args={ARM: argv}))


def prepare(profile):
    from tinylm import cli
    import tinylm.train as package
    assert previous.draw_receipt(16, 8) == profile["worker"]["draw"]
    with patch.object(sys, "argv", profile["worker"]["args"][ARM]), patch.object(package, "train") as stub:
        cli.main()
    stub.assert_called_once()
    args, kwargs = stub.call_args
    assert args[4:8] == (6, 16, 1024, 8) and kwargs["ce_recompute_rows"] == 1024
    OUT.mkdir(exist_ok=False)
    write(OUT / "profile.json", profile)
    return 0


def run(profile):
    assert previous.operating.previous.shapes.idle()
    raw = OUT / "device_100ms.csv"
    with raw.open("xb") as stream:
        watch = subprocess.Popen((*device.DEVICE, f"--loop-ms={device.INTERVAL_MS}"), stdout=stream)
        try:
            argv = ["timeout", "--kill-after=5s", f"{previous.CAP}s", sys.executable, "-B", "-u", "-X", "utf8", "-m",
                    "scripts.diag_p102a_p109_warm32k_mid_batch", "worker"]
            status = subprocess.run(argv, cwd=previous.ROOT, check=False).returncode
        finally:
            if watch.poll() is None:
                watch.terminate()
            watch.wait(timeout=8)
    returned = previous.operating.previous.shapes.idle()
    samples = device.read_samples(raw)
    peak = max(samples, key=lambda row: row["occupied_mib"]) if samples else None
    actual = read(OUT / f"{ARM}.json") if status == 0 else None
    reference = read(previous.OUT / "report.json")["arms"]
    match = actual is not None and actual["initial"] == reference["micro8"]["initial"]
    pinned = current() == profile
    write(OUT / "report.json", dict(exit=status, arm=actual, device=peak, device_samples=len(samples),
          device_sha256=sha(raw), same_initial=match, sources_unchanged=pinned, gpu_returned=returned))
    print("P102A_WARM32K_MICRO16_RESULT", status, peak, actual["targets_per_second"] if actual else None, flush=True)
    return 0 if status == 0 and returned and match and pinned and peak else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", "worker"))
    phase = parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if phase == "prepare" else "0")
    cutoff = previous.CUTOFF
    assert datetime.now(cutoff.tzinfo) + timedelta(seconds=previous.CAP + 25) < cutoff
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    profile = current()
    if phase == "prepare":
        assert not torch.cuda.is_initialized()
        return prepare(profile)
    assert read(OUT / "profile.json") == profile
    assert os.environ.get("PYTORCH_CUDA_ALLOC_CONF") == device.prior.ALLOCATOR
    assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8"
    from tinylm.train.context_training_state import cache_identity

    assert profile["worker"]["cache"] == cache_identity(previous.operating.CACHE)
    if phase == "worker":
        with patch.object(previous, "OUT", OUT):
            return previous.worker(ARM, profile["worker"])
    return run(profile)


if __name__ == "__main__":
    sys.exit(main())
