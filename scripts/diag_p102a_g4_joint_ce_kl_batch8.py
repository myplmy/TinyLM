"""Measure 248K G4 8x1 with the same target stream as the recorded 4x2 run."""

import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path
import subprocess
import sys

import torch

from scripts import diag_p102a_g4_joint_ce_kl_host_capacity as capacity


prior, joint, host = capacity.prior, capacity.joint, capacity.host
read, write, sha = capacity.read, capacity.write, capacity.sha
TAG = "p102a_g4_joint_ce_kl_batch8_v1_20261119"
OUT = capacity.OUT.with_name(TAG)
SELF = "scripts/diag_p102a_g4_joint_ce_kl_batch8.py"
LIMIT = 70
INTERVAL_MS = 100
DEVICE = ("nvidia-smi", "--id=0", "--query-gpu=timestamp,memory.total,memory.free",
          "--format=csv,noheader,nounits")


def batch8(original):
    grouped = []
    for group in original:
        x, y = zip(*group, strict=True)
        grouped.append([(torch.cat(x), torch.cat(y))])
    assert all(len(group) == 1 and group[0][0].shape == (8, prior.WIDTH) for group in grouped)
    assert capacity.ordered_tokens_sha(original) == capacity.ordered_tokens_sha(grouped)
    return grouped


def prepare(bank, provenance, original, grouped):
    parent = capacity.contract(bank, provenance, original, capacity.merge_micros(original))
    earlier_profile, earlier_report = capacity.OUT / "profile.json", capacity.OUT / "report.json"
    assert parent == read(earlier_profile)
    reference = read(earlier_report)
    assert reference["exits"] == {"cuda": 0, "pinned": 0} and all(reference["comparisons"].values())
    assert reference["gpu_returned"] and reference["sources_unchanged"]
    return dict(tag=TAG, previous=parent, previous_profile_sha256=sha(earlier_profile),
                previous_result_sha256=sha(earlier_report), runner_sha256=sha(prior.ROOT / SELF),
                ordered_tokens_sha256=capacity.ordered_tokens_sha(grouped),
                grouped_sha256=prior.state_sha(grouped), micro_bs=8, accum=1,
                target_total_device_gb=[12, 13], sample_ms=INTERVAL_MS,
                max_worker_s=LIMIT, approval="WIP176 + 사용자 12~13GB 운용 목표")


def read_samples(path):
    samples = []
    for line in path.read_text().splitlines():
        stamp, total, free = [cell.strip() for cell in line.split(",")]
        samples.append(dict(timestamp=stamp, total_mib=int(total), free_mib=int(free),
                            occupied_mib=int(total) - int(free)))
    return samples


def run(profile):
    assert prior.idle()
    raw = OUT / "device_100ms.csv"
    before = subprocess.check_output(DEVICE, text=True, timeout=8)
    with raw.open("xb") as stream:
        sampler = subprocess.Popen((*DEVICE, f"--loop-ms={INTERVAL_MS}"), stdout=stream)
        try:
            argv = ["timeout", "--kill-after=5s", f"{LIMIT}s", sys.executable, "-B", "-u", "-X", "utf8", "-m",
                    "scripts.diag_p102a_g4_joint_ce_kl_batch8", "worker"]
            process = subprocess.run(argv, cwd=prior.ROOT, check=False)
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    returned = prior.idle()
    after = subprocess.check_output(DEVICE, text=True, timeout=8)
    samples = read_samples(raw)
    peak = max(samples, key=lambda row: row["occupied_mib"]) if samples else None
    reference = read(capacity.OUT / "report.json")["arms"]["cuda"]
    actual = read(OUT / "chunk_sum.json") if process.returncode == 0 else None
    same = (profile["runner_sha256"] == sha(prior.ROOT / SELF)
            and profile["previous_result_sha256"] == sha(capacity.OUT / "report.json"))
    speed = None
    if actual is not None:
        speed = {key: prior.BATCH*prior.MICROS*prior.WIDTH / value["median_seconds_after_first"]
                 for key, value in (("reference_4x2", reference), ("gpu_8x1", actual))}
        assert actual["initial"] == reference["initial"]
        assert all(event["targets"] == 4096 for event in actual["history"])
    ok = process.returncode == 0 and bool(samples) and returned and same
    write(OUT / "report.json", dict(exit=process.returncode, reference_4x2=reference, gpu_8x1=actual,
          device_samples=len(samples), peak_device=peak, device_before=before.strip(), device_after=after.strip(),
          sample_sha256=sha(raw), gpu_returned=returned, sources_unchanged=same, targets_per_second=speed))
    print("P102A_G4_BATCH8_RESULT", process.returncode, len(samples), peak, speed, returned, flush=True)
    return 0 if ok else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", "worker"))
    phase = parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if phase == "prepare" else "0")
    deadline = prior.warm.CUTOFF
    assert datetime.now(deadline.tzinfo) + timedelta(seconds=LIMIT + 20) < deadline
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    bank, provenance = prior.frozen_logits(torch)
    original = prior.crops()
    grouped = batch8(original)
    profile = prepare(bank.float(), provenance, original, grouped)
    if phase == "prepare":
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        write(OUT / "profile.json", profile)
        print("P102A_G4_BATCH8_PREPARED", profile["ordered_tokens_sha256"], flush=True)
        return 0
    assert os.environ.get("PYTORCH_CUDA_ALLOC_CONF") == prior.ALLOCATOR
    assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8"
    assert read(OUT / "profile.json") == profile
    if phase == "worker":
        return joint.worker(host.REFERENCE_ARM, bank.float(), grouped, out=OUT, teacher_storage="cuda") or 0
    return run(profile)


if __name__ == "__main__":
    sys.exit(main())
