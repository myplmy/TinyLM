"""Only exact explicit metadata aliases may change parser interpretation."""
from pathlib import Path
import sys
import unittest

AUDIT=Path(__file__).resolve().parent
sys.path[:0]=[str(AUDIT),str(AUDIT.parents[2])]
import exact_review_output_cell_alias_v3 as current
from scripts.p106b_hold_resolution_author_output_bindings_v1 import declared_txt_basename


class ExplicitMarkdownOutputTests(unittest.TestCase):
    def entry(self,output,header=None):
        header=header or ['ID','판정','범위','원문 SHA-256','새 본문 / 선택 경로','메모']
        return dict(number=1,header=header,cells=['expanded_train:12','REVISE_TEXT','EOF','A'*64,output,'이유'])

    def normalize(self,entry):
        return current.wrap_review_entries(lambda *args,**kwargs:[entry])(b'metadata')[0]

    def test_exact_extra_sha_column_and_local_link(self):
        row=self.normalize(self.entry('[revised body](expanded_train_12_revised_v1.txt)'))
        self.assertEqual(row['header'][4],'출력')
        self.assertEqual(row['cells'][4],'expanded_train_12_revised_v1.txt')
        self.assertEqual(row['cells'][3],'A'*64)

    def test_plain_explicit_path_and_status_are_unchanged(self):
        entry=self.entry('/tmp/expanded_train_12_final.txt');row=self.normalize(entry)
        self.assertEqual(row['cells'],entry['cells'])

    def test_other_observed_exact_new_body_heading_is_recognized(self):
        row=self.normalize(self.entry('[revised body](expanded_train_12_revised_v1.txt)',
            ['ID','판정','원문 판독 범위','SHA-256','새 본문','판정 메모']))
        self.assertEqual(row['header'][4],'출력')
        self.assertEqual(row['cells'][4],'expanded_train_12_revised_v1.txt')

    def test_another_id_or_traversal_is_not_normalized(self):
        for value in ['[body](expanded_train_13_final.txt)','[body](../expanded_train_12_final.txt)',
                      '[body](/tmp/expanded_train_12_final.txt)']:
            self.assertEqual(self.normalize(self.entry(value))['cells'][4],value)

    def test_two_links_or_extra_tokens_are_not_guessed(self):
        for value in ['[a](expanded_train_12_a.txt) [b](expanded_train_12_b.txt)',
                      '[a](expanded_train_12_a.txt) sidecar.md']:
            self.assertEqual(self.normalize(self.entry(value))['cells'][4],value)

    def test_duplicate_output_columns_are_rejected(self):
        with self.assertRaises(ValueError):self.normalize(self.entry('x',
            ['ID','판정','범위','정확 출력','새 본문 / 선택 경로','메모']))

    def test_existing_exact_directory_and_same_id_binding_remains(self):
        root=AUDIT.parents[2];directory=root/'data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/legacy_review/cohort'
        row=self.normalize(self.entry('[body](expanded_train_12_final.txt)'))
        self.assertEqual(declared_txt_basename(row['cells'][4],'expanded_train:12',directory,{},'EDIT_TEXT'),
            'expanded_train_12_final.txt')
        with self.assertRaises(ValueError):declared_txt_basename('/tmp/expanded_train_12_final.txt',
            'expanded_train:12',directory,{},'EDIT_TEXT')


if __name__=='__main__':unittest.main()
