#!/usr/bin/env python3
"""P102A T1 host-wall JSON contract and attribution; no GPU/model import."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

MATCH_FIELDS = (
    "arch", "preset", "data", "steps", "seed", "micro_bs", "accum",
    "seq", "pool_tokens", "exact_cache", "lr", "sched", "optimizer",
    "muon_scale", "muon_lr_mult", "matrix_weight_decay_effective",
    "cla_group", "grad_ckpt", "anneal_end", "decay_frac", "ce_chunk",
    "init_from_src", "compile", "compile_mode", "tokens",
    "vocab_size", "n_layers", "qk_gain_learnable",
)


def summarize(record: dict) -> dict:
    phase = record.get("t1_phase_wall")
    if not isinstance(phase, dict) or phase.get("kind") != "host_wall_no_extra_sync":
        raise ValueError("T1 phase-wall contract is absent")
    durations = ("step_sec", "eval_sec", "save_sec", "snapshot_sec", "final_eval_sec")
    counts = ("eval_calls", "checkpoint_writes")
    if any(not isinstance(phase.get(key), (int, float)) or not math.isfinite(phase[key])
           or phase[key] < 0 for key in durations):
        raise ValueError("T1 duration is missing, negative or non-finite")
    if any(not isinstance(phase.get(key), int) or phase[key] < 0 for key in counts):
        raise ValueError("T1 call count is missing or invalid")
    history = record.get("history")
    if not isinstance(history, list) or phase["eval_calls"] != len(history):
        raise ValueError("T1 eval count does not match history")
    wall = record.get("wall_sec")
    if not isinstance(wall, (int, float)) or not math.isfinite(wall) or wall <= 0:
        raise ValueError("T1 whole wall is missing or invalid")
    covered = sum(phase[key] for key in durations)
    if covered > wall * 1.05 + 1.0:
        raise ValueError("T1 measured phases exceed whole wall beyond clock tolerance")
    return {"wall_sec": wall, "covered_sec": covered,
            "other_sec": wall - covered,
            "eval_save_sec": phase["eval_sec"] + phase["save_sec"],
            "eval_save_fraction": (phase["eval_sec"] + phase["save_sec"]) / wall,
            "eval_calls": phase["eval_calls"],
            "checkpoint_writes": phase["checkpoint_writes"]}



def compare_pair(baseline: dict, candidate: dict) -> dict:
    """T1 cadence-only screen, not a speed or quality adoption verdict."""
    for key in MATCH_FIELDS:
        if key not in baseline or key not in candidate or baseline[key] != candidate[key]:
            raise ValueError(f"T1 paired condition differs or is absent: {key}")
    if baseline.get("eval_every") != 100 or baseline.get("save_every") != 0:
        raise ValueError("T1 control must use eval100/save0")
    if candidate.get("eval_every") != 500 or candidate.get("save_every") != 1000:
        raise ValueError("T1 candidate must use eval500/save1000")
    left, right = summarize(baseline), summarize(candidate)
    return {"t0_wall_sec": left["wall_sec"], "t1_wall_sec": right["wall_sec"],
            "t0_eval_save_sec": left["eval_save_sec"],
            "t1_eval_save_sec": right["eval_save_sec"],
            "whole_saved_sec": left["wall_sec"] - right["wall_sec"],
            "eval_save_saved_sec": left["eval_save_sec"] - right["eval_save_sec"],
            "whole_speedup": left["wall_sec"] / right["wall_sec"],
            "condition": "PAIRED_CONDITION_SINGLE_ORDER",
            "adoption": "NOT_DECIDED"}

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--baseline", type=Path)
    ap.add_argument("--candidate", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        fixture = {"wall_sec": 10.0, "history": [{}, {}], "t1_phase_wall": {
            "kind": "host_wall_no_extra_sync", "step_sec": 8.0,
            "eval_sec": 1.0, "save_sec": 0.5, "snapshot_sec": 0.1,
            "final_eval_sec": 0.2, "eval_calls": 2, "checkpoint_writes": 3}}
        assert abs(summarize(fixture)["eval_save_fraction"] - 0.15) < 1e-12
        for broken in (
            dict(fixture, t1_phase_wall=dict(fixture["t1_phase_wall"], eval_calls=1)),
            dict(fixture, t1_phase_wall=dict(fixture["t1_phase_wall"], save_sec=50.0)),
            dict(fixture, t1_phase_wall={}),
        ):
            try:
                summarize(broken)
            except ValueError:
                pass
            else:
                raise AssertionError("invalid T1 fixture was accepted")
        control = dict(fixture, eval_every=100, save_every=0)
        candidate = dict(fixture, eval_every=500, save_every=1000)
        for key in MATCH_FIELDS:
            control[key] = candidate[key] = 1
        assert compare_pair(control, candidate)["whole_speedup"] == 1.0
        for bad in (dict(candidate, seed=2), dict(candidate, save_every=0),
                    dict(candidate, t1_phase_wall={})):
            try:
                compare_pair(control, bad)
            except ValueError:
                pass
            else:
                raise AssertionError("invalid T1 pair was accepted")
        print("[PASS] P102A T1 single/paired JSON phase-wall contract; model/GPU NOT_RUN")
        return 0
    if args.baseline or args.candidate:
        if not args.baseline or not args.candidate or args.json:
            ap.error("--baseline and --candidate must be paired without --json")
        left = json.loads(args.baseline.read_text(encoding="utf-8"))
        right = json.loads(args.candidate.read_text(encoding="utf-8"))
        print(json.dumps(compare_pair(left, right), ensure_ascii=False, sort_keys=True))
        print("[LIMIT] one order/seed is descriptive only; fixed-crop quality and GPU E2E need user evidence")
        return 0
    if args.json is None:
        ap.error("--json, paired inputs or --self-test is required")
    record = json.loads(args.json.read_text(encoding="utf-8"))
    summary = summarize(record)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    print("[LIMIT] host wall attribution is not individual GPU kernel time; paired quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
