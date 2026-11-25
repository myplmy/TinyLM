"""Recount actual v3 course answer lengths and CE weight from the frozen update journal."""

from argparse import ArgumentParser
from collections import Counter, defaultdict
from datetime import datetime
import json
from math import fsum, isclose
import os
from pathlib import Path
from time import time

import numpy as np

from scripts import diag_p109c_v3_rule_flip as v3
from scripts import run_p109c_integrated_scratch as integrated


OUTPUT = v3.EVIDENCE / "p109c_v3_answer_length_exposure_20261126.json"
END = datetime.fromisoformat("2026-11-26T06:45:00+09:00")
THRESHOLDS = (8, 12, 32, 64, 128)


def lengths(row, segments):
    starts = np.flatnonzero(row == 1)
    ends = np.flatnonzero(row == 3)
    if (len(starts) != len(ends) or np.any(ends <= starts) or np.any(starts[1:] <= ends[:-1])
            or np.any(segments[starts] <= 0) or not np.array_equal(segments[starts], segments[ends])):
        raise ValueError("a positive answer crossed a segment or lacks a terminal target")
    out = ends - starts
    if int(np.count_nonzero(row == 2)) != int(out.sum()) - len(out):
        raise ValueError("the answer body and the positive masks do not account for identical positions")
    return out


def totals(histogram):
    count = histogram.total()
    tokens = sum(length * uses for length, uses in histogram.items())
    if not count:
        raise ValueError("the archived course group has no positive answers")
    thresholds = {str(k): dict(exposures=sum(uses for length, uses in histogram.items() if length >= k),
                              content_tokens=sum(length * uses for length, uses in histogram.items() if length >= k))
                  for k in THRESHOLDS}
    cumulative = 0
    percentiles = {}
    for length, uses in sorted(histogram.items()):
        cumulative += uses
        for percentile in (50, 90, 95, 99):
            if percentile not in percentiles and cumulative * 100 >= percentile * count:
                percentiles[percentile] = length
    return dict(answers=count, content_targets=tokens, mean=tokens/count, max=max(histogram),
                percentile=percentiles, at_least=thresholds, histogram=dict(sorted(histogram.items())))


def measure(deadline):
    v3.checkpoint()
    profile, bundle, slots, policy = integrated.prepare("original", "capped", "proportional", 0., True)
    journal_path = v3.TRAINING / "updates.jsonl"
    journal = [json.loads(line) for line in journal_path.read_bytes().splitlines()]
    archived = v3.completed.read_json(v3.TRAINING / "training.json")
    if len(journal) != profile["steps"] or journal != archived["updates"]:
        raise ValueError("the completed native course exposure records differ")
    manifest_names = [lane["name"] for lane in bundle.manifest["lanes"]]
    if slots.lane != len(manifest_names) + 1 or len(bundle.data) != slots.lane + 1:
        raise ValueError("the course partition needs the admitted original, packed relation and bilingual lanes")
    sizes = defaultdict(Counter)
    first_mass, body_mass, stop_mass = [], [], []
    long_first_mass, long_body_mass, long_stop_mass = [], [], []
    for address, order in enumerate(bundle.schedule):
        if time() >= deadline:
            raise TimeoutError("the frozen CPU audit reached its authorized return time")
        row_counts = Counter()
        for lane, index in order[order[:, 0] >= 0]:
            _, _, batch = integrated.supervised.course_microbatch(bundle, slots, address, lane, index)
            for index, (kind, segment) in enumerate(zip(batch.kinds, batch.segments, strict=True)):
                values = lengths(kind, segment)
                if lane == slots.lane:
                    name = "paired_ko" if index % 2 == 0 else "paired_en"
                elif lane == slots.lane - 1:
                    name = "packed_relation"
                else:
                    name = manifest_names[lane]
                sizes[name].update(map(int, values))
                row_counts.update(map(int, values))
        exposure = journal[address]
        all_answers, all_body = row_counts.total(), sum((length - 1) * count for length, count in row_counts.items())
        expected = tuple(exposure[key] for key in ("answer_start_targets", "answer_body_targets", "answer_eot_targets"))
        if (not exposure["optimizer_applied"] or exposure["index"] != address
                or expected != (all_answers, all_body, all_answers)):
            raise ValueError(f"the actual positive targets differ at update {address}")
        long_answers = sum(count for length, count in row_counts.items() if length >= 12)
        long_body = sum((length - 1) * count for length, count in row_counts.items() if length >= 12)
        first, body, stop = exposure["answer_weights"]
        if not isclose(first*all_answers + body*all_body + stop*all_answers, policy.course[address], abs_tol=1e-12):
            raise ValueError(f"the actual CE weighting differs at update {address}")
        first_mass.append(first * all_answers)
        body_mass.append(body * all_body)
        stop_mass.append(stop * all_answers)
        long_first_mass.append(first * long_answers)
        long_body_mass.append(body * long_body)
        long_stop_mass.append(stop * long_answers)
    bundle.unchanged()
    total = Counter()
    for group in sizes.values():
        total.update(group)
    roles = [fsum(items) for items in (first_mass, body_mass, stop_mass)]
    long_roles = [fsum(items) for items in (long_first_mass, long_body_mass, long_stop_mass)]
    result = totals(total)
    if result["answers"] != profile["totals"]["answers"][0]:
        raise ValueError("the positive answer denominator disagrees with the original seal")
    return dict(status="COMPLETE_READ_ONLY_EXPOSURE", checkpoint_sha256=v3.CHECKPOINT_SHA256,
                journal_sha256=v3.file_sha(journal_path), audit_source_sha256=v3.file_sha(Path(__file__)),
                layout=profile["signature"]["layout"], counted_updates=len(journal), all=result,
                groups={name: totals(rows) for name, rows in sizes.items() if rows},
                ce_weight=dict(roles=["first", "body_after_first", "eot"], all=roles, at_least_12=long_roles,
                               long_share=sum(long_roles)/sum(roles)),
                interpretation="Positive tokenized answer exposures including the first token and excluding EOT. "
                               "CE coefficient totals are not gradient magnitudes or unique responses.")


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if (args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= END
            or os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
        parser.error("use CPU 14 and the approved cutoff without a device")
    result = measure(args.stop_by.timestamp())
    integrated.native.publish(OUTPUT, result)
    print(json.dumps({key: result["all"][key] for key in ("answers", "mean", "percentile", "at_least")}), flush=True)


if __name__ == "__main__":
    main()
