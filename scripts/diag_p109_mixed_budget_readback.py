"""Check that the sustained mixed arms saw the same data and price a full pass."""

from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
import json
import math

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "test_result/evidence"
SCOPE = EVIDENCE / "p109_full_train_6gib_20261124_budget.json"


def read(path):
    return json.loads(path.read_bytes())


def examine(parent, child, scope, reserve):
    profile = read(parent / "profile.json")
    recipe = dict(profile["arms"])[child.name[3:]]
    worker = read(child / "worker.json")
    supervisor = read(child / "supervisor.json")
    binding = read(child / "mix_binding.json")
    steps = [json.loads(row) for row in (child / "steps.jsonl").read_bytes().splitlines()]
    ceiling = profile["card_ceiling_mib"]
    if (supervisor["returncode"] != 0 or supervisor["stop_reason"] or not supervisor["samples"]
            or supervisor["peak_card_mib"] > ceiling or supervisor["card_after_exit"].get("compute_pids") != []
            or len(steps) != profile["steps"] or len(steps) != worker["updates"]
            or any(row["step"] != i or row["targets"] != row["raw_targets"]+row["course_tokens"]
                   for i, row in enumerate(steps))):
        raise ValueError(f"the supervisor or training journal did not close for {child.name}")
    rows = steps[1:]
    rate = sum(r["targets"] for r in rows) / sum(r["sec"] for r in rows)
    if not math.isclose(rate, worker["tokens_per_s"], rel_tol=1.e-9):
        raise ValueError("the recorded mixed rate disagrees with the update journal")

    phases = {}
    for repeat in (1, 2):
        part = [row for row in rows if row["raw_repeat"] == repeat]
        if part:
            phases[repeat] = sum(x["raw_targets"] for x in part)/sum(x["raw_sec"] for x in part)
    course_seconds = sum(row["course_sec"] for row in rows)/sum(row["course_batches"] for row in rows)
    fixed_step_seconds = sum(row["sec"]-row["raw_sec"]-row["course_sec"] for row in rows)/len(rows)
    scheduled_r1 = recipe["r2_from"] if recipe["repeat"] == 1 else 0.
    raw_time = scope["raw_scored_targets"]*((scheduled_r1/phases[1] if scheduled_r1 else 0.)
                                           + (1-scheduled_r1)/phases[2])
    course_time = course_seconds*scope["course_microbatches"]
    fixed_time = fixed_step_seconds*scope["steps"]
    compute = raw_time+course_time+fixed_time
    target = scope["twice_wall_seconds"]
    permitted_r2 = None
    if 1 in phases:
        # Available R2 share using the observed cost of the two raw routes.
        allowed = (target-course_time-fixed_time-reserve)/scope["raw_scored_targets"]
        permitted_r2 = (allowed-1/phases[1])/(1/phases[2]-1/phases[1])
    summary = dict(steps=len(steps), peak_card_mib=supervisor["peak_card_mib"], missed_samples=supervisor["missed"],
                   max_torch_allocated_mib=max(row["allocated_mib"] for row in steps),
                   max_torch_reserved_mib=max(row["reserved_mib"] for row in steps),
                   max_cuda_global_used_mib=max(row["cuda_global_used_mib"] for row in steps),
                   actual_startup_to_exit_sec=supervisor["end"]-supervisor["start"],
                   val_initial=worker["initial_val_r2"], val_final=worker["final_val_r2"],
                   val_windows_final=worker["val_curve"][-1]["window_nll"], val_targets=binding["val_targets"],
                   seen_raw=worker["seen_raw"], seen_course=worker["seen_course"],
                   supervised_answers=[sum(row["course_answers"][i] for row in steps) for i in range(3)],
                   bilingual_pairs=sum(row["bilingual_pairs"] for row in steps),
                   relation_questions=sum(row["relations"] for row in steps), decimals=sum(row["decimals"] for row in steps),
                   mixed_rate=rate, raw_rates=phases, course_seconds_per_batch=course_seconds,
                   fixed_seconds_per_update=fixed_step_seconds, projected_raw_sec=raw_time,
                   projected_course_sec=course_time, projected_fixed_sec=fixed_time,
                   projection_steady_sec=compute, assumed_saving_and_validation_reserve_sec=reserve,
                   projection_with_reserve_sec=compute+reserve, wall_budget_sec=target,
                   room_for_all_overhead_sec=target-compute, max_raw_r2_fraction_with_reserve=permitted_r2)
    identity = dict(raw_window_order=worker["raw_window_order_sha256"], val_starts=binding["val_starts_sha256"],
                    course=binding["actual_course_source_addresses"],
                    update_targets=[(r["raw_targets"], r["course_tokens"], r["course_answers"]) for r in steps])
    return summary, identity


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--reserve-seconds", type=int, required=True)
    args = parser.parse_args()
    if args.reserve_seconds < 0:
        raise ValueError("the I/O allowance must be nonnegative")
    parent = EVIDENCE / "p109_full_train_6gib_20261124_sustained_v3"
    scope = read(SCOPE)
    arms = {}
    previous = None
    for child in sorted(parent.glob("[0-9][0-9]_mix*")):
        summary, identity = examine(parent, child, scope, args.reserve_seconds)
        if previous is not None and identity != previous:
            raise ValueError("mixed arms saw different training or validation inputs")
        previous = identity
        arms[child.name] = summary
    if len(arms) != len(read(parent / "profile.json")["arms"]):
        raise ValueError("the paired queue is incomplete")
    control = next(value for key, value in arms.items() if key.endswith("_mix_r2"))
    for summary in arms.values():
        gaps = np.array(summary["val_windows_final"]) - control["val_windows_final"]
        summary["paired_window_delta_vs_r2"] = dict(mean=float(np.mean(gaps)),
            descriptive_ci95=[float(x) for x in np.quantile(np.random.default_rng(20261124).choice(
                gaps, size=(10000, len(gaps))).mean(axis=1), [.025, .975])])
    receipt = dict(paired_inputs_sha256=sha256(json.dumps(previous, sort_keys=True).encode()).hexdigest(),
                   v3_wall_seconds=scope["previous_wall_seconds"], full_nominal_tokens=scope["nominal_tokens"],
                   arms=arms, evidence="observed update rates, full-pass estimates, one seed and small R2 VAL sample")
    path = parent / "paired_budget_readback.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(path)


if __name__ == "__main__":
    main()
