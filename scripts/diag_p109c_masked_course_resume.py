"""Check a native G4 mixed-course boundary on owned synthetic inputs."""

import argparse
from dataclasses import replace
from datetime import datetime
import hashlib
import json
import os
import signal
from time import time
from unittest.mock import patch

import numpy as np
import torch

from scripts import diag_p109_ntp_visit_resume as fixture
from scripts import p109_mix_masked_course as mixed
from scripts.run_p109b_scratch_pair_20261120 import idle_gpu, publish


ROOT = mixed.routed.ROOT
CUTOFF = datetime.fromisoformat("2026-11-21T12:57:00+09:00").timestamp()
STEPS, BOUNDARY = 4, 2


def source(out, width, vocab, pool):
    cache = out / "synthetic"
    cache.mkdir()
    meta = dict(data="synthetic", dir=str(cache), tokens=pool, vocab=vocab,
                train=pool * 3 // 4, val=pool // 4, token_dtype="uint16")
    publish(cache / "meta.json", meta)
    for split, seed in (("train", 1818), ("val", 1729)):
        tokens = np.random.default_rng(seed).integers(4, vocab, size=meta[split], dtype=np.uint16)
        with (cache / (split + ".bin")).open("xb") as stream:
            stream.write(tokens.tobytes())
    return meta


def examples(width, vocabulary):
    rows = []
    for index in range(6):
        x = tuple(int(value) for value in np.random.default_rng(931 + index).integers(4, vocabulary, size=width))
        y = tuple(value if pos >= width - 5 else mixed.IGNORE for pos, value in enumerate(x[1:] + (2,)))
        rows.append((x, y))
    return mixed.Course(BOUNDARY, (1,), tuple(rows), vocabulary)


def commands(tag, width, pool, resume=False):
    count = f"{pool / 1_000_000:.6f}M"
    args = ["train", "--preset", "m100s12_g4", "--arch", "tied", "--data", "synthetic",
            "--tokens", count, "--pool-tokens", count, "--exact-cache", "--steps", str(STEPS),
            "--seq", str(width), "--micro-bs", "2", "--accum", "2", "--eval-every", "2", "--save-every", "2",
            "--sched", "wsd", "--anneal-start", "0", "--optimizer", "muon", "--muon-scale", "rms",
            "--muon-lr-mult", "4", "--train-repeat", "2", "--seed", "1337", "--tag", tag,
            "--ce-recompute-rows", "64"]
    if resume:
        args.append("--resume")
    return args


def compare(out, course, width, pool):
    def checkpoint(tag):
        return out / "ckpt" / f"m100s12_g4_synthetic_{pool}_{tag}.pt"

    def state(tag):
        return torch.load(checkpoint(tag), weights_only=True, map_location="cpu", mmap=True)

    full = mixed.run_native(course, commands("p109c_course_full", width, pool))
    split = "p109c_course_split"
    original_save = torch.save

    def stop(blob, path):
        original_save(blob, path)
        if path == checkpoint(split) and blob["step"] == BOUNDARY:
            raise fixture.SplitBoundary

    with patch.object(torch, "save", stop):
        try:
            mixed.run_native(course, commands(split, width, pool))
        except fixture.SplitBoundary:
            pass
        else:
            raise AssertionError("course boundary was never saved")

    def saved_boundary_sha():
        with checkpoint(split).open("rb") as stream:
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    before = saved_boundary_sha()
    changed = replace(course, rows=tuple(reversed(course.rows)))
    try:
        mixed.run_native(changed, commands(split, width, pool, resume=True))
    except ValueError as error:
        if "context recipe/cache/source/runtime binding differs" not in str(error):
            raise
    else:
        raise AssertionError("resumed with a different course")
    if before != saved_boundary_sha():
        raise AssertionError("rejected resume wrote a checkpoint")
    resumed = mixed.run_native(course, commands(split, width, pool, resume=True))
    left, right = state("p109c_course_full"), state(split)
    if (left["step"] != right["step"] or left["step"] != STEPS
            or fixture.state_fingerprint(left) != fixture.state_fingerprint(right)
            or full["updates"][BOUNDARY:] != resumed["updates"]):
        raise AssertionError("native continued and resumed training differ across the course boundary")
    assert [row["course_input_slots"] for row in full["updates"]] == [0, 0, 2 * width, 2 * width]
    assert [row["course_supervised_targets"] for row in full["updates"]] == [0, 0, 10, 10]
    assert all(row["optimizer_applied"] for row in full["updates"])
    return dict(full_updates=full["updates"], replayed_updates=resumed["updates"],
                same_terminal_state=True, changed_course_rejected=True, boundary_sha256=before,
                course=full["course"])


def main():
    from tinylm.train import trainer
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device", choices=("cpu", "gpu"))
    gpu = parser.parse_args().device == "gpu"
    budget = 240 if gpu else 120
    if time() + budget >= CUTOFF or os.environ.get("CUDA_VISIBLE_DEVICES") != ("0" if gpu else ""):
        raise RuntimeError("selected device or approved time unavailable")
    signal.alarm(budget)
    if gpu:
        idle_gpu()
    if bool(torch.cuda.is_available()) != gpu:
        raise RuntimeError("requested device is unavailable or incorrectly isolated")
    width, vocab, pool = (128, 32768, 8192) if gpu else (16, 64, 2048)
    out = ROOT / "test_result/evidence" / f"p109c_masked_course_{'gpu' if gpu else 'cpu'}_v1_20261120"
    out.mkdir(exist_ok=False)
    meta = source(out, width, vocab, pool)
    course = examples(width, vocab)
    torch.set_num_threads(2 if gpu else 1)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    real_evaluate = trainer.evaluate

    def evaluate(model, loader, _count, device, **kwargs):
        return real_evaluate(model, loader, 2, device, **kwargs)

    with (patch.object(trainer, "CKPT", out / "ckpt"), patch.object(trainer, "LOGS", out / "logs"),
          patch.object(trainer, "prepare", return_value=meta), patch.object(trainer, "evaluate", evaluate),
          patch.object(trainer, "build_config", trainer.build_config if gpu else fixture.small_config)):
        result = compare(out, course, width, pool)
    result.update(device="cuda" if gpu else "cpu", width=width, vocab=vocab, synthetic=True,
                  peak_allocated_bytes=torch.cuda.max_memory_allocated() if gpu else None)
    publish(out / "report.json", result)
    print("MASKED_COURSE_RESUME", result["device"], result["same_terminal_state"], flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
