"""Keep missing-decision rejection while ignoring references in an explanation."""
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.p106b_hold_resolution_review_safeguards_v4 import unparsed_declared_review_ids as check


class ReviewDeclarationTests(unittest.TestCase):
    def test_reason_reference_does_not_declare(self):
        payload = '| expanded_train:888524 | ACCEPT_CANDIDATE | old pointer expanded_train:98341 |'
        self.assertEqual(check(payload, {'expanded_train:888524'}, {'expanded_train:888524', 'expanded_train:98341'}), set())

    def test_missing_actual_table_row_stays_rejected(self):
        payload = '| expanded_train:98341 | REVISE_TEXT | unparsed output |'
        self.assertEqual(check(payload, set(), {'expanded_train:98341'}), {'expanded_train:98341'})

    def test_missing_heading_stays_rejected(self):
        self.assertEqual(check('## expanded_train:98341' + chr(10) + 'NEEDS_ROOT', set(), {'expanded_train:98341'}), {'expanded_train:98341'})

    def test_missing_bare_label_stays_rejected(self):
        self.assertEqual(check('ID: 98341' + chr(10) + 'REVISE_TEXT', set(), {'expanded_train:98341'}), {'expanded_train:98341'})

    def test_parsed_actual_row_not_unsupported(self):
        self.assertEqual(check('| expanded_train:98341 | ACCEPT_CANDIDATE |', {'expanded_train:98341'}, {'expanded_train:98341'}), set())

    def test_incidental_prose_unchanged(self):
        self.assertEqual(check('Old expanded_train:98341 is mentioned; REVISE_TEXT elsewhere.', set(), {'expanded_train:98341'}), set())

    def test_both_actual_and_reference(self):
        p = '| expanded_train:888524 | ACCEPT_CANDIDATE | old expanded_train:98341 |' + chr(10)
        p += '| expanded_train:98341 | NEEDS_ROOT | missing row |'
        self.assertEqual(check(p, {'expanded_train:888524'}, {'expanded_train:888524', 'expanded_train:98341'}), {'expanded_train:98341'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
