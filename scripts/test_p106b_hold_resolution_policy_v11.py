#!/usr/bin/env python3
"""Actual typed-tail/resource forms and conservative repetition contexts."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v11 as policy
from scripts import test_p106b_hold_resolution_policy_v10 as inherited


class ObservedTailContexts(unittest.TestCase):
    def propose(self, text, **extra):
        return policy.propose(dict(id="expanded_train:1", text=text, complete_eos=True, valid_utf8=True, **extra))

    def candidate(self, text):
        value = self.propose(text)
        return value.get("candidate", value["text"])

    def test_language_and_sport_categories_do_not_disappear_with_empty_footnote(self):
        text = "가람은 네덜란드의 가수이다.\n\n각주\n\n독일어 가수\n네덜란드어 가수\n살아있는 사람\n1973년 출생\n"
        self.assertNotIn("각주", self.candidate(text))
        self.assertIn("독일어 가수", self.candidate(text))
        self.assertNotEqual(self.propose(text)["decision"], "PENDING")

    def test_organization_dissolution_and_formation_metadata_survive(self):
        text = "가람은 미국의 단체이다.\n\n각주\n\n1970년 해체된 단체\n1955년 설립된 단체\n미국의 여성주의 단체\n"
        self.assertNotIn("각주", self.candidate(text))
        self.assertIn("1970년 해체된 단체", self.candidate(text))

    def test_literal_underscore_category_is_classified_without_rewriting_it(self):
        text = "가람의료원은 대한민국의 병원이다.\n\n각주\n\n외부 링크\n\n대한민국의_공공병원\n도립병원\n병원\n1912년 설립\n"
        self.assertIn("대한민국의_공공병원", self.candidate(text))
        self.assertNotIn("외부 링크", self.candidate(text))

    def test_named_daum_resource_survives_without_a_url(self):
        text = "가람은 오스트레일리아의 배우이다.\n\n외부 링크\nDaum 영화\n\n1984년 출생\n살아있는 사람\n"
        self.assertIn("외부 링크\nDaum 영화", self.candidate(text))
        self.assertNotEqual(self.propose(text)["decision"], "PENDING")

    def test_named_federation_resource_is_not_a_blank_footer(self):
        text = "가람은 축구의 한 종류이다.\n\n외부 링크\n국제 축구 연맹\n국제축구역사통계연맹\n"
        self.assertIn("국제 축구 연맹", self.candidate(text))
        self.assertIn("외부 링크", self.candidate(text))

    def test_unknown_named_prefix_is_still_not_inferred_to_be_a_category(self):
        text = "가람은 대한민국의 작가이다.\n\n각주\n\n알 수 없는 자료집\n1900년 출생\n"
        self.assertEqual(self.propose(text)["decision"], "PENDING")
        self.assertIn("알 수 없는 자료집", self.candidate(text))

    def test_summary_and_overview_repetition_is_retained(self):
        text = "가람은 용어이다.\n\n개요\n이 용어는 같은 뜻으로 쓰인다.\n\n요약\n이 용어는 같은 뜻으로 쓰인다.\n"
        self.assertEqual(self.candidate(text).count("이 용어는 같은 뜻으로 쓰인다."), 2)
        self.assertNotEqual(self.propose(text)["decision"], "PENDING")

    def test_unrelated_heading_does_not_release_same_context_duplicates(self):
        text = "가람은 용어이다.\n\n개요\n이 용어는 같은 뜻으로 쓰인다.\n이 용어는 같은 뜻으로 쓰인다.\n\n요약\n별도 설명이다.\n"
        self.assertEqual(self.propose(text)["decision"], "PENDING")
        self.assertEqual(self.candidate(text).count("이 용어는 같은 뜻으로 쓰인다."), 2)


if __name__ == "__main__":
    v9 = inherited.inherited
    v8 = v9.inherited
    v7 = v8.inherited
    with patch.object(inherited, "policy", policy), patch.object(v9, "policy", policy), \
            patch.object(v8, "policy", policy), patch.object(v7, "policy", policy), \
            patch.object(v7.inherited, "policy", policy), patch.object(v7.local_inherited, "policy", policy):
        suite = unittest.TestSuite([
            unittest.defaultTestLoader.loadTestsFromModule(v7.inherited),
            unittest.defaultTestLoader.loadTestsFromTestCase(v7.local_inherited.LocalOptionalFields),
            unittest.defaultTestLoader.loadTestsFromTestCase(v7.NamedContexts),
            unittest.defaultTestLoader.loadTestsFromTestCase(v8.LiteralContext),
            unittest.defaultTestLoader.loadTestsFromTestCase(v9.LocalFieldsAndPremises),
            unittest.defaultTestLoader.loadTestsFromTestCase(inherited.LiteralDamageBoundaries),
            unittest.defaultTestLoader.loadTestsFromTestCase(ObservedTailContexts)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
