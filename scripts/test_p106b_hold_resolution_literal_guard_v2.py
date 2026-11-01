#!/usr/bin/env python3
"""Exact-pair extension preserves original approvals and rejects borrowed ones."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_literal_guard_v2 as literal


class AdditionalLiteralPairs(unittest.TestCase):
    def setUp(self):
        self.cases = literal.load_registry()

    def texts(self, ident):
        row = self.cases[ident]
        return tuple((ROOT / row[key]).read_bytes().decode("utf-8") for key in ["original", "body"])

    def test_original_seven_approvals_are_preserved_exactly(self):
        original = literal.previous.load_registry()
        self.assertEqual(len(original), 7)
        self.assertEqual(len(self.cases), 10)
        for ident, value in original.items():
            self.assertEqual(self.cases[ident], value)

    def test_all_three_additions_match_the_exact_read_back_pair(self):
        for ident in literal.ADDITIONAL_IDS:
            with self.subTest(ident=ident):
                raw, clean = self.texts(ident)
                self.assertTrue(literal.exact_pair_preserved(raw, clean, ident, self.cases))

    def test_changed_original_cannot_borrow_a_source_approval(self):
        ident = "expanded_train:8455"
        raw, clean = self.texts(ident)
        self.assertFalse(literal.exact_pair_preserved(raw + "changed", clean, ident, self.cases))

    def test_changed_body_cannot_borrow_a_source_approval(self):
        ident = "expanded_train:8121"
        raw, clean = self.texts(ident)
        self.assertFalse(literal.exact_pair_preserved(raw, clean + "changed", ident, self.cases))

    def test_a_different_case_id_cannot_use_another_exact_pair(self):
        raw, clean = self.texts("expanded_train:36061")
        self.assertFalse(literal.exact_pair_preserved(raw, clean, "expanded_train:8455", self.cases))

    def test_an_unapproved_case_is_still_rejected(self):
        self.assertFalse(literal.exact_pair_preserved("```program", "program", "expanded_train:999", self.cases))


if __name__ == "__main__":
    unittest.main(verbosity=2)
