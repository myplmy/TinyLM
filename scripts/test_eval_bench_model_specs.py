#!/usr/bin/env python3
"""CPU-only contracts for P097 multi-recipe benchmark routing."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.eval_bench_suite import (
    _ad_klue_nli,
    _ad_klue_ynat,
    _cloze_detail,
    _dump_items,
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
    cloze_item = {"_iid": "item-1", "gold": " answer"}
    good = _cloze_detail(cloze_item, (0.2, 0.4, 2), " answer")
    skipped = _cloze_detail({"_iid": "item-2", "gold": " other"}, None)
    assert good["correct"] == 1 and good["gold_sum_ce"] == 0.4
    assert good["gold_token_count"] == 2 and skipped["skipped"]
    assert skipped["reason"] == "empty_gold_or_context_overflow"
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "cloze.jsonl"
        _dump_items(output, "lambada", "fixture", {"rows": [good], "skip_rows": [skipped]})
        records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert [(row["id"], row["model"], row["task"]) for row in records] == [
        ("item-1", "fixture", "lambada"), ("item-2", "fixture", "lambada")
    ]
    print("[PASS] P097 routing, KLUE adapters and P069 cloze item ledger")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
