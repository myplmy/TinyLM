#!/usr/bin/env python3
"""P096 Q2 bounded candidate/provenance contract on synthetic Q1b items."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from diag_heldout_taxonomy_contract import fixture_panel
from tinylm.eval.heldout_canary import validate_candidate_bundle


def main() -> int:
    baseline = fixture_panel()
    candidates = []
    for item in baseline:
        candidate = copy.deepcopy(item)
        candidate["provenance"] = {
            "source_id": item["id"],
            "candidate_id": item["id"] + "-candidate-a",
            "generation_rule": "synthetic-contract-only",
            "preserved": False,
        }
        candidates.append(candidate)
    assert validate_candidate_bundle(baseline, candidates) == []

    preserved = copy.deepcopy(baseline[0])
    preserved["provenance"] = {
        "source_id": baseline[0]["id"],
        "candidate_id": baseline[0]["id"] + "-preserved",
        "generation_rule": "preserve-valid-id",
        "preserved": True,
    }
    assert validate_candidate_bundle(baseline, [preserved]) == []

    too_many = copy.deepcopy(candidates[:3])
    for suffix in ("b", "c"):
        extra = copy.deepcopy(candidates[0])
        extra["provenance"]["candidate_id"] += suffix
        too_many.append(extra)
    assert any("candidates=" in error for error in validate_candidate_bundle(
        baseline, too_many, max_per_slot=2
    ))
    unknown = copy.deepcopy(candidates)
    unknown[0]["provenance"]["source_id"] = "missing"
    assert any("unknown source_id" in error for error in validate_candidate_bundle(baseline, unknown))
    print(f"[PASS] P096 Q2: baseline_slots={len(baseline)} candidates={len(candidates)} "
          "max_slots=450 max_candidates_per_slot=2 provenance/preservation/semantic-contract")
    print("NOTE: actual protected items, text generation, team semantic review and GPU panel remain NOT_RUN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
