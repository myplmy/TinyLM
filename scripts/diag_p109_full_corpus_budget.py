"""Audit one complete v1.1 pass and distribute the intact v3 curriculum groups."""

from hashlib import sha256
from pathlib import Path
import json
import math

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / "test_result/evidence/p109c_integrated_scratch_v3_v11_chat32_s1337_run1_20261124"
CACHE = ROOT / "data_cache/ko-en_p109c_adopted_v11_20261121_chat32/meta.json"
OUT = ROOT / "test_result/evidence/p109_full_train_6gib_20261124_budget.json"
WIDTH = 1024
BATCH = 4
SLOTS = 32
SEED = 1337


def read(path):
    return json.loads(path.read_bytes())


def main():
    old = read(V3 / "report.json")
    device = read(V3 / "supervisor.json")
    meta = read(CACHE)
    raw_tokens = int(meta["train"])
    course_tokens = int(old["course_tokens"])
    previous_draws = int(old["raw_tokens"]) + course_tokens
    old_elapsed = device["ended"] - device["started"]
    width = WIDTH * BATCH
    end_budget = old_elapsed * 2

    update_log = (V3 / "updates.jsonl").read_bytes()
    history = [json.loads(row) for row in update_log.splitlines()]
    if (len(history) != old["steps"] or sum(row["course_tokens"] for row in history) != course_tokens
            or sum(row["raw_targets"] for row in history) != old["raw_tokens"]
            or any(row["index"] != i or not row["optimizer_applied"] for i, row in enumerate(history))):
        raise ValueError("the proven v3 update census changed")
    counts = [row["actual_forwards"] - row["raw_targets"] // width for row in history]
    if any(row["raw_targets"] % width or row["route_visits"] != 28 or not 0 <= n < SLOTS
           for row, n in zip(history, counts, strict=True)):
        raise ValueError("invalid course slots or visit geometry")

    raw_targets = raw_tokens - 1
    raw_batches = math.ceil(raw_targets / width)
    course_batches = sum(counts)
    steps = math.ceil((raw_batches + course_batches) / SLOTS)
    placement = {}
    for i, count in enumerate(counts):
        if count:
            address = round(i * (steps - 1) / (len(counts) - 1))
            if address in placement:
                raise ValueError("two intact course groups reached the same new update")
            placement[address] = (i, count)

    raw_order = np.random.default_rng(SEED).permutation(raw_batches).astype("<i8")
    if not np.array_equal(np.sort(raw_order), np.arange(raw_batches)):
        raise ValueError("the raw target window order is incomplete")
    schedule = np.zeros((steps, 4), dtype="<i8")
    cursor = 0
    course_quarters = [0, 0, 0, 0]
    for update in range(steps):
        old_index, course = placement.get(update, (-1, 0))
        raw = min(SLOTS - course, raw_batches - cursor)
        schedule[update] = (cursor, raw, old_index, course)
        cursor += raw
        if old_index >= 0:
            course_quarters[update * 4 // steps] += history[old_index]["course_tokens"]
    if cursor != raw_batches or schedule[:, 3].sum() != course_batches or sum(course_quarters) != course_tokens:
        raise ValueError("the full-pass schedule dropped inputs")

    result = dict(previous_draws=previous_draws, previous_wall_seconds=old_elapsed, twice_wall_seconds=end_budget,
                  raw_file_tokens=raw_tokens, raw_scored_targets=raw_targets, v3_course_nonpad=course_tokens,
                  nominal_tokens=raw_tokens+course_tokens, required_nominal_per_second=(raw_tokens+course_tokens)/end_budget,
                  previous_nominal_per_second=previous_draws/old_elapsed,
                  raw_b4_windows=raw_batches, raw_tail_valid_targets=1+(raw_targets-1)%width,
                  raw_permutation_seed=SEED, raw_permutation_sha256=sha256(raw_order.tobytes()).hexdigest(),
                  steps=steps, course_microbatches=course_batches, first_course_update_zero_based=min(placement),
                  last_course_update_zero_based=max(placement), mixed_updates=len(placement),
                  course_tokens_by_quarter=course_quarters, course_padding_ratio=1-course_tokens / (width*course_batches),
                  all_active_forward_slots=(raw_batches+course_batches)*width,
                  active_forward_slots_per_second=(raw_batches+course_batches)*width/end_budget,
                  budget_sec_per_update=end_budget/steps,
                  original_mean_course_loss_share=sum(row["course_share"] for row in history)/len(history),
                  stretched_mean_course_loss_share=sum(history[i]["course_share"] for i, _ in placement.values())/steps,
                  original_update_log_sha256=sha256(update_log).hexdigest(),
                  schedule_columns=["raw_batch_cursor", "raw_batches", "original_course_update", "course_batches"],
                  schedule_sha256=sha256(schedule.tobytes()).hexdigest(), status="CPU_SCHEDULE_CENSUS_ONLY")
    with OUT.open("x", encoding="utf-8") as fp:
        json.dump(result, fp, indent=2)
        fp.write("\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
