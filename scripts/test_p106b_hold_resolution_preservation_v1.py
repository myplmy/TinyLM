#!/usr/bin/env python3
"""Counterexamples for missing glyphs and exact nonprogram delimiters."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_preservation_v1 as policy
from scripts import p106b_hold_resolution_literal_guard_v3 as literal


class UnicodeSourceValues(unittest.TestCase):
    def test_empty_example_delimiters_may_go_while_the_value_stays(self):
        self.assertTrue(policy.unicode_examples_preserved("U+1B001()", "U+1B001"))

    def test_whitespace_inside_absent_example_is_not_a_glyph(self):
        self.assertTrue(policy.unicode_examples_preserved("U+1B001( )", "U+1B001"))

    def test_a_real_example_cannot_disappear(self):
        self.assertFalse(policy.unicode_examples_preserved("U+1B001(𛀁)", "U+1B001"))

    def test_codepoint_value_cannot_disappear(self):
        self.assertFalse(policy.unicode_examples_preserved("U+1B001()", "YE"))

    def test_an_absent_glyph_is_not_generated_from_the_codepoint(self):
        self.assertFalse(policy.unicode_examples_preserved("U+1B001()", "U+1B001(𛀁)"))

    def test_one_real_glyph_does_not_excuse_another_loss(self):
        self.assertFalse(policy.unicode_examples_preserved("U+1B001(𛀁) U+1B000()", "U+1B001 U+1B000"))

    def test_a_real_example_does_not_license_filling_a_second_empty_one(self):
        self.assertFalse(policy.unicode_examples_preserved(
            "U+1B001(𛀁) U+1B001()", "U+1B001(𛀁) U+1B001(X)"))

    def test_real_example_stays_while_second_empty_delimiters_go(self):
        self.assertTrue(policy.unicode_examples_preserved(
            "U+1B001(𛀁) U+1B001()", "U+1B001(𛀁) U+1B001"))

    def test_source_pinned_actual_kana_body_retains_real_values(self):
        import json
        audit = json.loads((ROOT / "handoff/audit/hold_resolution_20261027_goalc/root_selected_body_literals_v2.json").read_text())
        row = next(row for row in audit["records"] if row["id"] == "expanded_train:48585")
        raw = (ROOT / row["compare_source"]["path"]).read_text()
        clean = (ROOT / row["body"]).read_text()
        self.assertTrue(policy.unicode_examples_preserved(raw, clean))


class ExactSearchUI(unittest.TestCase):
    def test_approved_dictionary_pair_and_original_ten_cases_are_pinned(self):
        cases = literal.load_registry()
        self.assertEqual(len(cases), 11)
        row = cases["expanded_train:6773"]
        raw = (ROOT / row["original"]).read_text()
        clean = (ROOT / row["body"]).read_text()
        self.assertTrue(literal.exact_pair_preserved(raw, clean, row["id"], cases))
        self.assertFalse(literal.exact_pair_preserved(raw, clean + " ", row["id"], cases))
        self.assertFalse(literal.exact_pair_preserved(raw, clean, "expanded_train:6774", cases))

    def test_an_actual_search_program_is_not_the_source_pinned_ui(self):
        cases = literal.load_registry()
        self.assertFalse(literal.exact_pair_preserved("run(`Search`);", "run();", "expanded_train:6773", cases))


if __name__ == "__main__":
    unittest.main(verbosity=2)
