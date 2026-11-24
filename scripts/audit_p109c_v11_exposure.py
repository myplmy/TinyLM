"""Recount format signals on the admitted P109C raw source windows."""

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from scripts import diag_p109_first_pass_planned_exposure as precedent
from scripts import eval_p109c_completed as evaluation
from scripts import run_p109c_scratch330 as training


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-record", required=True, type=Path)
    parser.add_argument("--training-manifest-sha256", required=True)
    parser.add_argument("--record", required=True, type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    parent = evaluation.training_input(args.training_record.absolute(), args.training_manifest_sha256)
    cache = parent["cache"]
    source = evaluation.regular_file(Path(cache["cache_dir"]) / "train.bin")
    stamp = training.file_stamp(source)
    source_sha = evaluation.core6.digest(source)
    if source_sha != cache["files"]["train.bin"]["sha256"]:
        raise ValueError("the admitted raw cache changed")
    data = np.memmap(source, mode="r", dtype="<u2")
    tokenizer = evaluation.load_tokenizer()
    if len(data) != parent["train_pool"]:
        raise ValueError("the actual raw cache length differs")

    update_count = parent["updates"]
    keep = np.ones((update_count, training.ACCUM), dtype=bool)
    for layout in (parent["plain"], parent["all_axes"]["layout"]):
        keep[layout["start_update"]:, layout["micro_slots"]] = False
    # The native Loader advances once per full microbatch, including a draw
    # replaced by a course row later in CourseCursor.prepare().
    rng = np.random.default_rng(precedent.SEED)
    offsets = np.asarray([rng.integers(0, len(data) - training.WIDTH - 1, training.MICRO)
                         for _ in range(update_count * training.ACCUM)])
    offsets = offsets[keep.reshape(-1)].reshape(-1)
    if len(offsets) * training.WIDTH != parent["ordinary_slots"]:
        raise ValueError("the actual course replacements differ from the planned raw target count")
    output = args.record.absolute()
    output.mkdir(exist_ok=False)
    counts = precedent.audit(data, tokenizer, offsets, started + 1800.)
    if training.file_stamp(source) != stamp:
        raise ValueError("the admitted raw cache changed during the read")
    earlier = evaluation.read_json(precedent.OUT / "report.json")
    measures = {}
    for signal in ("standalone_heading_lines", "within_segment_repeated_line_extras"):
        measures[signal] = dict(
            p109b_windows=earlier["windows_with_signal"].get(signal, 0),
            p109b_total=earlier["crop_windows"],
            p109c_windows=counts["windows_with_signal"].get(signal, 0),
            p109c_total=len(offsets),
        )
    training.publish(output / "report.json", dict(
        status="FULL_PLANNED_RAW_CROP_AUDIT", training_manifest_sha256=parent["manifest_sha256"],
        train_sha256=source_sha, tokenizer_sha256=evaluation.TOKENIZER_SHA, raw_windows=len(offsets),
        raw_target_slots=len(offsets)*training.WIDTH, replaced_course_slots=parent["course_slots"],
        offset_sha256=hashlib.sha256(offsets.astype("<i8").tobytes()).hexdigest().upper(),
        detector_sha256=evaluation.core6.digest(precedent.SCANNER),
        previous_report_sha256=evaluation.core6.digest(precedent.OUT / "report.json"),
        elapsed_seconds=time.monotonic()-started, comparison=measures, **counts,
    ))
    print("P109C_RAW_CROP_FORMAT", measures, flush=True)


if __name__ == "__main__":
    main()
