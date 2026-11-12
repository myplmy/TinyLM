from pathlib import Path
import sys
import unittest

AUDIT=Path(__file__).resolve().parent
sys.path[:0]=[str(AUDIT),str(AUDIT.parents[2])]
from structural_delimiter_deferrals_v1 import deferrals


class DelimiterContext(unittest.TestCase):
    def test_actual_nested_birth_death_shape_is_deferred(self):
        self.assertTrue(deferrals('나가야 왕(684?년 2월 12일 ~ 729년 2월 12일(양력 3월 16일)은 황족이다.'))

    def test_nested_birth_death_closure_preserves_question_mark(self):
        self.assertEqual(deferrals('나가야 왕(684?년 2월 12일 ~ 729년 2월 12일(양력 3월 16일))은 황족이다.'),[])

    def test_normal_empty_and_populated_aliases_are_balanced(self):
        self.assertEqual(deferrals('가람()과 나래(Narae)는 이름이다.'),[])

    def test_numbered_list_markers_are_not_broken_parentheses(self):
        self.assertEqual(deferrals('목록\n1) 가람\n2) 나래'),[])

    def test_actual_half_open_intervals_remain_valid(self):
        self.assertEqual(deferrals('구간 [0, 1)과 (a, b]를 생각한다.'),[])

    def test_crossed_delimiters_are_not_balanced_by_count(self):
        self.assertTrue(deferrals('([)]'))

    def test_unmatched_square_bracket_is_deferred(self):
        self.assertTrue(deferrals('이름]은 단어이다.'))

    def test_protected_code_is_not_parsed_as_prose(self):
        self.assertEqual(deferrals('예제이다.\n```python\ns = "("\n```\n'),[])


if __name__=='__main__':
    unittest.main()
