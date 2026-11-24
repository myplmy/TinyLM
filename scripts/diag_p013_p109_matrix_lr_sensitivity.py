"""Vary only matrix learning rate on the sealed P109 bilingual G4 panel."""

import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p013_p109_actual_optimizer as prior


TAG = "p013_p109_matrix_lr_sensitivity_v1_20261119"
REFERENCE, OUT = prior.OUT, prior.OUT.with_name(TAG)
base, read, write, sha = prior.base, prior.read, prior.write, prior.sha
ARMS = ((prior.MUON, 0.5), (prior.ADA, 2.0), (prior.MUON, 2.0), (prior.ADA, 0.5))
ORDERS = {2027: ARMS, 2039: tuple(reversed(ARMS))}
LIMIT = 510


def prepare():
    reference, *inputs = prior.prepared()
    source, result = REFERENCE / "profile.json", REFERENCE / "report.json"
    assert reference == read(source)
    previous = read(result)
    assert previous["source_preserved"] and previous["profile_sha256"] == sha(source)
    sources = dict(reference["source_sha256"])
    script = Path(__file__).relative_to(base.ROOT).as_posix()
    sources[script] = sha(Path(__file__))
    profile = dict(tag=TAG, approval="WIP176", source_sha256=sources, baseline_profile_sha256=sha(source),
        baseline_report_sha256=sha(result), order={str(k): [[m, v] for m, v in order] for k, order in ORDERS.items()},
        target_held=reference["target_held"], draw_receipts=reference["draws"], updates=reference["updates"],
        base_lr=reference["base_lr"], matrix_lr_multipliers=[0.5, 1.0, 2.0],
        nominal_1_reused=True, max_worker_seconds=LIMIT)
    return profile, reference, inputs, previous


def actual(profile, reference, inputs, previous):
    assert base.idle() and torch.cuda.device_count() == 1
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    write(OUT / "active.json", dict(pid=os.getpid(), tag=TAG))
    docs, xs, ys, held, draws = inputs
    xs, ys, held = (tensor.cuda() for tensor in (xs, ys, held))
    factory = prior.prior.build_experimental_optimizers
    device = OUT / "device_100ms.csv"
    rows = []
    with device.open("xb") as stream:
        sampler = subprocess.Popen((*base.DEVICE, f"--loop-ms={base.INTERVAL_MS}"), stdout=stream)
        try:
            with sdpa_kernel(SDPBackend.MATH):
                for seed, order in ORDERS.items():
                    ids = draws[seed].cuda()
                    for method, multiplier in order:
                        print("P109_MATRIX_LR_ARM", seed, method, multiplier, flush=True)

                        def build(model, name, *, lr, matrix_lr_mult):
                            assert name == method and lr == profile["base_lr"] and matrix_lr_mult == 1.
                            return factory(model, name, lr=lr, matrix_lr_mult=multiplier)

                        with patch.object(prior, "OUT", OUT), patch.object(prior.prior, "build_experimental_optimizers", build):
                            arm = prior.train(method, seed, docs, xs, ys, held, ids, reference)
                        old = next(v for v in previous["arms"] if v["seed"] == seed and v["method"] == method)
                        assert arm["roles_sha256"] == old["roles_sha256"]
                        assert arm["optimizer_contract_sha256"] != old["optimizer_contract_sha256"]
                        assert arm["history"][0]["loss"] == old["history"][0]["loss"]
                        arm.update(matrix_lr_mult=multiplier, nominal_matrix_lr=profile["base_lr"] * multiplier)
                        write(OUT / f"seed_{seed}_{method}_lr_{multiplier}.json", arm)
                        rows.append(arm)
                        torch.cuda.empty_cache()
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    samples = base.read_samples(device)
    assert samples and len(rows) == 8
    assert sha(prior.prior.frozen.prior.PARENT) == reference["parent_sha256"]
    assert all(sha(base.ROOT / src) == digest for src, digest in profile["source_sha256"].items())
    assert sha(REFERENCE / "report.json") == profile["baseline_report_sha256"]
    write(OUT / "report.json", dict(arms=rows, profile_sha256=sha(OUT / "profile.json"),
        source_preserved=True, checkpoint_writes=0, device_samples=len(samples),
        device_peak=max(samples, key=lambda row: row["occupied_mib"]), device_sha256=sha(device)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    phase = parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if phase == "prepare" else "0")
    assert datetime.now(base.CUTOFF.tzinfo) + timedelta(seconds=LIMIT + 20) < base.CUTOFF
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    profile, *args = prepare()
    if phase == "prepare":
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        write(OUT / "profile.json", profile)
        print("P109_MATRIX_LR_CPU", profile["order"], profile["draw_receipts"], flush=True)
    else:
        assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8"
        assert profile == read(OUT / "profile.json")
        actual(profile, *args)


if __name__ == "__main__":
    main()
