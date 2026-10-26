#!/usr/bin/env python3
"""Run the frozen CPU statistics only after both official full closures exist."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import summarize_p106b_native_format_pair as stats
from handoff.audit.oct26_research.run_native_official import publish

BASE = Path(__file__).resolve().parent
SOURCE = "0465071FB3FB9C18190D37DCDE72D85E86B3E36E445A9E4C194B13442A4F5BA5"
OUTPUT = ROOT / "test_result/evidence/p106b_native_format_pair_stats_v1_20261026_main"


def prepare(*, allow_write):
    stats.require(stats.source_identity()["sha256"] == SOURCE, "frozen statistics source differs")
    roots = {model: ROOT / "test_result/evidence" / (stats.official.PREFIX + model + "_full") / "root_closed_ref.json"
             for model in stats.NEW_MODELS}
    if not all(path.is_file() for path in roots.values()):
        raise stats.Hold("both actual full evaluations are required")
    value = dict(schema=stats.INPUTS_SCHEMA, root_approved=True, statistics_source_sha256=SOURCE,
                 official_source_sha256=stats.OFFICIAL_SHA, training_source_sha256=stats.TRAINING_SHA,
                 dialogue_source_sha256=stats.DIALOGUE_SHA, new_models={})
    for model, root in roots.items():
        profile = BASE / ("native_official_" + model + "_profile_v1.json")
        stats.require(profile.is_file(), "original official profile is absent")
        value["new_models"][model] = dict(
            profile=dict(path=str(profile.relative_to(ROOT)), sha256=stats.official.digest(profile)),
            full_root_ref=dict(path=str(root.relative_to(ROOT)), sha256=stats.official.digest(root)))
    path = BASE / "native_pair_stats_inputs_v1.json"
    if path.exists():
        stats.require(json.loads(path.read_text()) == value, "existing statistics inputs differ")
        return dict(path=str(path.relative_to(ROOT)), sha256=stats.official.digest(path))
    if not allow_write:
        raise stats.Hold("root statistics inputs are not yet prepared")
    return publish(path, value)


def validate_close(report, terminal, actual_exit, elapsed):
    stats.require(type(actual_exit) is int and actual_exit == 0, "actual CPU process must exit zero")
    stats.require(terminal == [dict(event="OBSERVATION", returncode=0)], "statistics terminal veto or missing closure")
    stats.require(report.get("schema") == stats.SCHEMA and report.get("returncode") == 9
                  and report.get("candidate_returncode") == 0
                  and report.get("candidate_status") == "PAIR_STATS_CPU_COMPLETE"
                  and report.get("source_identity", {}).get("sha256") == SOURCE
                  and set(report.get("models", {})) == set((*stats.NEW_MODELS, *stats.PEERS))
                  and set(report.get("pairs", {})) == {a + "__" + b for a, b in stats.PAIRS}
                  and len(report.get("exact_tests", [])) == 30
                  and report.get("holm_family", {}).get("size") == 30
                  and report.get("holm_family", {}).get("families") == 1
                  and report.get("models_loaded") == 0 and report.get("gpu_calls") == 0
                  and report.get("model_weight_bodies_read") is False,
                  "statistics candidate scope differs")
    stats.require(type(elapsed) in (float, int) and elapsed > 0
                  and 0 < report["whole_parent_seconds"] <= elapsed, "actual CPU wall receipt differs")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        ref = prepare(allow_write=not args.check_only)
        command = [sys.executable, "-I", "-B", "-X", "utf8", "scripts/summarize_p106b_native_format_pair.py",
                   "--inputs", ref["path"], "--inputs-sha256", ref["sha256"], "--source-sha256", SOURCE,
                   "--max-wall-sec", "600", "--deadline", stats.official.END.isoformat()]
        if args.check_only:
            return subprocess.run(command + ["--check-only"], cwd=ROOT, stdin=subprocess.DEVNULL).returncode
        stats.require(not OUTPUT.exists(), "preserve the previous statistics namespace")
        command += ["--execute", "--output", str(OUTPUT.relative_to(ROOT))]
        began = time.monotonic()
        actual = subprocess.run(["timeout", "--signal=TERM", "--kill-after=5s", "610s", *command],
                                cwd=ROOT, stdin=subprocess.DEVNULL)
        elapsed = time.monotonic() - began
        observed = dict(actual_cpu_exit=actual.returncode, actual_parent_wall_sec=elapsed, command=command)
        if OUTPUT.is_dir():
            publish(OUTPUT / "root_observation.json", observed)
        if actual.returncode:
            return actual.returncode
        report = json.loads((OUTPUT / "report.json").read_text())
        terminal = [json.loads(line) for line in (OUTPUT / "terminal.jsonl").read_text().splitlines()]
        validate_close(report, terminal, actual.returncode, elapsed)
        for name, expected in report["input_files"].items():
            path = stats.checked(name)
            stats.require(path.stat().st_size == expected["bytes"] and stats.official.digest(path) == expected["sha256"],
                          "closed statistics input changed")
        stats.require(stats.source_identity()["sha256"] == SOURCE, "statistics source changed at root close")
        publish(OUTPUT / "root_closed_ref.json", dict(
            path=str((OUTPUT / "report.json").relative_to(ROOT)), sha256=stats.official.digest(OUTPUT / "report.json"),
            terminal_sha256=stats.official.digest(OUTPUT / "terminal.jsonl"), actual_cpu_exit=actual.returncode,
            actual_parent_wall_sec=elapsed, status="CLOSED_CPU_STATS"))
        print(json.dumps(dict(status="CLOSED_CPU_STATS", actual_cpu_exit=0, pairs=5, exact_tests=30)), flush=True)
        return 0
    except stats.Hold:
        print(json.dumps(dict(returncode=8, status="BOTH_OFFICIAL_FULL_NOT_READY", files_written=0, models_loaded=0)))
        return 8


if __name__ == "__main__":
    raise SystemExit(main())
