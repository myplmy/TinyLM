"""Literal preservation, actual consumer contract, and discovered content-stub negatives."""
from pathlib import Path
import sys
import unittest

AUDIT=Path(__file__).resolve().parent
sys.path[:0]=[str(AUDIT),str(AUDIT.parents[2])]
from verify_category_metadata_delta_v1 import evaluate,context_deferrals


class CategoryLiteral(unittest.TestCase):
    def values(self):
        source='《가람》()는 2015년 일본의 영화이다.\n\n출연\n김가람 - 주인공\n\n각주\n\n일본의 청춘 영화\n일본의 드라마 영화\n'
        clean=source.replace('()','').replace('\n각주\n','\n')
        return source,clean

    def test_year_free_metadata_and_filled_cast(self):
        self.assertTrue(evaluate(*self.values(),'EDIT')['eligible_narrow_literal_delta'])

    def test_populated_name_removal_is_rejected(self):
        a,b=self.values()
        self.assertFalse(evaluate(a,b.replace('김가람',''),'EDIT')['eligible_narrow_literal_delta'])

    def test_numeric_change_is_rejected(self):
        a,b=self.values()
        self.assertFalse(evaluate(a,b.replace('2015','2016'),'EDIT')['guards']['numeric_atoms'])

    def test_keep_releases_only_unchanged_terminal_body(self):
        _,b=self.values()
        self.assertTrue(evaluate(b,b,'KEEP')['eligible_narrow_literal_delta'])

    def test_stale_edit_contract_is_rejected(self):
        _,b=self.values()
        self.assertFalse(evaluate(b,b,'EDIT')['guards']['actual_terminal_body_contract'])

    def test_filled_reference_heading_cannot_be_stripped(self):
        a,b=self.values()
        a=a.replace('\n각주\n','\n참고 문헌\n김가람 2015\n')
        b=b.replace('\n일본의 청춘 영화','\n김가람 2015\n\n일본의 청춘 영화')
        self.assertFalse(evaluate(a,b,'EDIT')['eligible_narrow_literal_delta'])

    def test_no_typed_markers_is_rejected(self):
        a,b=self.values()
        a=a.replace('일본의 청춘 영화\n일본의 드라마 영화','가람\n나래')
        b=b.replace('일본의 청춘 영화\n일본의 드라마 영화','가람\n나래')
        self.assertFalse(evaluate(a,b,'EDIT')['guards']['independent_literal_category_markers'])

    def test_empty_content_head_before_date_free_metadata_is_held(self):
        a,b=self.values()
        a=a.replace('\n각주\n','\n수상자\n\n각주\n')
        b=b.replace('\n일본의 청춘 영화','\n수상자\n\n일본의 청춘 영화')
        self.assertIn('UNFILLED_CONTENT_HEADING_REMAINS',context_deferrals(b))
        self.assertFalse(evaluate(a,b,'EDIT')['eligible_narrow_literal_delta'])


if __name__=='__main__':
    unittest.main()
