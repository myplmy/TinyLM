#!/usr/bin/env python3
"""Actual-name substring, unknown-field and dependent-paragraph regressions."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_policy_v9 as policy
from scripts import test_p106b_hold_resolution_policy_v8 as inherited


class LocalFieldsAndPremises(unittest.TestCase):
    def propose(self,text,**more):
        return policy.propose(dict(id="expanded_train:1",text=text,complete_eos=True,valid_utf8=True,**more))

    def candidate(self,text):
        result=self.propose(text)
        return result.get("candidate",result["text"])

    def test_station_name_is_not_a_mathematical_codomain(self):
        text="신사카에마치역()은 나고야시에 위치한 철도역이다.\n"
        self.assertEqual(self.candidate(text),text.replace("()",""))

    def test_actual_mathematical_codomain_value_stays_unresolved(self):
        text="가람은 수학적 대상이다.\n\n함수의 치역()은 다음과 같이 정해진다.\n"
        candidate=self.candidate(text)
        self.assertNotIn("치역은 다음",candidate)

    def test_the_complete_currency_definition_keeps_units_and_values(self):
        text="구르드(, )는 아이티의 통화로 1 구르드는 100 상팀(, )으로 나뉜다.\n"
        self.assertEqual(self.candidate(text),text.replace("(, )",""))

    def test_populated_former_name_arrow_stays_literal(self):
        text="실로암(←Siloan, , )은 예루살렘의 지역이다.\n"
        self.assertEqual(self.candidate(text),text.replace("←Siloan, , ","←Siloan"))

    def test_unknown_former_name_is_never_supplied(self):
        text="가람(←, )은 예루살렘의 지역이다.\n"
        self.assertEqual(self.propose(text)["decision"],"PENDING")
        self.assertEqual(self.candidate(text),text)

    def test_empty_optional_package_name_does_not_delete_existing_title(self):
        text="《마리오 게임》(Mario Game) 또는 《마리오 게임 2》(; 패키지명 )는 2005년에 발매되었다.\n"
        candidate=self.candidate(text)
        self.assertEqual(candidate,text.replace("(; 패키지명 )",""))

    def test_filled_package_name_is_never_changed(self):
        text="《마리오 게임》(Mario Game) 또는 《마리오 게임 2》(패키지명 실제 이름)는 2005년에 발매되었다.\n"
        self.assertEqual(self.candidate(text),text)

    def test_math_on_another_disambiguation_row_does_not_erase_a_real_alias(self):
        text="F는 다음을 가리키는 말이다.\n플루오린(, 또는 플루오르(), 불소(弗素))의 원소기호\n수학에서 F는 함수를 뜻한다.\n"
        candidate=self.candidate(text)
        self.assertIn("플루오린(또는 플루오르, 불소(弗素))",candidate)
        self.assertIn("F는 함수를 뜻한다.",candidate)

    def test_actual_math_on_the_same_row_prevents_nominal_erasure(self):
        text="F는 다음을 가리키는 말이다.\n수학에서 함수 F()는 아래와 같이 정의된다.\n"
        self.assertNotIn("F는 아래",self.candidate(text))

    def test_missing_premise_and_its_example_are_both_quarantined(self):
        text="가람은 수학적 개념이다.\n\n임의의 에 대하여 공식이 정의된다.\n\n따라서 이 공식으로 4를 얻는다.\n\n예제\n예를 들어 결과는 8이다.\n\n역사\n가람은 1900년에 처음 소개된 개념이다.\n"
        candidate=self.candidate(text)
        self.assertIn("가람은 수학적 개념이다.",candidate)
        self.assertIn("1900년에 처음",candidate)
        self.assertNotIn("공식으로 4",candidate)
        self.assertNotIn("결과는 8",candidate)

    def test_a_missing_first_definition_is_not_released_by_dropping_its_evidence(self):
        text="가람()은 수식의 계수로 임의의 에 대해 정의된다.\n\n따라서 결과는 8이다.\n"
        self.assertEqual(self.propose(text)["decision"],"PENDING")

    def test_code_bytes_cannot_be_lost_with_a_missing_premise(self):
        text="가람은 계산 기법이다.\n\n임의의 에 대한 연산이다.\n\n```python\nanswer = f(x)\n```\n\n역사\n가람은 1900년에 소개된 기법이다.\n"
        candidate=self.candidate(text)
        self.assertIn("answer = f(x)",candidate)
        self.assertEqual(self.propose(text)["decision"],"PENDING")

    def test_a_complete_history_is_retained_after_missing_quantity(self):
        text="가람은 물체이다.\n\n무게는 kg이다.\n\n이 값으로 계산한 결과는 7이다.\n\n역사\n가람은 오랜 역사를 가진 물체이다.\n"
        candidate=self.candidate(text)
        self.assertIn("오랜 역사",candidate)
        self.assertNotIn("결과는 7",candidate)

    def test_nonempty_physical_quantity_and_its_condition_remain_literal(self):
        text="가람은 물체이다.\n\n조건이 맞을 때만 무게는 3 kg이다.\n\n이 조건이 아니면 계산하지 않는다.\n"
        self.assertEqual(self.candidate(text),text)

    def test_inherited_span_review_remains_pending(self):
        text="구르드(, )는 아이티의 통화로 100 상팀으로 나뉜다.\n"
        self.assertEqual(self.propose(text,previous_holds=["native-span-review"])["decision"],"PENDING")


if __name__=="__main__":
    old=inherited.inherited
    with patch.object(inherited,"policy",policy),patch.object(old,"policy",policy), \
            patch.object(old.inherited,"policy",policy),patch.object(old.local_inherited,"policy",policy):
        suite=unittest.TestSuite([
            unittest.defaultTestLoader.loadTestsFromModule(old.inherited),
            unittest.defaultTestLoader.loadTestsFromTestCase(old.local_inherited.LocalOptionalFields),
            unittest.defaultTestLoader.loadTestsFromTestCase(old.NamedContexts),
            unittest.defaultTestLoader.loadTestsFromTestCase(inherited.LiteralContext),
            unittest.defaultTestLoader.loadTestsFromTestCase(LocalFieldsAndPremises)])
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
