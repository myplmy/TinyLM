#!/usr/bin/env python3
"""P096 Q1 — 보호 데이터 없이 schema/proof/ambiguity negative fixture를 검증한다."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tinylm.eval.heldout_contract import validate_panel


def fixture():
    return {
        "id": "synthetic-001",
        "relation": "ancestor",
        "relation_subtype": "two_hop",
        "family_id": "family-a",
        "template_id": "template-1",
        "facts": [
            {"id": "f1", "subject": "A", "relation": "ancestor", "object": "B"},
            {"id": "f2", "subject": "B", "relation": "ancestor", "object": "C"},
        ],
        "query_subject": "A",
        "candidates": ["C", "D", "E"],
        "gold_index": 0,
        "gold_proof": {"rule": "transitive", "edge_ids": ["f1", "f2"]},
        "distractor_error_type": {"1": "unsupported", "2": "near_miss"},
        "difficulty_target": "mid",
        "difficulty_knobs": {
            "hops": 2, "explicitness": "implicit", "competing_clues": 1,
            "distractor_distance": "near",
        },
    }


def main() -> int:
    valid = fixture()
    assert validate_panel([valid]) == []

    ambiguous = copy.deepcopy(valid)
    ambiguous["id"] = "synthetic-ambiguous"
    ambiguous["facts"].append(
        {"id": "f3", "subject": "A", "relation": "ancestor", "object": "D"})
    assert any("정답 유일성 실패" in e for e in validate_panel([ambiguous]))

    false_gold = copy.deepcopy(valid)
    false_gold["id"] = "synthetic-false-gold"
    false_gold["gold_index"] = 1
    assert any("정답 유일성 실패" in e for e in validate_panel([false_gold]))

    missing = copy.deepcopy(valid)
    missing["id"] = "synthetic-missing"
    del missing["family_id"]
    assert any("missing fields" in e for e in validate_panel([missing]))

    assert any("duplicate id" in e for e in validate_panel([valid, valid]))
    print("[PASS] P096 Q1: schema, unique proof, distractor labels, negative fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
