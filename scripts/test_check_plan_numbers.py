#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("check_plan_numbers.py")
SPEC = importlib.util.spec_from_file_location("check_plan_numbers", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class DiagnosticReferenceTests(unittest.TestCase):
    def test_exact_diagnostic_path_is_removed_but_original_remains(self):
        refs = {"P091": {"draft.md", "report.md"}}
        missing, diagnostic = MODULE.unresolved_refs(
            refs, have={}, diagnostic_refs={("P091", "report.md"): "explains failure"}
        )
        self.assertEqual(missing, {"P091": ["draft.md"]})
        self.assertEqual(diagnostic, {"P091": ["report.md"]})

    def test_diagnostic_entry_does_not_exempt_other_number_or_file(self):
        refs = {"P091": {"other.md"}, "P092": {"report.md"}}
        missing, _ = MODULE.unresolved_refs(
            refs, have={}, diagnostic_refs={("P091", "report.md"): "narrow"}
        )
        self.assertEqual(missing, {"P091": ["other.md"], "P092": ["report.md"]})

    def test_existing_plan_wins_before_diagnostic_filter(self):
        missing, diagnostic = MODULE.unresolved_refs(
            {"P091": {"report.md"}}, have={"P091": ["P091_x.md"]},
            diagnostic_refs={("P091", "report.md"): "old diagnostic"},
        )
        self.assertEqual((missing, diagnostic), ({}, {}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
