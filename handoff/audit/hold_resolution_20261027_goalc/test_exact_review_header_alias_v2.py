"""Actual page-row regression plus the unchanged v1 negative binding cases."""
from pathlib import Path
import sys
import unittest

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
import test_exact_review_header_alias_v1 as prior
from exact_review_header_alias_v2 import wrap_review_entries

prior.wrap_review_entries = wrap_review_entries


class ExpandedOutputHeaderTests(prior.OutputHeaderTests):
    def test_actual_fifty_five_page_rows_keep_raw_bytes_and_bind_explicit_column(self):
        directory = prior.inv.BASE / 'agents/context_hangul/remaining_field_title_page_002_counter_v1'
        sources = {r['id']: r for r in prior.inv.cache.read(
            prior.inv.BASE / 'remaining_field_title_page_002_counter_v1/manifest.json')['rows']}
        checked = 0
        for number in range(2, 13):
            name = 'review_003_v2.md' if number == 3 else 'review_' + str(number).zfill(3) + '.md'
            path = directory / name
            before = path.read_bytes()
            old = self.original(before)
            new = self.wrapped(before)
            self.assertEqual(len(new), 5)
            for previous, entry in zip(old, new):
                self.assertEqual(previous['raw'], entry['raw'])
                self.assertEqual(previous['cells'], entry['cells'])
                self.assertEqual(entry['header'][3], '출력')
                ident = entry['cells'][0]
                row = sources[ident]
                self.assertNotIn(ident, self.contract['restricted_ids'])
                self.assertNotIn(row['original']['sha256'], self.contract['restricted_hashes'])
                absolute = {key: dict(row[key], path=str(prior.ROOT / row[key]['path']))
                            for key in ('original', 'candidate')}
                decision = {'REVISE_TEXT': 'EDIT_TEXT', 'ACCEPT_CANDIDATE': 'ADOPT_CANDIDATE'}[entry['cells'][1]]
                name = prior.bindings.declared_txt_basename(entry['cells'][3], ident, directory, absolute, decision)
                self.assertTrue(name.endswith('.txt'))
                checked += 1
            self.assertEqual(path.read_bytes(), before)
        self.assertEqual(checked, 55)

    def test_two_registered_alias_columns_are_rejected(self):
        payload = ('| ID | 판정 | 출력 TXT | 출력 (TXT basename) |' + chr(10)
                   + '| expanded_train:10981 | REVISE_TEXT | one.txt | two.txt |').encode()
        with self.assertRaisesRegex(ValueError, 'AMBIGUOUS_EXPLICIT_OUTPUT_HEADERS'):
            self.wrapped(payload)


if __name__ == '__main__':
    unittest.main(verbosity=2)
