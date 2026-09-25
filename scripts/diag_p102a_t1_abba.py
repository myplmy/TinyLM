#!/usr/bin/env python3
"""P102A Stage1Wb: CPU-only order-balanced T0/T1 JSON attribution."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from diag_p102a_t1_wall_contract import MATCH_FIELDS, compare_pair


def evaluate(t0a: dict, t1a: dict, t1b: dict, t0b: dict) -> dict:
    records = (t0a, t1a, t1b, t0b)
    tags = [record.get("tag") for record in records]
    if any(not isinstance(tag, str) or not tag for tag in tags) or len(set(tags)) != 4:
        raise ValueError("ABBA needs four distinct tagged training JSONs")
    for key in MATCH_FIELDS:
        if key not in t0a or any(record.get(key) != t0a[key] for record in records[1:]):
            raise ValueError(f"ABBA four-arm identity differs or is absent: {key}")
    forward = compare_pair(t0a, t1a)
    reverse = compare_pair(t0b, t1b)
    ratios = (forward["whole_speedup"], reverse["whole_speedup"])
    mean_ratio = math.sqrt(ratios[0] * ratios[1])
    eval_save = (forward["eval_save_saved_sec"], reverse["eval_save_saved_sec"])
    residual = (
        forward["whole_saved_sec"] - eval_save[0],
        reverse["whole_saved_sec"] - eval_save[1],
    )
    if any(not math.isfinite(value) for value in (*ratios, *eval_save, *residual)):
        raise ValueError("non-finite ABBA attribution")
    direction = all(ratio >= 1.01 and saving > 0 for ratio, saving in zip(ratios, eval_save))
    return {
        "schema": "P102A_T1_ABBA_V1",
        "orders": ["T0a,T1a", "T1b,T0b"],
        "tags": tags,
        "forward": forward,
        "reverse": reverse,
        "whole_speedup_geomean": mean_ratio,
        "whole_speedup_order_ratio": ratios[0] / ratios[1],
        "unattributed_sec_by_order": list(residual),
        "screen": "DIRECTIONAL_CANDIDATE" if direction else "VALID_NEGATIVE",
        "adoption": "NOT_DECIDED_FIXED_CROP_AND_DEPLOY_NOT_RUN",
        "limit": "host wall is not GPU kernel time; two orders in one session are not independent seeds",
    }


def _fixture(tag: str, eval_every: int, save_every: int, wall: float) -> dict:
    calls = 8 if eval_every == 100 else 2
    phase = {
        "kind": "host_wall_no_extra_sync",
        "step_sec": wall - 20.0,
        "eval_sec": 12.0 if calls == 8 else 3.0,
        "save_sec": 3.0 if calls == 8 else 1.0,
        "snapshot_sec": 1.0,
        "final_eval_sec": 1.0,
        "eval_calls": calls,
        "checkpoint_writes": 16 if calls == 8 else 3,
    }
    data = {"tag": tag, "eval_every": eval_every, "save_every": save_every,
            "wall_sec": wall, "history": [{} for _ in range(calls)],
            "t1_phase_wall": phase}
    data.update({key: 1 for key in MATCH_FIELDS})
    return data


def self_test() -> None:
    records = (
        _fixture("t0a", 100, 0, 120.0),
        _fixture("t1a", 500, 1000, 100.0),
        _fixture("t1b", 500, 1000, 100.0),
        _fixture("t0b", 100, 0, 110.0),
    )
    good = evaluate(*records)
    assert good["screen"] == "DIRECTIONAL_CANDIDATE"
    assert good["whole_speedup_geomean"] > 1.1
    slow = evaluate(records[0], records[1], _fixture("slow", 500, 1000, 120.0), records[3])
    assert slow["screen"] == "VALID_NEGATIVE"
    for broken in (
        (records[0], records[1], records[2], records[0]),
        (records[0], records[1], dict(records[2], seed=2), records[3]),
        (records[0], records[1], dict(records[2], save_every=0), records[3]),
    ):
        try:
            evaluate(*broken)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid ABBA fixture accepted")
    print("[PASS] P102A ABBA four-tag, condition, order and negative-screen contract; model NOT_RUN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    for name in ("t0a", "t1a", "t1b", "t0b"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    paths = [getattr(args, name) for name in ("t0a", "t1a", "t1b", "t0b")]
    if any(path is None for path in paths):
        parser.error("all four --t0a/--t1a/--t1b/--t0b JSONs are required")
    try:
        records = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        result = evaluate(*records)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"[FAIL] P102A ABBA input/condition: {type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if result["screen"] == "VALID_NEGATIVE":
        print("[GATE NEGATIVE] speed/eval-saving direction did not replicate in both orders")
        return 8
    print("[CANDIDATE] order-balanced host-wall direction only; fixed-crop quality is separate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
