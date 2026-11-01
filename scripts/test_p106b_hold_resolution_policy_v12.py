#!/usr/bin/env python3
"""Source-observed nominal cases, value-hole negatives and inherited controls."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v12 as policy
from scripts import test_p106b_hold_resolution_policy_v11 as inherited


class NamedSourcesAndSubjects(unittest.TestCase):
    def value(self, text, **extra):
        return policy.propose(dict(id="expanded_train:12", text=text, complete_eos=True, valid_utf8=True, **extra))

    def clean(self, text):
        value = self.value(text)
        return value.get("candidate", value["text"])

    def test_police_metadata_remains_and_only_empty_footnote_disappears(self):
        text = "가람경찰서는 대한민국의 경찰서이다.\n\n각주\n강원특별자치도의 경찰서\n1948년 설치\n1956년 폐지\n대한민국의 없어진 경찰서\n"
        clean = self.clean(text)
        self.assertNotEqual(self.value(text)["decision"], "PENDING")
        self.assertNotIn("각주", clean)
        for line in text.splitlines()[3:]:
            self.assertIn(line, clean)

    def test_populated_bus_routes_and_vehicles_survive_category_context(self):
        text = "가람여객은 전라남도의 버스 회사이다.\n\n운행 노선\n130번: 항구 ~ 송공항\n150번: 항구 ~ 송공항\n보유 차량\n현대 그린시티\n\n각주\n전라남도의 시내버스 기업\n신안군의 교통\n1972년 설립된 기업\n"
        clean = self.clean(text)
        for literal in ["130번: 항구 ~ 송공항", "150번: 항구 ~ 송공항", "현대 그린시티", "신안군의 교통"]:
            self.assertIn(literal, clean)
        self.assertNotIn("각주", clean)

    def test_actual_playdb_resource_without_url_keeps_reference_heading(self):
        text = "가람은 대한민국의 배우이다.\n\n외부 링크\nplayDB 인물정보\n1974년 출생\n대한민국의 남자 연극 배우\n대한민국의 남자 뮤지컬 배우\n"
        self.assertIn("외부 링크\nplayDB 인물정보", self.clean(text))
        self.assertNotEqual(self.value(text)["decision"], "PENDING")

    def test_named_election_statistics_source_is_preserved(self):
        text = "가람은 대한민국의 선거구이다.\n\n외부 링크\n중앙선거관리위원회 선거통계시스템\n1948년 신설된 대한민국 선거구\n1963년 폐지된 대한민국 선거구\n"
        self.assertIn("중앙선거관리위원회 선거통계시스템", self.clean(text))
        self.assertIn("외부 링크", self.clean(text))

    def test_explicit_period_definition_needs_no_invented_translation(self):
        text = "벤델 시대()란 스웨덴 역사에서 게르만족의 대이동 시대와 바이킹 시대 사이의 기간을 말한다.\n"
        self.assertEqual(self.clean(text), text.replace("()", ""))
        self.assertNotEqual(self.value(text)["decision"], "PENDING")

    def test_complete_book_title_and_qualified_source_claim_survive(self):
        text = "《브리튼인의 역사》()는 브리튼섬의 역사를 기록했다고 주장되는 문헌으로, 대략 828년경 작성되었다.\n"
        clean = self.clean(text)
        self.assertEqual(clean, text.replace("()", ""))
        self.assertIn("주장되는", clean)

    def test_person_date_with_literal_slash_and_every_filled_alias_is_preserved(self):
        text = "아흐메트 3세(, Aḥmed-i sālis, 1673년 12월 30/31일 ~ 1736년 7월 1일)는 오스만 제국의 술탄이자 술탄 메흐메트 4세의 아들이다.\n"
        clean = self.clean(text)
        self.assertEqual(clean, text.replace("(, ", "("))
        self.assertIn("30/31일", clean)
        self.assertIn("Aḥmed-i sālis", clean)

    def test_computer_scientist_is_not_confused_with_a_program_call(self):
        text = "크리스토퍼 스트래치(, , 1916년 11월 16일 ~ 1975년 5월 18일)는 영국의 컴퓨터 과학자였다. 표시적 의미론을 만들었고 프로그래밍 언어 디자인에 기여했다.\n"
        self.assertEqual(self.clean(text), text.replace("(, , ", "("))

    def test_missing_population_is_never_an_optional_alias(self):
        text = "인구()는 이 도시에서 조사한 값이다.\n"
        self.assertIn("인구()", self.clean(text))
        self.assertEqual(self.value(text)["decision"], "PENDING")

    def test_mathematical_parameter_is_never_a_nominal_alias(self):
        text = "함수 f()는 매개변수에 따른 방정식을 정의한다.\n"
        self.assertIn("f()", self.clean(text))

    def test_actual_code_and_unicode_examples_keep_their_literal_bytes(self):
        text = "가람은 대한민국의 작가이다.\n\n```python\nname = '인물()'\n```\nU+F900(豈)\n\n각주\n1900년 출생\n대한민국의 시인\n"
        clean = self.clean(text)
        self.assertTrue(policy.code_preserved(text, clean))
        self.assertTrue(policy.unicode_examples_preserved(text, clean))

    def test_prior_individual_hold_is_not_released_by_a_new_nominal_form(self):
        text = "벤델 시대()란 두 시대 사이의 기간을 말한다.\n"
        result = self.value(text, previous_holds=["old_individual"])
        self.assertEqual(result["decision"], "PENDING")
        self.assertEqual(result["text"], text)


if __name__ == "__main__":
    v10 = inherited.inherited
    v9 = v10.inherited
    v8 = v9.inherited
    v7 = v8.inherited
    modules = [inherited, v10, v9, v8, v7, v7.inherited, v7.local_inherited]
    with ExitStack() as stack:
        for module in modules:
            stack.enter_context(patch.object(module, "policy", policy))
        suite = unittest.TestSuite([
            unittest.defaultTestLoader.loadTestsFromModule(v7.inherited),
            unittest.defaultTestLoader.loadTestsFromTestCase(v7.local_inherited.LocalOptionalFields),
            unittest.defaultTestLoader.loadTestsFromTestCase(v7.NamedContexts),
            unittest.defaultTestLoader.loadTestsFromTestCase(v8.LiteralContext),
            unittest.defaultTestLoader.loadTestsFromTestCase(v9.LocalFieldsAndPremises),
            unittest.defaultTestLoader.loadTestsFromTestCase(v10.LiteralDamageBoundaries),
            unittest.defaultTestLoader.loadTestsFromTestCase(inherited.ObservedTailContexts),
            unittest.defaultTestLoader.loadTestsFromTestCase(NamedSourcesAndSubjects)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
