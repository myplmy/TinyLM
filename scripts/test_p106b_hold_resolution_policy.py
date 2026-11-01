#!/usr/bin/env python3
"""Real counterexample shapes: empty sections, references, code and repetition."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy as policy


class DraftPolicyTests(unittest.TestCase):
    def propose(self, text, **kwargs):
        row = dict(id="expanded_train:1", text=text, complete_eos=True, valid_utf8=True)
        row.update(kwargs)
        return policy.propose(row)

    def test_known_empty_climate_section_is_not_a_populated_topic(self):
        original = "가람은 도시이다.\n\n기후\n\n교통\n철도역이 있다.\n"
        result = self.propose(original)
        self.assertEqual(result["decision"], "EDIT")
        self.assertNotIn("기후", result["text"])
        self.assertIn("교통\n철도역이 있다.", result["text"])

    def test_related_topic_names_are_not_mistaken_for_empty_sections(self):
        text = "가람은 도시이다.\n\n같이 보기\n 기후\n 교통\n"
        result = self.propose(text)
        self.assertEqual(result["text"], text)

    def test_empty_alias_inside_real_title_does_not_remove_the_title(self):
        result = self.propose("《어떤 소설()》은 작가의 소설이다.\n")
        self.assertEqual(result["decision"], "EDIT")
        self.assertEqual(result["text"], "《어떤 소설》은 작가의 소설이다.\n")

    def test_multiple_empty_foreign_name_fields_keep_all_date_values(self):
        result = self.propose("김가람(, , 1950년 5월 17일~2008년 2월 23일)은 정치가이다.\n")
        self.assertEqual(result["decision"], "EDIT")
        self.assertIn("(1950년 5월 17일~2008년 2월 23일)", result["text"])

    def test_function_parentheses_are_not_optional_name_fields(self):
        text = "이 함수()는 코드 문법의 예이다.\n"
        result = self.propose(text)
        self.assertEqual(result["text"], text)

    def test_empty_footer_before_two_explicit_category_anchors(self):
        text = "김가람은 미국의 배우이다.\n외부 링크\n2007년 출생\n살아있는 사람\n미국의 여자 배우\n"
        result = self.propose(text)
        self.assertEqual(result["decision"], "EDIT")
        self.assertNotIn("외부 링크", result["text"])
        self.assertIn("2007년 출생\n살아있는 사람\n미국의 여자 배우", result["text"])

    def test_real_profile_link_label_survives_following_categories(self):
        text = "김가람은 정치가이다.\n외부 링크\nParliamentary profile\n1954년 출생\n살아있는 사람\n"
        result = self.propose(text)
        self.assertIn("외부 링크\nParliamentary profile", result["text"])

    def test_single_booklike_title_stays_pending(self):
        text = "An article about films.\nExternal links\n2017년 영화\n"
        self.assertEqual(self.propose(text)["decision"], "PENDING")

    def test_repeated_statistics_sources_keep_distinct_contexts(self):
        text = "가람은 도시이다.\n1950-현재 유엔 추계\n출처: 유엔 세계인구전망 2019\n2019년 유엔 인구 통계\n출처: 유엔 세계인구전망 2019\n"
        self.assertTrue(policy.contextual_repetitions(text))
        result = self.propose(text)
        self.assertEqual(result["text"], text)
        self.assertEqual(result["decision"], "KEEP")

    def test_unanchored_repeated_prose_is_not_released_as_normal(self):
        text = "Repeated main-body prose.\nRepeated main-body prose.\n"
        self.assertEqual(self.propose(text)["decision"], "PENDING")

    def test_unicode_and_real_fenced_code_bytes_survive(self):
        literal = "U+F900 (豈) e\u0301"
        block = "```python\nprint('<div>')\n```"
        text = "가람()은 도시이다.\n\n" + literal + "\n" + block + "\n"
        result = self.propose(text)
        self.assertIn(literal, result["text"])
        self.assertIn(block, result["text"])

    def test_true_birth_conflict_is_still_pending(self):
        text = "김가람(1992년 1월 31일 ~ )은 선수이다.\n1991년 출생\n살아있는 사람\n"
        self.assertEqual(self.propose(text)["decision"], "PENDING")

    def test_individual_review_cannot_be_bypassed_by_a_clean_surface(self):
        row = dict(id="expanded_train:1", text="A complete independent article.", complete_eos=True, valid_utf8=True)
        self.assertEqual(policy.propose(row, True)["decision"], "PENDING")

    def test_actual_split_fragment_is_excluded_without_inventing_eos(self):
        self.assertEqual(self.propose("A truncated fragment", complete_eos=False)["decision"], "EXCLUDE")


if __name__ == "__main__":
    unittest.main()
