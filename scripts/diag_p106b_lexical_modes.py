#!/usr/bin/env python3
"""Read-only CPU A/B latency gate on exact frozen teacher answers, not new GPU evidence.

Print candidate text for later context review. No quality threshold/adoption,
new data, model loading or embedding/NLI implementation.
"""
import argparse
import json
from pathlib import Path
import statistics
import sys
import time
import tracemalloc
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.p106b_lexical_observation import TextObserver


def benchmark(groups, repetitions=10):
    results = {}
    for mode in ("within", "recent"):
        durations, pair_counts, examples = [], [], []
        tracemalloc.start()
        for repeat in range(repetitions):
            observer = TextObserver(mode)
            for index, (question, answers) in enumerate(groups):
                began = time.perf_counter()
                output = observer.observe(f"r{repeat}:g{index}", question, answers)
                durations.append(time.perf_counter()-began)
                pair_counts.append(output["pair_count"])
                if repeat == 0:
                    examples.append(output)
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        p95 = sorted(durations)[max(0, int(len(durations)*.95)-1)]
        results[mode] = {"requests": len(durations), "median_ms": statistics.median(durations)*1000,
            "p95_ms": p95*1000, "cpu_peak_bytes": peak, "displayed_pairs": sum(pair_counts),
            "latency_budget_passed": p95 <= .2 and peak <= 32*1024*1024,
            "examples": examples, "false_positive_review": "NOT_RUN", "adoption": "NOT_DECIDED"}
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--check-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        results = benchmark([("same question", ["A is X", "A is Y"]), ("say1", ["1", "1"])], 1)
        assert all(r["adoption"] == "NOT_DECIDED" for r in results.values())
    else:
        from scripts.view_p106b_saved_answers import panel_data
        _report, _raw, rows = panel_data()
        from scripts.p106b_output_contract import row_text
        grouped = {}
        for row in rows:
            ident = row["meta"]["generation_id"].rsplit("_a", 1)[0]
            grouped.setdefault(ident, []).append(row)
        if args.check_only:
            print("[PASS] exact frozen answer SHA; CPU observations not yet run")
            return 0
        results = benchmark([(row_text(group[0], 0), [row_text(r, 1) for r in group]) for group in grouped.values()])
    print("[LEXICAL_AB_CPU] " + json.dumps({name: {key: value for key, value in result.items() if key != "examples"}
          for name, result in results.items()}, ensure_ascii=False, sort_keys=True))
    for mode, result in results.items():
        for observation in result["examples"]:
            print("[LEXICAL_PAIR_VIEW] " + json.dumps({"mode": mode, **observation}, ensure_ascii=False))
    print("[INFO] CPU latency only; live teacher/student slowdown and candidate false positives require user review.")
    return 0 if all(r["latency_budget_passed"] for r in results.values()) else 8


if __name__ == "__main__":
    raise SystemExit(main())
