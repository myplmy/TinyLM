from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lter_table_identity_v1 import START, END, FIELDS, prove_table


class LterTableTests(unittest.TestCase):
    def setUp(self):
        self.raw = ('First introduction.' + chr(10) + 'Second introduction.' + chr(10)
            + 'Unusable script claim.' + chr(10) + 'library(maps) # comment ' + START
            + ' 0 0 Alpha LTER (ALP) 1.20 -2.30 Beta LTER (BET) -4.50 6.70 '
            + END + ' ' + FIELDS)
        self.body = ('First introduction.' + chr(10) + 'Second introduction.' + chr(10)
            + chr(10) + 'LTER sites' + chr(10) * 2 + '| sites | lat | long |' + chr(10)
            + '|---|---:|---:|' + chr(10) + '| Alpha LTER (ALP) | 1.20 | -2.30 |' + chr(10)
            + '| Beta LTER (BET) | -4.50 | 6.70 |' + chr(10))

    def test_exact_names_fields_values_order(self):
        self.assertEqual(prove_table(self.raw, self.body)['rows_checked'], 2)

    def rejected(self, text):
        with self.assertRaises(ValueError): prove_table(self.raw, text)

    def test_missing_name_word_rejected(self):
        self.rejected(self.body.replace('Alpha LTER (ALP)', 'Alpha (ALP)'))

    def test_latitude_longitude_swap_rejected(self):
        self.rejected(self.body.replace('1.20 | -2.30', '-2.30 | 1.20'))

    def test_negative_sign_loss_rejected(self):
        self.rejected(self.body.replace('-4.50', '4.50'))

    def test_precision_spelling_change_rejected(self):
        self.rejected(self.body.replace('1.20', '1.2'))

    def test_duplicate_row_rejected(self):
        self.rejected(self.body.replace('Beta LTER (BET) | -4.50 | 6.70', 'Alpha LTER (ALP) | 1.20 | -2.30'))

    def test_missing_row_rejected(self):
        self.rejected(self.body.replace('| Beta LTER (BET) | -4.50 | 6.70 |', ''))

    def test_changed_intro_rejected(self):
        self.rejected(self.body.replace('Second introduction.', 'Added claim.'))

    def test_added_unnamed_row_rejected(self):
        self.rejected(self.body + '| invented | 0 | 0 |')

    def test_changed_source_field_binding_rejected(self):
        with self.assertRaises(ValueError): prove_table(self.raw.replace(FIELDS, 'unknown fields'), self.body)

    def test_ambiguous_source_boundary_rejected(self):
        with self.assertRaises(ValueError): prove_table(self.raw.replace('Beta LTER (BET)', 'Beta LTER'), self.body)


if __name__ == '__main__': unittest.main()
