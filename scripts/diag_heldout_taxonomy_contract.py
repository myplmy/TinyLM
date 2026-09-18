#!/usr/bin/env python3
"""P096 Q1b — 여덟 relation taxonomy와 difficulty 계약의 합성 fixture."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tinylm.eval.heldout_contract import (  # noqa: E402
    RELATION_TAXONOMY,
    validate_panel,
)
from diag_heldout_contract import main as q1a_main  # noqa: E402


KNOBS = {
    "easy": {"hops": 1, "explicitness": "explicit", "competing_clues": 0,
             "distractor_distance": "far"},
    "mid": {"hops": 2, "explicitness": "explicit", "competing_clues": 1,
            "distractor_distance": "same_relation"},
    "hard": {"hops": 3, "explicitness": "implicit", "competing_clues": 2,
             "distractor_distance": "near"},
}
ERRORS = ("inverse", "necessary_sufficient", "temporal_reversal",
          "causal_correlation", "near_miss", "unsupported")


def make_item(relation, subtype, family_no, template_no, difficulty, ordinal):
    knobs = dict(KNOBS[difficulty])
    hops = knobs["hops"]
    nodes = [f"n{ordinal}-{i}" for i in range(hops + 1)]
    facts = [
        {"id": f"f{ordinal}-{i}", "subject": nodes[i], "relation": relation,
         "object": nodes[i + 1]}
        for i in range(hops)
    ]
    return {
        "id": f"q1b-{ordinal:03d}",
        "relation": relation,
        "relation_subtype": subtype,
        "family_id": f"{relation}-{subtype}-family-{family_no}",
        "template_id": f"{relation}-{subtype}-family-{family_no}-template-{template_no}",
        "facts": facts,
        "query_subject": nodes[0],
        "candidates": [nodes[-1], f"wrong-{ordinal}-a", f"wrong-{ordinal}-b"],
        "gold_index": 0,
        "gold_proof": {
            "rule": "direct" if hops == 1 else "transitive",
            "edge_ids": [fact["id"] for fact in facts],
        },
        "distractor_error_type": {
            "1": ERRORS[ordinal % len(ERRORS)],
            "2": ERRORS[(ordinal + 1) % len(ERRORS)],
        },
        "difficulty_target": difficulty,
        "difficulty_knobs": knobs,
    }


def fixture_panel():
    items = []
    ordinal = 0
    cycle = ("easy", "mid", "hard", "mid", "hard", "easy", "hard", "mid", "easy", "hard")
    for relation, subtypes in RELATION_TAXONOMY.items():
        for subtype in subtypes:
            for family_no in range(5):
                for template_no in range(2):
                    difficulty = cycle[(family_no * 2 + template_no) % len(cycle)]
                    items.append(make_item(
                        relation, subtype, family_no, template_no, difficulty, ordinal
                    ))
                    ordinal += 1
    return items


def main() -> int:
    assert q1a_main() == 0
    panel = fixture_panel()
    assert len(panel) == 8 * 4 * 5 * 2
    errors = validate_panel(panel, require_full_taxonomy=True)
    assert errors == [], "\n".join(errors)

    bad_knob = copy.deepcopy(panel)
    bad_knob[0]["difficulty_knobs"]["hops"] = 3
    assert any("target/knobs 불일치" in error for error in validate_panel(
        bad_knob, require_full_taxonomy=True
    ))

    bad_path = copy.deepcopy(panel)
    bad_path[1]["gold_proof"]["edge_ids"] = list(reversed(
        bad_path[1]["gold_proof"]["edge_ids"]
    ))
    assert any("연속 경로" in error for error in validate_panel(
        bad_path, require_full_taxonomy=True
    ))

    missing_subtype = [
        item for item in panel
        if not (item["relation"] == "조건" and item["relation_subtype"] == "independent")
    ]
    assert any("subtype coverage" in error for error in validate_panel(
        missing_subtype, require_full_taxonomy=True
    ))

    print(
        "[PASS] P096 Q1b: relations=8 subtypes=32 fixtures=320 "
        "difficulty=easy/mid/hard family/template-cap<=5%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
