"""Check conservative deferrals without rewriting any source."""
from pathlib import Path
import sys
import unittest

AUDIT = Path(__file__).resolve().parent
sys.path[:0] = [str(AUDIT), str(AUDIT.parents[2])]
from authored_literal_readiness_v1 import deferrals


class Readiness(unittest.TestCase):
    def test_truncated_complete_paragraph_tail_is_deferred(self):
        value = '클래식 기타의 수명은 제작 조건과 연주 및 보관 방식에 따라서 달라진다. 이런 차이로 인해 중고 악기를 구입할 때는 상태를 확인해야 한다. 반대급부로 잘 연주하지 않은 채로 오래'
        self.assertIn('POSSIBLE_UNFINISHED_KOREAN_PROSE_NEEDS_CONTEXT', deferrals(value))

    def test_complete_korean_paragraph_is_not_deferred(self):
        self.assertEqual(deferrals('악기의 수명은 제작 조건과 보관 방식에 따라 달라진다. 이 설명은 보관 조건을 함께 명시한다.'), [])

    def test_numbered_populated_list_is_kept(self):
        self.assertEqual(deferrals('작품 목록\n1. 작품 가 (2001년)\n2. 작품 나 (2002년)'), [])

    def test_quotes_across_blocks_are_balanced(self):
        self.assertEqual(deferrals('저자는 “첫 문장.\n\n다음 문장.”이라고 적었다.'), [])

    def test_missing_quote_end_is_deferred(self):
        self.assertIn('UNBALANCED_CURLY_DOUBLE_QUOTES_NEED_CONTEXT', deferrals('저자는 “첫 문장.\n\n다음 절'))

    def test_retail_fields_are_deferred_not_deleted(self):
        value = 'The named book describes history.\n- ISBN: 123\n- Item No: 456\n- Vendor: A'
        self.assertIn('RETAIL_CATALOG_FIELDS_STILL_NEED_CONTEXT', deferrals(value))
        self.assertIn('Item No: 456', value)

    def test_ordinary_reference_is_not_retail(self):
        self.assertEqual(deferrals('참고 문헌\nAuthor A. Book B. Publisher C. 2001. ISBN 123.'), [])

    def test_unclear_affiliation_is_deferred(self):
        self.assertIn('POSSIBLE_OCR_AFFILIATION_NEEDS_CONTEXT', deferrals('Kåre Rokoengen, /KU (Institute), Norway;'))


if __name__ == '__main__':
    unittest.main()
