"""Actual review regression and fail-closed output-column tests; no source bodies."""
from pathlib import Path
import re
import sys
import unittest

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_author_output_bindings_v1 as bindings
from collect_exact_cohort_reviews_v5 import load_reused
from exact_review_header_alias_v1 import wrap_review_entries


class OutputHeaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        environment=load_reused(AUDIT/'collect_supplemental_candidates_v63.py',dict(re=re,inv=inv,Path=Path))
        cls.original=staticmethod(environment['review_entries'])
        cls.wrapped=staticmethod(wrap_review_entries(environment['review_entries']))
        cls.directory=inv.BASE/'agents/context_latin/remaining_literal_full_counter_v1'
        cls.sources={row['id']:row for row in inv.cache.read(inv.BASE/'remaining_literal_full_counter_v1/manifest.json')['rows']}
        cls.contract=inv.cache.read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')

    def test_actual_twenty_five_rows_bind_only_explicit_output(self):
        checked=0
        for number in range(61,66):
            path=self.directory/('review_'+str(number).zfill(3)+'.md')
            before=path.read_bytes()
            old=self.original(before);new=self.wrapped(before)
            self.assertEqual(len(new),5)
            for previous,entry in zip(old,new):
                self.assertEqual(previous['cells'],entry['cells'])
                self.assertEqual(previous['raw'],entry['raw'])
                self.assertEqual(entry['header'][3],'출력')
                ident=entry['cells'][0];source=self.sources[ident]
                self.assertNotIn(ident,self.contract['restricted_ids'])
                self.assertNotIn(source['original']['sha256'],self.contract['restricted_hashes'])
                absolute={key:dict(source[key],path=str(ROOT/source[key]['path'])) for key in ('original','candidate')}
                decision={'REVISE_TEXT':'EDIT_TEXT','ACCEPT_CANDIDATE':'ADOPT_CANDIDATE'}[entry['cells'][1]]
                name=bindings.declared_txt_basename(entry['cells'][3],ident,self.directory,absolute,decision)
                self.assertTrue(name.endswith('.txt'))
                checked+=1
            self.assertEqual(path.read_bytes(),before)
        self.assertEqual(checked,25)

    def test_original_output_header_is_unchanged(self):
        payload=('| ID | 판정 | 범위 | 출력 | 근거 |'+chr(10)+
                 '| expanded_train:822377 | REVISE_TEXT | 읽음 | reviewed_822377_task061_v3.txt | 근거 |').encode()
        self.assertEqual(self.wrapped(payload),self.original(payload))

    def test_two_explicit_output_columns_are_rejected(self):
        payload=('| ID | 판정 | 출력 | 출력 TXT |'+chr(10)+
                 '| expanded_train:822377 | REVISE_TEXT | one.txt | two.txt |').encode()
        with self.assertRaisesRegex(ValueError,'AMBIGUOUS_EXPLICIT_OUTPUT_HEADERS'):
            self.wrapped(payload)

    def test_rationale_file_name_is_not_promoted_to_body(self):
        payload=('| ID | 판정 | 범위 | 출력 TXT | 근거 |'+chr(10)+
                 '| expanded_train:822377 | REVISE_TEXT | 읽음 | — | reviewed_822377_task061_v3.txt |').encode()
        row=self.wrapped(payload)[0]
        with self.assertRaisesRegex(ValueError,'NO_EXACT_BODY_OUTPUT_PATH'):
            bindings.declared_txt_basename(row['cells'][3],row['cells'][0],self.directory,{},'EDIT_TEXT')

    def test_unregistered_heading_is_not_guessed(self):
        payload=('| ID | 판정 | 범위 | 출력물 추측 | 근거 |'+chr(10)+
                 '| expanded_train:822377 | REVISE_TEXT | 읽음 | reviewed_822377_task061_v3.txt | 근거 |').encode()
        self.assertEqual(self.wrapped(payload)[0]['header'][3],'출력물 추측')
        with self.assertRaisesRegex(ValueError,'NO_EXACT_BODY_OUTPUT_PATH'):
            bindings.declared_txt_basename(self.wrapped(payload)[0]['raw'],'expanded_train:822377',self.directory,{},'EDIT_TEXT')


if __name__=='__main__':
    unittest.main(verbosity=2)
