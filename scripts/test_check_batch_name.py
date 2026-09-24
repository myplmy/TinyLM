#!/usr/bin/env python3
"""Composite rerun-stage names still need an exact plan label."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_batch_name import check, stage_present


def main():
    plan = ROOT / "test_plan" / "P104A_WSL-M4-M5-게이트와-소형-dense-교량.md"
    if not stage_present(plan, "Stage1Bb"):
        raise RuntimeError("planned composite rerun suffix was rejected")
    if stage_present(plan, "Stage1Bc"):
        raise RuntimeError("unplanned composite suffix was accepted")
    errors, _ = check("run_P104A_Stage1Bb_m5_dense_bridge.bat")
    if errors:
        raise RuntimeError("planned Windows rerun BAT was rejected: " + str(errors))
    print("[PASS] exact composite stage label; unplanned suffix rejected")


if __name__ == "__main__":
    main()
