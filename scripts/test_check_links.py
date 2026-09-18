#!/usr/bin/env python3
"""Regression checks for the cross-platform document link checker."""
from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().with_name("check_links.py")
SPEC = importlib.util.spec_from_file_location("check_links_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_protected_relative_target_is_classified_without_io() -> None:
    source = MODULE.ROOT / "ai_dev_tool" / "20260909_report" / "report.md"
    assert MODULE._is_protected_target(
        source, "../../datasets/TinyDataset/docs/example.md"
    )
    assert not MODULE._is_protected_target(source, "../../docs/example.md")


def test_status_candidate_supports_ongoing_and_absorbed() -> None:
    ongoing = Path("proposal/item-approved-on-going.md")
    absorbed = Path("docs/review/item_absorbed.md")
    index = {
        ongoing.name: ongoing,
        absorbed.name: absorbed,
    }
    assert MODULE._status_candidate(index, "item.md") == ongoing

    index = {absorbed.name: absorbed}
    assert MODULE._status_candidate(index, "item.md") == absorbed


def test_ambiguous_candidates_are_not_auto_fixable() -> None:
    index: dict[str, Path | None] = {}
    MODULE._record_candidate(index, "same.md", Path("a/same.md"))
    MODULE._record_candidate(index, "same.md", Path("b/same.md"))
    assert index["same.md"] is None
    assert MODULE._status_candidate(index, "same.md") is None


def test_each_explicit_fix_mode_requests_persistence() -> None:
    assert MODULE._write_requested(True, False)
    assert MODULE._write_requested(False, True)
    assert MODULE._write_requested(True, True)
    assert not MODULE._write_requested(False, False)


def main() -> int:
    tests = [
        test_protected_relative_target_is_classified_without_io,
        test_status_candidate_supports_ongoing_and_absorbed,
        test_ambiguous_candidates_are_not_auto_fixable,
        test_each_explicit_fix_mode_requests_persistence,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"SUMMARY {len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
