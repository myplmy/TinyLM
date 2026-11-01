#!/usr/bin/env python3
"""Adversarial source-derived boundaries plus retained draft protections."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v4 as policy
from scripts import test_p106b_hold_resolution_policy_v2 as prior_tests


class RetainedDraftGuards(prior_tests.RetainedDraftGuards):
    def setUp(self):
        change = patch.object(prior_tests, "policy", policy)
        change.start()
        self.addCleanup(change.stop)
        super().setUp()


class RetainedV2Boundaries(prior_tests.NewSourceShapes):
    def setUp(self):
        change = patch.object(prior_tests, "policy", policy)
        change.start()
        self.addCleanup(change.stop)


class SourceContexts(unittest.TestCase):
    def propose(self, text, **extra):
        row = dict(id="expanded_train:1", text=text, complete_eos=True, valid_utf8=True)
        row.update(extra)
        return policy.propose(row)

    def test_player_da_intro_recovers_empty_footer_without_changing_school_list(self):
        text = "김가람(1962년 2월 7일 ~)은 전 야구 선수다.\n\n출신 학교\n 가람중학교\n\n각주\n1962년 출생\n살아있는 사람\n"
        result = self.propose(text)
        self.assertEqual(result["decision"], "EDIT")
        self.assertEqual(result["text"], text.replace("각주\n", ""))

    def test_single_explicit_album_category_is_not_a_missing_reference(self):
        result = self.propose("《Call》는 발매된 음반이다.\n각주\n2006년 컴필레이션 음반\n")
        self.assertEqual(result["decision"], "EDIT")
        self.assertNotIn("각주", result["text"])

    def test_semicolon_empty_alias_preserves_full_dates_and_places(self):
        text = "돈 가람(; 1898년 7월 17일, 산 세바스티안 ~ 1990년 4월 1일)는 축구 감독이다.\n"
        result = self.propose(text)
        self.assertEqual(result["text"], text.replace("(; ", "("))

    def test_alias_before_another_explicit_name_does_not_require_immediate_particle(self):
        text = "오가와(,1860년 9월 29일 ~ 1929년 9월 6일), 또는 가즈마사는 일본의 사진가이다.\n"
        self.assertEqual(self.propose(text)["text"], text.replace("(,", "("))

    def test_quoted_filled_translation_after_empty_slot_survives(self):
        text = "《영화》(, ‘빌려 사는 사람’)는 장편 애니메이션 영화로, 일본에서 개봉되었다.\n"
        self.assertEqual(self.propose(text)["text"], text.replace("(, ", "("))

    def test_korean_profile_is_a_populated_reference_and_heading_survives(self):
        text = "김가람은 사격 선수이다.\n외부 링크\n김가람 프로필 - ISSF\n1976년 출생\n살아있는 사람\n"
        result = self.propose(text)
        self.assertEqual(result["text"], text)
        self.assertEqual(result["decision"], "KEEP")

    def test_unclassified_named_reference_cannot_be_eaten_by_category_tail(self):
        text = "김가람은 축구 선수이다.\n외부 링크\n가람 자료 모음\n1976년 출생\n살아있는 사람\n"
        self.assertIn("외부 링크", self.propose(text).get("candidate", self.propose(text)["text"]))

    def test_parent_heading_before_populated_child_is_retained(self):
        text = "가람은 도시이다.\n문화\n교통\n철도가 지역을 연결한다.\n"
        result = self.propose(text)
        self.assertEqual(result["text"], text)
        self.assertEqual(result["decision"], "KEEP")

    def test_empty_body_chain_before_appendix_has_no_population_values_to_invent(self):
        text = "가람은 도시이다.\n인구\n기후\n각주\n2000년 설립\n"
        result = self.propose(text)
        self.assertEqual(result["text"], "가람은 도시이다.\n2000년 설립\n")

    def test_real_book_contents_list_is_retained(self):
        text = "Book\n\nTable of Contents\nChapter One\nChapter Two\n"
        self.assertEqual(self.propose(text)["text"], text)

    def test_empty_web_contents_marker_can_precede_a_real_heading_and_prose(self):
        text = "A complete introductory sentence.\nTable of Contents\nChapter One\n" + "The explanation is complete. " * 9 + "\n"
        result = self.propose(text)
        self.assertNotIn("Table of Contents", result["text"])
        self.assertIn("Chapter One", result["text"])

    def test_new_downstream_birth_guard_cannot_be_skipped_by_an_earlier_repetition_risk(self):
        text = "김가람(1900년 1월 2일 ~)은 배우이다.\n문장이 반복된다.\n문장이 반복된다.\n1901년 출생\n"
        result = self.propose(text)
        self.assertEqual(result["decision"], "PENDING")
        self.assertIn("INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED", result["reasons"])

    def test_missing_statistical_values_remain_pending(self):
        result = self.propose("가람은 사이트이다.\n년 월 일 기준으로 총 개의 항목이 있다.\n")
        self.assertEqual(result["decision"], "PENDING")

    def test_legacy_span_hold_is_never_automatically_released(self):
        result = self.propose("가람은 도시이다.\n", previous_holds=["eos_1", "text_old"])
        self.assertEqual(result["decision"], "PENDING")
        self.assertIn("PRIOR_INDIVIDUAL_OR_SPAN_REVIEW_REQUIRES_ROOT_ADOPTION", result["reasons"])

    def test_code_fences_and_unicode_examples_stay_byte_identical(self):
        code = "```python\nf()\n```\n"
        text = "김가람은 작가이다.\n" + code + "U+F900 (豈)\n"
        result = self.propose(text)
        self.assertIn(code, result.get("candidate", result["text"]))
        self.assertIn("U+F900 (豈)", result.get("candidate", result["text"]))


if __name__ == "__main__":
    unittest.main()
