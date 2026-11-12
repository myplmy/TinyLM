"""Inherited exact path denials plus explicit final-body prefix cases."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import exact_review_output_cell_alias_v2 as alias
from test_exact_review_output_cell_alias_v1 import CellAliasTests


class FinalPrefixTests(CellAliasTests):
    def test_original_registry_receives_both_adapter_levels(self):
        self.assertIs(alias.NORMALIZATIONS,alias.previous.NORMALIZATIONS)

    def output(self,value):
        entry=dict(number=5,header=['ID','판정','판독 범위','출력','근거'],
                   cells=['expanded_train:123','REVISE_TEXT','full EOF',value,'reason'])
        wrapped=alias.wrap_review_entries(lambda raw,allow_sections=False:[entry])
        return wrapped('unchanged original MD')[0]['cells'][3]

    def test_named_final_body_prefix_keeps_one_owned_path(self):
        for prefix in ['최종 파일','최종 본문']:
            value=self.output(prefix+' `revision_123.txt`')
            self.assertEqual(value,'revision_123.txt')
            self.assertEqual(self.bind(value),'revision_123.txt')

    def test_prefix_does_not_authorize_foreign_directory(self):
        value=self.output('최종 본문 `/tmp/foreign/revision_123.txt`')
        with self.assertRaises(ValueError):
            self.bind(value)

    def test_prefix_does_not_authorize_another_source_id(self):
        value=self.output('최종 본문 `revision_124.txt`')
        with self.assertRaises(ValueError):
            self.bind(value)


if __name__=='__main__':
    unittest.main(verbosity=2)
