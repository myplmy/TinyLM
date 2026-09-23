#!/usr/bin/env python3
"""Compare user-run P104A small dense Windows/WSL JSON; never infer full M5 quality."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def compare(win, wsl, *, ce_limit=0.01, grad_rel_limit=0.10):
    required = ("checkpoint_sha256", "code_sha256", "input_sha256")
    if win.get("schema") != "TINYLM_M5_SMALL_DENSE_V2" or wsl.get("schema") != win.get("schema"):
        return 2, "schema mismatch"
    if win.get("declared_platform") != "windows" or wsl.get("declared_platform") != "wsl":
        return 2, "platform labels mismatch"
    for key in required:
        if win.get(key) != wsl.get(key):
            return 2, f"{key} mismatch"
    values = ("eval_ce", "one_step_ce", "one_step_grad_norm",
              "post_step_eval_ce", "one_step_param_delta_abs")
    if not all(isinstance(row.get(key), (int, float)) and math.isfinite(row[key])
               for row in (win, wsl) for key in values):
        return 2, "missing or non-finite metrics"
    if any(row["one_step_param_delta_abs"] <= 0 for row in (win, wsl)):
        return 8, "one-step optimizer update is zero"
    eval_gap = abs(win["eval_ce"] - wsl["eval_ce"])
    step_gap = abs(win["one_step_ce"] - wsl["one_step_ce"])
    post_gap = abs(win["post_step_eval_ce"] - wsl["post_step_eval_ce"])
    grad_scale = max(abs(win["one_step_grad_norm"]), abs(wsl["one_step_grad_norm"]), 1e-12)
    grad_rel = abs(win["one_step_grad_norm"] - wsl["one_step_grad_norm"]) / grad_scale
    info = (f"eval_ce_abs={eval_gap:.8g} one_step_ce_abs={step_gap:.8g} "
            f"post_step_ce_abs={post_gap:.8g} grad_norm_rel={grad_rel:.8g}")
    if (eval_gap > ce_limit or step_gap > ce_limit or post_gap > ce_limit
            or grad_rel > grad_rel_limit):
        return 8, info + " [GATE NEGATIVE]"
    return 0, info + " [FUNCTIONAL_BRIDGE_PASS; full M5 quality NOT_RUN]"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--win", type=Path, default=Path("runs/bench/p104a_m5_windows.json"))
    ap.add_argument("--wsl", type=Path, default=Path("runs/bench/p104a_m5_wsl.json"))
    ap.add_argument("--max-ce-abs", type=float, default=0.01)
    ap.add_argument("--max-grad-rel", type=float, default=0.10)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        a = {"schema": "TINYLM_M5_SMALL_DENSE_V2", "declared_platform": "windows",
             "checkpoint_sha256": "A", "code_sha256": {"m": "B"}, "input_sha256": "C",
             "eval_ce": 2.0, "one_step_ce": 2.0, "one_step_grad_norm": 0.5,
             "post_step_eval_ce": 1.99, "one_step_param_delta_abs": 0.0002}
        b = dict(a, declared_platform="wsl")
        assert compare(a, b)[0] == 0
        assert compare(a, dict(b, input_sha256="X"))[0] == 2
        assert compare(a, dict(b, eval_ce=2.1))[0] == 8
        assert compare(a, dict(b, post_step_eval_ce=2.1))[0] == 8
        assert compare(a, dict(b, one_step_param_delta_abs=0.0))[0] == 8
        assert compare(a, dict(b, post_step_eval_ce=float("nan")))[0] == 2
        print("[PASS] M5 JSON comparator fixture; model/GPU NOT_RUN")
        return 0
    if not (0 < args.max_ce_abs < 1 and 0 < args.max_grad_rel < 1):
        ap.error("invalid comparison thresholds")
    win = json.loads(args.win.read_text(encoding="utf-8"))
    wsl = json.loads(args.wsl.read_text(encoding="utf-8"))
    code, info = compare(win, wsl, ce_limit=args.max_ce_abs,
                         grad_rel_limit=args.max_grad_rel)
    print(info)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
