"""Regressions from corpus names, actual broken wiki and math intervals."""
import unittest
from structural_delimiter_deferrals_v2 import deferrals


class BracketContext(unittest.TestCase):
    def test_mixed_width_cast_credit(self):
        self.assertEqual([], deferrals('가수: 류구 레나 （나카하라 마이)'))

    def test_mixed_width_nested_title(self):
        self.assertEqual([], deferrals('초코라(정식명칭/초코리나M120）'))

    def test_real_missing_wiki_bracket(self):
        self.assertTrue(deferrals('공개 연도 [[2014년]'))

    def test_crossed_brackets_remain_invalid(self):
        self.assertTrue(deferrals('［cast (name］)'))

    def test_missing_fullwidth_close_remains_invalid(self):
        self.assertTrue(deferrals('성우 （나카하라 마이'))

    def test_typed_half_open_intervals(self):
        self.assertEqual([], deferrals('실수 구간 [0, 1) 및 （-∞, 2]'))

    def test_code_fences_remain_outside_prose_stack(self):
        self.assertEqual([], deferrals('```text\n([\n```\n가수 （이름)'))


if __name__ == '__main__':
    unittest.main()
