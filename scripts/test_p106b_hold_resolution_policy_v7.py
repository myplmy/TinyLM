#!/usr/bin/env python3
"""Typed metadata, populated resources and same/different section repeats."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v7 as policy
from scripts import test_p106b_hold_resolution_policy_v5 as inherited
from scripts import test_p106b_hold_resolution_policy_v6 as local_inherited


class NamedContexts(unittest.TestCase):
    def propose(self, text, **more):
        return policy.propose(dict(id="expanded_train:1", text=text, complete_eos=True, valid_utf8=True, **more))

    def candidate(self, text):
        result = self.propose(text)
        return result.get("candidate", result["text"])

    def test_filled_dash_resource_names_keep_the_reference_heading(self):
        text = "나노카는 일본의 배우이다.\n외부 링크\n – Fit One\n – Ameba Blog\n1989년 출생\n살아있는 사람\n"
        self.assertEqual(self.propose(text)["text"], text)
        self.assertEqual(self.propose(text)["decision"], "KEEP")

    def test_exact_topic_named_resource_is_kept_without_inventing_a_url(self):
        text = "주리투아니아 대만 대표처는 대만의 대표부이다.\n외부 링크\n 주리투아니아 대만 대표처\n2021년 설립\n리투아니아\n대만\n"
        self.assertEqual(self.propose(text)["text"], text)
        self.assertEqual(self.propose(text)["decision"], "KEEP")

    def test_typed_political_writer_prefix_keeps_every_category_word(self):
        text = "코리 로빈은 미국의 정치학 교수이다.\n참고 문헌\n미국의 정치 작가\n미국의 정치철학자\n미국의 정치 평론가\n1967년 출생\n살아있는 사람\n"
        self.assertEqual(self.propose(text)["text"], text.replace("참고 문헌\n", ""))

    def test_family_and_explicit_historical_role_precede_a_year_anchor(self):
        text = "고조기는 고려의 문신이다.\n각주\n제주 고씨\n과거 급제자\n고려의 문신\n1157년 사망\n"
        self.assertEqual(self.propose(text)["text"], text.replace("각주\n", ""))

    def test_explicit_year_company_anchor_preserves_the_actual_category_tail(self):
        text = "가람은 로봇 기업이다.\n외부 링크\n1992년 설립된 기업\n경기도의 기업\n로봇 기업\n"
        self.assertEqual(self.propose(text)["text"], text.replace("외부 링크\n", ""))

    def test_named_material_before_a_year_is_not_consumed_as_category_text(self):
        text = "김가람은 축구 선수이다.\n외부 링크\n김가람 자료 모음\n1983년 출생\n살아있는 사람\n"
        self.assertEqual(self.candidate(text), text)

    def test_populated_child_section_keeps_its_parent(self):
        text = "가람은 도시이다.\n문화\n교통\n철도가 지역을 연결한다.\n"
        self.assertEqual(self.propose(text)["text"], text)

    def test_empty_population_before_a_populated_city_sibling_is_removed(self):
        text = "가람은 도시이다.\n\n인구\n\n기후\n연중 비가 자주 내린다.\n"
        self.assertEqual(self.candidate(text), text.replace("인구\n", ""))
        self.assertIn("기후", self.candidate(text))

    def test_book_child_with_an_actual_citation_is_retained(self):
        text = "가람은 작가이다.\n참고 문헌\n책\n저자명, 《책 제목》, 1990.\n외부 링크\n가람 공식 사이트\n"
        self.assertIn("책\n저자명", self.candidate(text))

    def test_empty_book_child_is_only_removed_at_an_actual_appendix_boundary(self):
        text = "가람은 작가이다.\n참고 문헌\n책\n외부 링크\n가람 공식 사이트\n"
        self.assertNotIn("\n책\n", self.candidate(text))
        self.assertIn("가람 공식 사이트", self.candidate(text))

    def test_identical_intro_and_dedicated_section_statement_are_both_kept(self):
        text = "가람은 도시이다.\n같은 역사적 사건을 설명하는 문장이다.\n\n역사\n같은 역사적 사건을 설명하는 문장이다.\n"
        self.assertEqual(self.propose(text)["decision"], "KEEP")
        self.assertEqual(self.propose(text)["text"], text)

    def test_same_context_duplicate_is_not_automatically_released(self):
        text = "가람은 도시이다.\n\n역사\n같은 문장이 반복된다.\n같은 문장이 반복된다.\n"
        self.assertEqual(self.propose(text)["decision"], "PENDING")
        self.assertEqual(self.candidate(text), text)

    def test_a_lyric_like_refrain_is_never_deduplicated_by_this_rule(self):
        text = "가람은 노래이다.\n후렴\n다시 돌아오는 우리 노래.\n다시 돌아오는 우리 노래.\n"
        self.assertEqual(self.candidate(text), text)

    def test_prior_span_adjudication_cannot_be_bypassed(self):
        text = "가람은 작가이다.\n외부 링크\n가람\n1970년 출생\n살아있는 사람\n"
        result = self.propose(text, previous_holds=["prior-review"])
        self.assertEqual(result["decision"], "PENDING")
        self.assertEqual(result["text"], text)

    def test_birth_conflict_survives_a_newly_recognized_reference(self):
        text = "가람(1900년 1월 2일 ~)은 배우이다.\n외부 링크\n가람\n1901년 출생\n살아있는 사람\n"
        result = self.propose(text)
        self.assertEqual(result["decision"], "PENDING")
        self.assertIn("INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED", result["reasons"])


if __name__ == "__main__":
    with patch.object(inherited, "policy", policy), patch.object(local_inherited, "policy", policy):
        suite = unittest.TestSuite([
            unittest.defaultTestLoader.loadTestsFromModule(inherited),
            unittest.defaultTestLoader.loadTestsFromTestCase(local_inherited.LocalOptionalFields),
            unittest.defaultTestLoader.loadTestsFromTestCase(NamedContexts)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
