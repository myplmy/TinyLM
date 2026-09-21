#!/usr/bin/env python3
"""CPU-only contracts for P097 multi-recipe benchmark routing."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.eval_bench_suite import (
    _ad_klue_nli,
    _ad_klue_ynat,
    _model_specs,
)
from scripts.fetch_bench_data import SPECS


def main() -> int:
    models = ["p097_ctrl_v2", "p097_fw2", "p097_edu_v2", "p097_madlad"]
    datas = ["ko-en-control-v2", "ko-en-fw2", "ko-en-edu-v2", "ko-en-madlad"]
    specs = _model_specs(models, "ko-en", datas, ["dense"])
    assert specs == list(zip(models, datas, ["dense"] * 4))
    shared = _model_specs(["dense", "tied"], "ko-en")
    assert shared == [("dense", "ko-en", "dense"), ("tied", "ko-en", "tied")]

    ynat = _ad_klue_ynat({"title": "반도체 산업 성장", "label": 0})
    assert ynat["gold"] == 0 and len(ynat["choices"]) == 7
    nli = _ad_klue_nli({"premise": "비가 온다.", "hypothesis": "날씨가 맑다.", "label": 2})
    assert nli["gold"] == 2 and nli["choices"] == [" 함의", " 중립", " 모순"]
    specs_by_name = {row[0]: row for row in SPECS}
    assert specs_by_name["klue_ynat"][1:5] == ("klue/klue", "ynat", "validation", 9107)
    assert specs_by_name["klue_nli"][1:5] == ("klue/klue", "nli", "validation", 3000)
    print("[PASS] P097 multi-recipe data/arch routing and KLUE adapters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
