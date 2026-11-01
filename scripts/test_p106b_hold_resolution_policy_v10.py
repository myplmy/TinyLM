#!/usr/bin/env python3
"""Literal source counterexamples and actual damage dependency regressions."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v10 as policy
from scripts import test_p106b_hold_resolution_policy_v9 as inherited


class LiteralDamageBoundaries(unittest.TestCase):
    def propose(self, text, **more):
        return policy.propose(dict(id="expanded_train:1", text=text, complete_eos=True, valid_utf8=True, **more))

    def candidate(self, text):
        result = self.propose(text)
        return result.get("candidate", result["text"])

    def test_narrative_ellipsis_is_not_a_missing_measured_value(self):
        text = "가람은 소설의 등장인물이다.\n\n준의 동급생으로 전학을 왔다. 하지만 결과는...\n\n1969년 다른 학교로 전학했다.\n"
        self.assertEqual(self.candidate(text), text)

    def test_actual_absent_value_is_not_released_as_an_ellipsis(self):
        self.assertIsNotNone(policy.MISSING_DECLARATION.search("속도는."))
        self.assertIsNone(policy.MISSING_DECLARATION.search("결과는..."))

    def test_populated_railway_arrows_and_their_relations_survive(self):
        text = "가람구는 도시의 행정구역이다.\n\n교통\n서일본 여객철도\n(← 신코베역) - 신오사카역 - (오사카역 →)\n\n역사\n가람구는 1900년에 설립되었다.\n"
        self.assertIn("(← 신코베역) - 신오사카역 - (오사카역 →)", self.candidate(text))

    def test_an_actually_empty_former_name_still_requires_recovery(self):
        text = "가람(←, )은 도시이다.\n"
        self.assertEqual(self.propose(text)["decision"], "PENDING")

    def test_empty_relative_rows_do_not_remove_named_relatives(self):
        text = "가람은 대한민국의 정치인이다.\n\n가족 관계\n아버지: 김가람\n고모:\n고모:\n동생: 김나라\n\n역사\n가람은 1900년에 태어났다.\n"
        candidate = self.candidate(text)
        self.assertIn("아버지: 김가람", candidate)
        self.assertIn("동생: 김나라", candidate)
        self.assertNotIn("고모:", candidate)

    def test_empty_title_does_not_delete_populated_bibliography(self):
        text = "가람은 대한민국의 작가이다.\n\n주요 논문\n김가람, 《》 연구보고 60권 (1971), p.43-51\nKim, A complete title. Journal of Examples, Volume 20, 1979, Pages 34-40.\n\n각주\n"
        candidate = self.candidate(text)
        self.assertIn("연구보고 60권 (1971), p.43-51", candidate)
        self.assertIn("A complete title", candidate)

    def test_bibliographic_alias_removes_no_publisher_or_date(self):
        text = "가람은 일본의 만화가이다.\n\n완결 작품\n케이온!(, 망가타임 키라라, 호분샤, 2007년 5월호 - 2010년 10월호)\n\n외부 링크\n공식 사이트\n"
        candidate = self.candidate(text)
        self.assertIn("케이온!(망가타임 키라라, 호분샤, 2007년 5월호 - 2010년 10월호)", candidate)

    def test_a_nested_named_alias_and_its_existing_date_remain(self):
        text = "가람은 도시이다.\n\n자전거 페달 브레이크(코스터 브레이크)(, 1903년)가 있다.\n"
        self.assertIn("브레이크(코스터 브레이크)(1903년)", self.candidate(text))

    def test_literal_link_display_is_rendered_without_inventing_a_label(self):
        text = "A complete sentence names [[the actual target|its visible label]].\n"
        self.assertEqual(self.candidate(text), "A complete sentence names its visible label.\n")

    def test_empty_link_display_and_namespaced_resources_are_not_guessed(self):
        text = "A sentence names [[target|]] and [[File:photo.jpg|caption]].\n"
        self.assertIn("[[target|]]", self.candidate(text))
        self.assertIn("[[File:photo.jpg|caption]]", self.candidate(text))

    def test_code_link_examples_remain_literal(self):
        text = "```text\n[[target|display]]\n```\n"
        self.assertEqual(self.candidate(text), text)

    def test_complex_mixed_damage_is_not_whole_block_deleted(self):
        text = "가람은 개념이다.\n\n완전한 문장이다.\n고모:\n다른 완전한 이름과 설명이다.\n\n역사\n가람은 1900년에 소개되었다.\n"
        candidate = self.candidate(text)
        self.assertIn("다른 완전한 이름과 설명이다.", candidate)

    def test_unproven_independent_continuation_is_not_deleted(self):
        text = "가람은 수학적 개념이다.\n\n임의의 에 대하여 공식이 정의된다.\n\n두 개 이상의 원소를 갖는 집합 위의 정렬 순서는 조밀 순서가 아니다.\n\n역사\n가람은 1900년에 소개되었다.\n"
        candidate = self.candidate(text)
        self.assertIn("두 개 이상의 원소를 갖는 집합", candidate)
        self.assertEqual(self.propose(text)["decision"], "PENDING")


if __name__ == "__main__":
    v8 = inherited.inherited
    v7 = v8.inherited
    with patch.object(inherited, "policy", policy), patch.object(v8, "policy", policy), \
            patch.object(v7, "policy", policy), patch.object(v7.inherited, "policy", policy), \
            patch.object(v7.local_inherited, "policy", policy):
        suite = unittest.TestSuite([
            unittest.defaultTestLoader.loadTestsFromModule(v7.inherited),
            unittest.defaultTestLoader.loadTestsFromTestCase(v7.local_inherited.LocalOptionalFields),
            unittest.defaultTestLoader.loadTestsFromTestCase(v7.NamedContexts),
            unittest.defaultTestLoader.loadTestsFromTestCase(v8.LiteralContext),
            unittest.defaultTestLoader.loadTestsFromTestCase(inherited.LocalFieldsAndPremises),
            unittest.defaultTestLoader.loadTestsFromTestCase(LiteralDamageBoundaries)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
