"""Regression checks for partial values, signs, and whole-value quarantine."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from numeric_atom_integrity_v1 import numeric_atom_changes


class NumericAtomTests(unittest.TestCase):
    def test_partial_twelve_is_flagged(self):
        self.assertTrue(numeric_atom_changes('거리 12km', '거리 1'))

    def test_decimal_suffix_loss_is_flagged(self):
        self.assertTrue(numeric_atom_changes('중력 9.8076 m/s2', '중력 9.8 m/s2'))

    def test_sign_loss_is_flagged(self):
        self.assertTrue(numeric_atom_changes('온도 −12 C', '온도 12 C'))

    def test_entire_value_quarantine_is_allowed(self):
        self.assertEqual(numeric_atom_changes('섬 12km\n다음 3km\n', '섬\n다음 3km\n'), [])

    def test_separate_values_cannot_merge(self):
        self.assertTrue(numeric_atom_changes('값 1 2', '값 12'))

    def test_existing_identical_value_does_not_hide_loss(self):
        self.assertTrue(numeric_atom_changes('첫째 1\n둘째 12km\n', '첫째 1\n둘째 1\n'))

    def test_unchanged_formulas_are_allowed(self):
        text='2^3 = 2*2*2\n비율 0.622\n'
        self.assertEqual(numeric_atom_changes(text, text), [])

    def test_fact_correction_still_needs_review(self):
        self.assertTrue(numeric_atom_changes('동경 137도', '동경 139도'))


if __name__ == '__main__':
    unittest.main()
