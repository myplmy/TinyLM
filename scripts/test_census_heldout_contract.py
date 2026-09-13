#!/usr/bin/env python3
"""GPU-free regression tests for the held-out census persistence contract."""
from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().with_name("census_heldout_discrimination.py")
SPEC = importlib.util.spec_from_file_location("census_contract_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_pairs_keep_discordance_and_family_ci() -> None:
    per_ok = {"a": [True, False, True], "b": [False, False, True]}

    def fake_ci(ok_a, ok_b, relations):
        assert ok_a == [True, False, True]
        assert ok_b == [False, False, True]
        assert relations == ["r1", "r1", "r2"]
        return 0.05, 0.25, 2

    rows = MODULE.pair_records(per_ok, ["a", "b"], ["r1", "r1", "r2"], 3,
                               ci_fn=fake_ci)
    assert rows == [{
        "a": "a", "b": "b", "a_only": 1, "b_only": 0, "discordant": 1,
        "family_count": 2, "family_ci95": [0.05, 0.25],
        "family_verdict": "a_better",
    }]


def test_family_ci_withheld_is_explicit() -> None:
    rows = MODULE.pair_records(
        {"a": [True], "b": [False]}, ["a", "b"], ["only"], 1,
        ci_fn=lambda *_: (None, None, 1),
    )
    assert rows[0]["family_ci95"] is None
    assert rows[0]["family_verdict"] == "withheld"


def main() -> int:
    tests = [test_pairs_keep_discordance_and_family_ci, test_family_ci_withheld_is_explicit]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"SUMMARY {len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
