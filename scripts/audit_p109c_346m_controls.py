"""Compare completed P109C training routes, exposure and host-wall accounting."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
import re

from scripts.diag_p102a_t1_wall_contract import summarize as wall_contract


EVIDENCE = Path(__file__).resolve().parents[1] / "test_result" / "evidence"
STEPS = 2942
EXPOSURE = (
    "index", "source_update", "reserved_batches", "empty_batches", "actual_forwards", "raw_targets",
    "course_tokens", "context_targets", "location_targets", "contrast_questions", "relation_questions",
    "answer_start_targets", "answer_body_targets", "answer_eot_targets", "valid_ce_targets",
    "answer_weights", "raw_context_weight", "course_share", "value_weight",
)
PROGRESS = re.compile(r"\s*step\s+(\d+)/2942.*?(\d+) ms/step\s*\Z")


def file_data(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"missing regular receipt {path}")
    return path.read_bytes()


def timed_record(record, tag, terminal):
    logs = sorted((record / "native_logs").glob(f"*_{tag}.json"))
    if len(logs) != 1:
        raise ValueError("exactly one native training time receipt is required")
    contents = file_data(logs[0])
    native = json.loads(contents)
    validated = wall_contract(native)
    measured = native["t1_phase_wall"]
    wall = terminal["ended"] - terminal["started"]
    if not wall >= validated["wall_sec"] > 0:
        raise ValueError("supervisor wall must contain native wall time")
    durations = {key: measured[key] for key in ("step_sec", "eval_sec", "save_sec", "snapshot_sec", "final_eval_sec")}
    durations.update(native_other_sec=validated["other_sec"], supervisor_outside_native_sec=wall-validated["wall_sec"],
                     total_sec=wall)
    source = file_data(record / "stdout.txt")
    points = {}
    for line in source.decode().splitlines():
        match = PROGRESS.fullmatch(line)
        if match:
            index, cumulative_ms = map(int, match.groups())
            points[index+1] = cumulative_ms * (index+1) / 1000
    return dict(durations=durations, native_log_sha256=sha256(contents).hexdigest().upper(),
                native_stdout_sha256=sha256(source).hexdigest().upper(), progress_points=points,
                save_count=measured["checkpoint_writes"], eval_count=measured["eval_calls"])


def arm(record):
    profile, report, receipt = (json.loads(file_data(record / f"{name}.json"))
                                for name in ("extension", "report", "supervisor"))
    if (report["status"] != "FULL_SCRATCH_MIXED_COMPLETE" or report["tag"] != profile["tag"]
            or report["steps"] != STEPS or profile["steps"] != STEPS or receipt["returncode"] != 0
            or receipt["stop_reason"] is not None or receipt["card_after_exit"]["compute_pids"] != []
            or receipt["card_after_exit"]["sampled_at"] < receipt["ended"]):
        raise ValueError("the training and device return receipts must agree")
    signature = profile["signature"]
    schedule = signature["raw_visit_schedule"]
    if (report["input_manifest_sha256"] != signature["manifest_sha256"]
            or report["final_preset"] != signature or schedule["course_repeat"] != 2 or schedule["late_repeat"] != 2):
        raise ValueError("the completed weights must bind the intended training route")
    journal = file_data(record / "updates.jsonl")
    rows = [json.loads(line) for line in journal.splitlines()]
    if len(rows) != STEPS or not journal.endswith(b"\n"):
        raise ValueError("the complete update journal must be present")
    for index, row in enumerate(rows):
        expected = 16 if index < schedule["boundary"] and schedule["early_repeat"] == 1 else 28
        if (row["index"] != index or row["source_update"] != index or not row["optimizer_applied"]
                or row["raw_route_visits"] != expected or row["course_route_visits"] != 28):
            raise ValueError(f"the actual optimizer or route differs at update {index+1}")
    if sum(row["raw_targets"] for row in rows[:schedule["boundary"]]) != schedule["prefix_raw_targets"]:
        raise ValueError("the cutover must bind its raw target count")
    return dict(profile=profile, schedule=schedule, rows=rows, timing=timed_record(record, profile["tag"], receipt),
                weights=report["evaluation_sha256"], journal_sha256=sha256(journal).hexdigest().upper(),
                peak_card_mib=receipt["peak_card_mib"], report=report)


def time_windows(left, right, boundary):
    base, candidate = (item["timing"]["progress_points"] for item in (left, right))
    common = sorted(base.keys() & candidate.keys())
    before = [step for step in common if 100 < step < boundary]
    after = [step for step in common if boundary < step]
    windows = {}
    for name, steps in (("prefix", before), ("suffix", after)):
        if len(steps) < 2:
            raise ValueError("a reported transition phase has too few native time points")
        start, end = steps[0], steps[-1]
        windows[name] = dict(from_completed_updates=start, until_completed_updates=end,
                             r2_sec_per_update=(base[end]-base[start])/(end-start),
                             candidate_sec_per_update=(candidate[end]-candidate[start])/(end-start))
    return windows


def compare(left, right):
    if left["schedule"]["early_repeat"] != 2 or right["schedule"]["early_repeat"] != 1:
        raise ValueError("compare pure R2 with an R1 to R2 candidate")
    a, b = (item["profile"]["signature"] for item in (left, right))
    ignore = {"raw_visit_schedule", "sources"}
    if ({key: value for key, value in a.items() if key not in ignore}
            != {key: value for key, value in b.items() if key not in ignore}
            or a["sources"].items() - b["sources"].items()):
        raise ValueError("the input or common training source differs")
    for left_row, right_row in zip(left["rows"], right["rows"], strict=True):
        if any(left_row[key] != right_row[key] for key in EXPOSURE):
            raise ValueError(f"the paired exposures differ at update {left_row['index']+1}")
    totals = {key: sum(row[key] for row in left["rows"]) for key in
              ("raw_targets", "course_tokens", "answer_start_targets", "answer_body_targets", "answer_eot_targets")}
    if (totals["raw_targets"], totals["course_tokens"]) != (300_023_808, 46_292_274):
        raise ValueError("the known 346.316M exposure did not close")
    a, b = (item["timing"]["durations"] for item in (left, right))
    delta = {key: value - b[key] for key, value in a.items()}
    def output(item):
        timing = {key: value for key, value in item["timing"].items() if key != "progress_points"}
        return dict(tag=item["profile"]["tag"], route=item["schedule"], checkpoint_sha256=item["weights"],
                    journal_sha256=item["journal_sha256"], peak_card_mib=item["peak_card_mib"], timing=timing,
                    forward_layer_slots=sum(row["forward_layer_slots"] for row in item["rows"]))
    return dict(status="COMPLETED_TRAINING_PAIRED", r2=output(left), candidate=output(right),
                matched_update_fields=EXPOSURE, exposure=totals, delta_seconds=delta,
                wall_reduction=delta["total_sec"]/a["total_sec"],
                approximate_native_updates=time_windows(left, right, right["schedule"]["boundary"]),
                timing_scope="Host wall by phase; progress time uses rounded cumulative averages and includes periodic work.")


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--r2", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    r2, candidate = (path.resolve(strict=True) for path in (args.r2, args.candidate))
    if any(path.parent != EVIDENCE for path in (r2, candidate)) or args.output.absolute().parent != EVIDENCE:
        parser.error("use explicit local evidence records")
    result = compare(arm(r2), arm(candidate))
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(result["delta_seconds"]), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
