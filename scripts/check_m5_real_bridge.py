#!/usr/bin/env python3
"""P104A same-real-checkpoint Windows/WSL JSON comparator; CPU-only."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from check_m5_dense_bridge import compare as compare_small


def compare(win: dict, wsl: dict, *, ce_limit: float = 0.01,
            grad_rel_limit: float = 0.10) -> tuple[int, str]:
    if win.get("schema") != "TINYLM_M5_REAL_DENSE_V1" or wsl.get("schema") != win.get("schema"):
        return 2, "real M5 schema mismatch"
    if win.get("declared_platform") != "windows" or wsl.get("declared_platform") != "wsl":
        return 2, "real M5 platform labels mismatch"
    for key in ("checkpoint_sha256", "code_sha256", "input_sha256",
                "step_input_sha256", "tokenizer_sha256", "preset", "data", "arch",
                "eval_seq", "eval_micro_bs", "eval_windows", "eval_tokens"):
        if key not in win or win[key] != wsl.get(key):
            return 2, f"real M5 {key} missing or mismatched"
    if win["eval_windows"] < 1000 or win["eval_tokens"] < 1_000_000:
        return 2, "real M5 fixed-val coverage insufficient"
    left, right = dict(win, schema="TINYLM_M5_SMALL_DENSE_V2"), dict(wsl, schema="TINYLM_M5_SMALL_DENSE_V2")
    status, info = compare_small(left, right, ce_limit=ce_limit,
                                 grad_rel_limit=grad_rel_limit)
    if status != 0:
        return status, info
    times = ("eval_wall_sec", "one_step_wall_ms")
    if any(not isinstance(row.get(key), (int, float)) or not math.isfinite(row[key])
           or row[key] <= 0 for row in (win, wsl) for key in times):
        return 2, "real M5 timing absent or invalid"
    return 0, (
        info + f"; fixed_val_windows={win['eval_windows']} "
        f"eval_wall_windows_over_wsl={win['eval_wall_sec']/wsl['eval_wall_sec']:.4f} "
        f"one_step_wall_windows_over_wsl={win['one_step_wall_ms']/wsl['one_step_wall_ms']:.4f} "
        "[REAL_CHECKPOINT_FUNCTIONAL_PASS; OS speed and 300M training equivalence NOT_DECIDED]"
    )


def self_test() -> None:
    base = {
        "schema": "TINYLM_M5_REAL_DENSE_V1", "declared_platform": "windows",
        "checkpoint_sha256": "A", "code_sha256": {"source": "B"},
        "input_sha256": "C", "step_input_sha256": "D",
        "tokenizer_sha256": "E", "preset": "m100s10", "data": "ko-en",
        "arch": "dense", "eval_seq": 1024, "eval_micro_bs": 4,
        "eval_windows": 2929, "eval_tokens": 2_999_296,
        "eval_ce": 3.5, "one_step_ce": 3.5, "one_step_grad_norm": 0.5,
        "post_step_eval_ce": 3.49, "one_step_param_delta_abs": 0.0002,
        "eval_wall_sec": 20.0, "one_step_wall_ms": 100.0,
    }
    other = dict(base, declared_platform="wsl", eval_ce=3.5001)
    assert compare(base, other)[0] == 0
    assert compare(base, dict(other, checkpoint_sha256="X"))[0] == 2
    assert compare(base, dict(other, eval_windows=20))[0] == 2
    assert compare(base, dict(other, eval_ce=3.7))[0] == 8
    assert compare(base, dict(other, one_step_param_delta_abs=0.0))[0] == 8
    print("[PASS] P104A real M5 SHA/coverage/numeric and negative fixtures; GPU/model NOT_RUN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--win", type=Path, default=Path("runs/bench/p104a_m5_real_windows.json"))
    parser.add_argument("--wsl", type=Path, default=Path("runs/bench/p104a_m5_real_wsl.json"))
    parser.add_argument("--max-ce-abs", type=float, default=0.01)
    parser.add_argument("--max-grad-rel", type=float, default=0.10)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not (0 < args.max_ce_abs < 1 and 0 < args.max_grad_rel < 1):
        parser.error("invalid comparison thresholds")
    try:
        win = json.loads(args.win.read_text(encoding="utf-8"))
        wsl = json.loads(args.wsl.read_text(encoding="utf-8"))
        status, info = compare(win, wsl, ce_limit=args.max_ce_abs,
                               grad_rel_limit=args.max_grad_rel)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"[FAIL] P104A real M5 comparator input: {type(exc).__name__}: {exc}")
        return 2
    print(info)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
