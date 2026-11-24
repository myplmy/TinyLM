"""Measure the owned synthetic mixed-course path at the P109C update shape."""

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import signal
from time import monotonic, time
from unittest.mock import patch

import torch

from scripts import diag_p109c_masked_course_resume as base
from scripts.run_p109b_scratch_pair_20261120 import CARD_LIMIT_MIB, file_sha, idle_gpu, publish
from tinylm.train import trainer


OUT = base.ROOT / "test_result/evidence/p109c_course_full_shape_v2_20261120"
TAG = "p109c_course_full_shape_v2_20261120"
POOL, SEQ, MICRO, ACCUM, STEPS, START = 2**21, 1024, 4, 32, 3, 1
WALL = 110


def command():
    args = base.commands(TAG, SEQ, POOL)
    for option, value in {
        "--steps": STEPS, "--micro-bs": MICRO, "--accum": ACCUM,
        "--eval-every": START, "--save-every": STEPS, "--ce-recompute-rows": SEQ,
    }.items():
        args[args.index(option) + 1] = str(value)
    return args + ["--no-ckpt"]


def profile(course):
    pins = base.mixed.routed.source_pins()
    for path in (__file__, base.__file__, base.mixed.__file__,
                 *(OUT / "synthetic" / name for name in ("meta.json", "train.bin", "val.bin"))):
        pins[str(path)] = file_sha(Path(path))
    return dict(approval="WIP191", device="single CUDA", inputs="owned synthetic", argv=command(),
                course=course.binding(), pins=pins, target_card_mib=CARD_LIMIT_MIB)


def gpu(course):
    sealed = json.loads((OUT / "profile.json").read_bytes())
    if profile(course) != sealed:
        raise ValueError("the sealed sources, fixture or update shape changed")
    total, used = idle_gpu()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    signal.alarm(WALL)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.cuda.set_per_process_memory_fraction((CARD_LIMIT_MIB - used - 512) / total)
    before = monotonic()
    torch.cuda.reset_peak_memory_stats()
    meta = json.loads((OUT / "synthetic/meta.json").read_bytes())
    real_evaluate = trainer.evaluate

    def evaluate(model, loader, _count, device, **kwargs):
        return real_evaluate(model, loader, 1, device, **kwargs)

    with (patch.object(trainer, "CKPT", OUT / "ckpt"), patch.object(trainer, "LOGS", OUT / "logs"),
          patch.object(trainer, "prepare", return_value=meta), patch.object(trainer, "evaluate", evaluate)):
        receipt = base.mixed.run_native(course, command())
    torch.cuda.synchronize()
    seconds = monotonic() - before
    updates = receipt["updates"]
    if (len(updates) != STEPS or any(not row["optimizer_applied"] for row in updates)
            or any(row["visits"] != 28 or row["draw_tokens"] != SEQ * MICRO * ACCUM for row in updates)
            or [row["course_input_slots"] for row in updates] != [0, 32 * SEQ, 32 * SEQ]
            or [row["course_supervised_targets"] for row in updates] != [0, 160, 160]
            or profile(course) != sealed):
        raise RuntimeError("update, slot or source accounting did not close")
    receipt.update(complete=True, wall_seconds=seconds, baseline_card_mib=used, total_card_mib=total,
                   allocated_bytes=torch.cuda.max_memory_allocated(), reserved_bytes=torch.cuda.max_memory_reserved(),
                   profile_sha256=file_sha(OUT / "profile.json"))
    publish(OUT / "report.json", receipt)
    print("P109C_COURSE_FULL_SHAPE_COMPLETE", receipt["allocated_bytes"], receipt["reserved_bytes"], flush=True)
    signal.alarm(0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "gpu"))
    args = parser.parse_args()
    if (time() + WALL >= base.CUTOFF
            or os.environ.get("CUDA_VISIBLE_DEVICES") != ("0" if args.phase == "gpu" else "")):
        raise RuntimeError("selected device or approved time unavailable")
    course = replace(base.examples(SEQ, 32768), start_update=START, micro_slots=tuple(range(3, ACCUM, 4)))
    if args.phase == "prepare":
        OUT.mkdir(exist_ok=False)
        base.source(OUT, SEQ, 32768, POOL)
        publish(OUT / "profile.json", profile(course))
        print("P109C_COURSE_FULL_SHAPE_SEALED", TAG, SEQ * MICRO * ACCUM, flush=True)
        return
    gpu(course)


if __name__ == "__main__":
    main()
