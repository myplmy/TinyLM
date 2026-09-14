#!/usr/bin/env python3
"""GPU-free regression tests for paired held-out census comparison."""
from __future__ import annotations

import copy
import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import compare_heldout_census as compare  # noqa: E402


def _document(version: str, rows: dict[str, list[bool]], *, signature: bool = True) -> dict:
    ids = ["a", "b", "c", "d"]
    models = list(rows)
    rates = [sum(rows[model][i] for model in models) / len(models) for i in range(len(ids))]
    doc = {
        "schema_version": 2,
        "task": "stage1_heldout",
        "heldout_version": version,
        "n": len(ids),
        "n_ckpt": len(models),
        "models": models,
        "ids": ids,
        "per_ok": rows,
        "per_item_rate": rates,
        "item_labels": [
            {"id": "a", "relation": "r1", "relation_subtype": "s1",
             "family_id": "f1", "difficulty": "easy"},
            {"id": "b", "relation": "r1", "relation_subtype": "s1",
             "family_id": "f1", "difficulty": "mid"},
            {"id": "c", "relation": "r2", "relation_subtype": "s2",
             "family_id": "f2", "difficulty": "hard"},
            {"id": "d", "relation": "r2", "relation_subtype": "s2",
             "family_id": "f2", "difficulty": "mid"},
        ],
    }
    if signature:
        doc["condition_signature"] = {
            "dataset": {
                "task": "stage1_heldout",
                "heldout_version_resolved": version,
                "ids_sha256": "same-ids",
                "content_sha256": version + "-content",
            },
            "sample": {
                "actual_n": 4, "source_rows": 4, "seed": 99,
                "covers_all_rows": True,
            },
            "evaluation": {
                "data": "ko-en", "tokens": "300M", "seq_max": 1024,
                "pmi": True, "device": "cuda",
            },
            "models": [
                {"tag": model, "preset": "tiny", "checkpoint": model + ".pt",
                 "checkpoint_size_bytes": 10}
                for model in models
            ],
            "code_revision": {
                "scripts/census_heldout_discrimination.py": "same-census",
                "scripts/eval_bench_suite.py": "same-eval",
            },
        }
    return doc


def test_full_signature_paired_comparison_and_direction() -> None:
    baseline = _document("2.9", {
        "m1": [True, True, False, False],
        "m2": [True, False, False, True],
    })
    candidate = _document("3.0", {
        "m1": [True, True, False, False],
        "m2": [True, True, False, False],
    })
    report = compare.compare_documents(baseline, candidate)
    assert report["comparison_status"] == "FULL_SIGNATURE_MATCH"
    assert report["directional_verdict"] == "CORE_REGRESSION"
    assert report["delta_candidate_minus_baseline"]["d9"] < 0
    assert report["delta_candidate_minus_baseline"]["zero_info_rate"] > 0
    assert report["delta_candidate_minus_baseline"]["bits_total"] < 0
    assert report["baseline_label_projection"]["relation"]["status"].startswith("AVAILABLE")
    assert report["baseline_label_projection"]["family_id"]["status"].startswith("AVAILABLE")
    assert report["dataset_identity"]["baseline_content_sha256"] == "2.9-content"


def test_candidate_id_order_is_repaired_by_id() -> None:
    baseline = _document("2.9", {
        "m1": [True, False, True, False],
        "m2": [False, True, True, False],
    })
    candidate = copy.deepcopy(baseline)
    candidate["heldout_version"] = "3.0"
    candidate["condition_signature"]["dataset"]["heldout_version_resolved"] = "3.0"
    order = [2, 0, 3, 1]
    candidate["ids"] = [candidate["ids"][i] for i in order]
    candidate["per_item_rate"] = [candidate["per_item_rate"][i] for i in order]
    candidate["per_ok"] = {
        model: [values[i] for i in order]
        for model, values in candidate["per_ok"].items()
    }
    candidate["item_labels"] = [candidate["item_labels"][i] for i in order]
    report = compare.compare_documents(baseline, candidate)
    assert report["ids_equal_in_order"] is False
    assert report["directional_verdict"] == "NO_CORE_REGRESSION"
    assert all(row["rate_delta"] == 0 for row in report["per_item_transition"])


def test_legacy_metadata_gap_requires_explicit_opt_in() -> None:
    baseline = _document("2.9", {"m1": [True] * 4, "m2": [False] * 4})
    candidate = _document("3.0", {"m1": [True] * 4, "m2": [False] * 4}, signature=False)
    try:
        compare.compare_documents(baseline, candidate)
    except compare.ComparisonError as exc:
        assert "--allow-legacy-metadata-gap" in str(exc)
    else:
        raise AssertionError("legacy metadata gap was accepted without opt-in")
    report = compare.compare_documents(baseline, candidate, allow_legacy=True)
    assert report["comparison_status"] == "CORE_MATCH_LEGACY_METADATA_GAP"
    assert report["metadata_gaps"][0] == "candidate.condition_signature"
    assert any("pmi" in gap for gap in report["metadata_gaps"])


def test_signature_mismatch_is_rejected() -> None:
    baseline = _document("2.9", {"m1": [True] * 4, "m2": [False] * 4})
    candidate = _document("3.0", {"m1": [True] * 4, "m2": [False] * 4})
    candidate["condition_signature"]["evaluation"]["pmi"] = False
    try:
        compare.compare_documents(baseline, candidate)
    except compare.ComparisonError as exc:
        assert "evaluation.pmi" in str(exc)
    else:
        raise AssertionError("condition mismatch was accepted")


def test_evaluation_source_mismatch_is_rejected() -> None:
    baseline = _document("2.9", {"m1": [True] * 4, "m2": [False] * 4})
    candidate = _document("3.0", {"m1": [True] * 4, "m2": [False] * 4})
    candidate["condition_signature"]["code_revision"][
        "scripts/census_heldout_discrimination.py"
    ] = "different-census"
    try:
        compare.compare_documents(baseline, candidate)
    except compare.ComparisonError as exc:
        assert "evaluation_source_hashes" in str(exc)
    else:
        raise AssertionError("evaluation source mismatch was accepted")


def test_recorded_rate_must_match_per_ok() -> None:
    baseline = _document("2.9", {"m1": [True] * 4, "m2": [False] * 4})
    baseline["per_item_rate"][0] = 0.0
    try:
        compare.compare_documents(baseline, copy.deepcopy(baseline))
    except compare.ComparisonError as exc:
        assert "per_item_rate" in str(exc)
    else:
        raise AssertionError("inconsistent rate was accepted")


def main() -> int:
    tests = [
        test_full_signature_paired_comparison_and_direction,
        test_candidate_id_order_is_repaired_by_id,
        test_legacy_metadata_gap_requires_explicit_opt_in,
        test_signature_mismatch_is_rejected,
        test_evaluation_source_mismatch_is_rejected,
        test_recorded_rate_must_match_per_ok,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"SUMMARY {len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
