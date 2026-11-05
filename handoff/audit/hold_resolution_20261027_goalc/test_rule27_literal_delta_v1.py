"""Counterexamples for the independent all-row rule27 preservation check."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import verify_rule27_literal_delta_v1 as check


class LiteralDeltaTests(unittest.TestCase):
    def test_empty_alias_allowed(self):
        self.assertTrue(check.evaluate('페랭()은 다음 사람을 가리킨다.\n자크 페랭(): 배우이다.',
            '페랭은 다음 사람을 가리킨다.\n자크 페랭: 배우이다.')['eligible_narrow_literal_delta'])

    def test_filled_foreign_name_deletion_rejected(self):
        result=check.evaluate('자크 페랭(, acques Perrin): 배우이다.', '자크 페랭: 배우이다.')
        self.assertFalse(result['guards']['all_populated_characters_in_source_order'])

    def test_date_endpoint_deletion_rejected(self):
        result=check.evaluate('이름(, 1910~1990): 작가이다.', '이름(1910~): 작가이다.')
        self.assertFalse(result['eligible_narrow_literal_delta'])

    def test_unknown_endpoint_is_preserved(self):
        self.assertTrue(check.evaluate('이름(, 1910~): 작가이다.',
            '이름(1910~): 작가이다.')['eligible_narrow_literal_delta'])

    def test_populated_reference_preserved(self):
        result=check.evaluate('목록은 다음 뜻으로 쓰인다.\n참고 문헌\n책 이름, 2001.',
            '목록은 다음 뜻으로 쓰인다.')
        self.assertFalse(result['eligible_narrow_literal_delta'])

    def test_only_empty_eof_reference_heading_removed(self):
        self.assertTrue(check.evaluate('목록은 다음 뜻으로 쓰인다.\n각주\n외부 링크\n',
            '목록은 다음 뜻으로 쓰인다.')['eligible_narrow_literal_delta'])

    def test_interior_heading_not_empty_eof(self):
        result=check.evaluate('목록은 다음 뜻으로 쓰인다.\n같이 보기\n다른 이름: 설명이다.',
            '목록은 다음 뜻으로 쓰인다.\n다른 이름: 설명이다.')
        self.assertFalse(result['eligible_narrow_literal_delta'])

    def test_negation_loss_rejected(self):
        self.assertFalse(check.evaluate('이름: 배우가 아니다.', '이름: 배우이다.')['eligible_narrow_literal_delta'])

    def test_reordering_rejected(self):
        self.assertFalse(check.evaluate('이름: 작가이자 배우이다.', '이름: 배우이자 작가이다.')['eligible_narrow_literal_delta'])

    def test_quote_subject_loss_rejected(self):
        self.assertFalse(check.evaluate('이름: 김씨가 "아니다"라고 말했다.',
            '이름: "아니다"라고 말했다.')['eligible_narrow_literal_delta'])


if __name__=='__main__':
    unittest.main()
