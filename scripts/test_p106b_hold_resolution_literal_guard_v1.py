#!/usr/bin/env python3
"""Exact source/body, evidence scope and actual program preservation checks."""
from pathlib import Path
import copy
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_literal_guard_v1 as guard


class ExactLiteralExceptions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = guard.load_registry()

    def texts(self, ident="expanded_train:1242413"):
        row = self.cases[ident]
        return tuple((ROOT / row[key]).read_bytes().decode("utf-8") for key in ["original", "body"])

    def test_all_seven_actual_reviewed_pairs_and_unicode(self):
        for ident in self.cases:
            with self.subTest(ident=ident):
                original, clean = self.texts(ident)
                self.assertTrue(guard.exact_pair_preserved(original, clean, ident, self.cases))

    def test_an_altered_original_is_not_the_reviewed_source(self):
        original, clean = self.texts()
        self.assertFalse(guard.exact_pair_preserved(original + "x", clean, "expanded_train:1242413", self.cases))

    def test_an_altered_body_is_not_automatically_approved(self):
        original, clean = self.texts()
        self.assertFalse(guard.exact_pair_preserved(original, clean + "x", "expanded_train:1242413", self.cases))

    def test_a_different_case_id_cannot_borrow_an_exception(self):
        original, clean = self.texts()
        self.assertFalse(guard.exact_pair_preserved(original, clean, "expanded_train:1", self.cases))

    def test_a_lost_program_is_rejected_even_if_the_body_hash_is_rebound(self):
        original, clean = self.texts()
        altered = clean.replace("cxyN = cohere(x,y,N);", "")
        cases = copy.deepcopy(self.cases)
        cases["expanded_train:1242413"]["clean_text_sha256"] = guard.sha(altered.encode("utf-8"))
        self.assertFalse(guard.exact_pair_preserved(original, altered, "expanded_train:1242413", cases))

    def test_unicode_guard_cannot_be_overridden_by_a_reviewed_pair(self):
        original, clean = self.texts()
        with patch.object(guard.policy, "unicode_examples_preserved", return_value=False):
            self.assertFalse(guard.exact_pair_preserved(original, clean, "expanded_train:1242413", self.cases))

    def test_unapproved_case_is_rejected(self):
        original, clean = self.texts()
        cases = copy.deepcopy(self.cases)
        cases["expanded_train:1242413"]["root_approved"] = False
        self.assertFalse(guard.exact_pair_preserved(original, clean, "expanded_train:1242413", cases))

    def test_registry_byte_change_fails_before_loading_evidence(self):
        with patch.object(guard, "REGISTRY_SHA256", "0" * 64):
            with self.assertRaisesRegex(ValueError, "registry changed"):
                guard.load_registry()


if __name__ == "__main__":
    unittest.main(verbosity=2)
