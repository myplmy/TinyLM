#!/usr/bin/env python3
"""Actual alias/call contexts and adversarial missing-value counterexamples."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_policy_v6 as policy
from scripts import test_p106b_hold_resolution_policy_v5 as previous_tests


class LocalOptionalFields(unittest.TestCase):
    def propose(self,text,**extra):
        return policy.propose(dict(id="expanded_train:1",text=text,complete_eos=True,valid_utf8=True,**extra))

    def candidate(self,text):
        result=self.propose(text)
        return result.get("candidate",result["text"])

    def test_explicit_quoted_name_does_not_need_an_entity_type(self):
        text="가람은 언어의 단어이다.\n\n이탈리아어 ‘베르가모토()’에서 유래한 말이다.\n"
        self.assertEqual(self.candidate(text),text.replace("()",""))

    def test_ascii_name_before_a_korean_subject_particle_is_not_a_call(self):
        text="K-OTC()는 대한민국의 장외주식시장이다.\n"
        self.assertEqual(self.propose(text)["text"],text.replace("()",""))

    def test_sports_club_alias_before_the_word_or_keeps_the_real_title(self):
        text="아프리카 스포르 다비장() 또는 아프리카 스포르는 코트디부아르 아비장의 축구 클럽이다.\n"
        self.assertEqual(self.propose(text)["text"],text.replace("()",""))

    def test_multiple_names_before_punctuation_keep_all_names_and_birth_date(self):
        text="키스 에이프(), 전 닉네임 키드 애쉬() (, 1993년 12월 25일 ~ )는 대한민국의 래퍼이다.\n"
        value=self.candidate(text)
        self.assertNotIn("()",value)
        self.assertIn("1993년 12월 25일",value)
        self.assertIn("키스 에이프",value)
        self.assertIn("키드 애쉬",value)

    def test_named_article_does_not_justify_deleting_a_missing_physical_symbol(self):
        text="광자는 빛을 구성하는 입자이다.\n\n광자 한 개의 에너지는 플랑크 상수()에 빛의 진동수()를 곱한 값이다.\n"
        result=self.propose(text)
        self.assertEqual(result["decision"],"PENDING")
        self.assertIn("플랑크 상수()",result.get("candidate",result["text"]))

    def test_a_missing_value_label_is_not_an_optional_name(self):
        text="가람은 도시이다.\n\n인구()는 다음과 같다.\n"
        self.assertEqual(self.propose(text)["decision"],"PENDING")

    def test_a_real_book_title_hole_is_never_deleted_or_filled(self):
        text="가람은 작가이다. 대표작은 《》이다.\n"
        self.assertEqual(self.propose(text)["decision"],"PENDING")
        self.assertIn("《》",self.candidate(text))

    def test_former_name_arrow_remains_for_actual_content_recovery(self):
        text="가람(←, 1980년)은 가수이다.\n"
        self.assertEqual(self.propose(text)["decision"],"PENDING")
        self.assertIn("←",self.candidate(text))

    def test_subroutine_syntax_is_kept_literally_without_a_language_brand(self):
        text="The function sprintf() converts the value; call imagecoloursforindex() afterwards.\n"
        result=self.propose(text)
        self.assertEqual(result["decision"],"KEEP")
        self.assertEqual(result["text"],text)

    def test_an_unattached_unknown_value_does_not_become_a_function_call(self):
        text="The function uses a value ().\n"
        self.assertEqual(self.propose(text)["decision"],"PENDING")

    def test_empty_reference_record_cannot_remove_a_following_body_tuple(self):
        text="가람은 도시이다.\n외부 링크\n자료 소개\n\n()\nA tuple represents a complete mathematical object.\n"
        self.assertIn("()",self.candidate(text))

    def test_fenced_empty_tuple_is_byte_identical_after_reference_heading(self):
        code="```python\n()\n```\n"
        text="가람은 작가이다.\n참고 문헌\n"+code
        self.assertIn(code,self.candidate(text))

    def test_empty_reference_slot_is_removed_without_touching_the_named_article(self):
        text="가람은 작가이다.\n외부 링크\n ()\n1970년 출생\n살아있는 사람\n"
        value=self.candidate(text)
        self.assertNotIn("()",value)
        self.assertIn("1970년 출생",value)

    def test_full_populated_aliases_are_literal_including_original_spacing(self):
        text="가람은 문학 작품이다.\n등장인물 이름(John,  Smith)은 그대로 쓰인다.\n"
        self.assertEqual(self.candidate(text),text)

    def test_named_external_reference_and_metadata_remain_present(self):
        text="파이살은 태권도 선수이다.\n외부 링크\n 파이살 - Taekwondo Data\n1970년 출생\n살아있는 사람\n"
        result=self.propose(text)
        self.assertEqual(result["decision"],"KEEP")
        self.assertEqual(result["text"],text)

    def test_prior_individual_hold_cannot_be_waived_by_new_name_rule(self):
        result=self.propose("가람()은 도시이다.\n",previous_holds=["prior-context"])
        self.assertEqual(result["decision"],"PENDING")


if __name__=="__main__":
    with patch.object(previous_tests,"policy",policy):
        suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(previous_tests),
                                 unittest.defaultTestLoader.loadTestsFromTestCase(LocalOptionalFields)])
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
