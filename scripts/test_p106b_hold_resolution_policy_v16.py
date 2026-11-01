#!/usr/bin/env python3
"""Real boundary/value-hole regressions together with the frozen 184 tests."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v16 as policy
from scripts import test_p106b_hold_resolution_policy_v15 as inherited


class SeparateMetadataAndLiteralHoles(unittest.TestCase):
    def value(self, text):
        return policy.propose(dict(id="expanded_train:16", text=text, complete_eos=True, valid_utf8=True))

    def test_named_see_also_is_retained_before_separate_birth_metadata(self):
        text = "가람은 프랑스의 정치인이다.\n\n같이 보기\n레지스탕스\n알제리 독립 전쟁\n\n1899년 출생\n1983년 사망\n프랑스의 총리\n프랑스의 외무장관\n"
        clean, changes, proven = policy.separate_metadata_suffix(text)
        self.assertTrue(proven)
        self.assertEqual(clean, text)
        self.assertEqual(changes, [])
        self.assertIn("같이 보기\n레지스탕스\n알제리 독립 전쟁", self.value(text)["text"])

    def test_only_isolated_empty_footer_paragraph_is_removed(self):
        text = "가람은 프랑스의 정치인이다.\n\n참고 문헌\n자료 제목 — 저자, 1980\n\n각주\n\n외부 링크\n\n1899년 출생\n1983년 사망\n프랑스의 총리\n"
        clean, changes, proven = policy.separate_metadata_suffix(text)
        self.assertTrue(proven)
        self.assertEqual(len(changes), 2)
        self.assertIn("참고 문헌\n자료 제목 — 저자, 1980", clean)
        self.assertIn("1899년 출생\n1983년 사망\n프랑스의 총리", clean)
        self.assertNotIn("각주", clean)
        self.assertNotIn("외부 링크", clean)
        self.assertTrue(policy.ordered_deletion(text, clean))

    def test_unknown_value_inside_last_block_does_not_prove_metadata(self):
        text = "가람은 프랑스의 정치인이다.\n\n각주\n\n1899년 출생\n정체를 확인하지 못한 항목\n"
        self.assertEqual(policy.separate_metadata_suffix(text), (text, [], False))

    def test_two_arbitrary_categories_without_year_are_not_a_new_anchor(self):
        text = "가람은 프랑스의 정치인이다.\n\n각주\n\n프랑스의 총리\n프랑스의 외무장관\n"
        self.assertEqual(policy.separate_metadata_suffix(text), (text, [], False))

    def test_source_book_title_is_not_converted_to_birth_metadata(self):
        text = "가람은 프랑스의 정치인이다.\n\n참고 문헌\n\n《1899년 출생》\n《1983년 사망》\n"
        self.assertEqual(policy.separate_metadata_suffix(text), (text, [], False))

    def test_inline_year_words_do_not_prove_a_separate_metadata_block(self):
        text = "가람은 프랑스의 정치인이다. 1899년 출생\n1983년 사망\n프랑스의 총리\n"
        self.assertEqual(policy.separate_metadata_suffix(text), (text, [], False))

    def test_code_metadata_example_is_preserved(self):
        text = "가람은 프랑스의 정치인이다.\n\n```text\n각주\n\n1899년 출생\n1983년 사망\n```\n"
        self.assertEqual(policy.separate_metadata_suffix(text), (text, [], False))

    def test_observed_empty_wartime_name_stays_pending(self):
        text = "가람(, , 제2차 세계 대전 당시의 명칭: )은 폴란드의 도시이다.\n"
        value = self.value(text)
        self.assertEqual(value["decision"], "PENDING")
        self.assertIn("OBSERVED_EMPTY_NAMED_VALUE_REQUIRES_SOURCE_REVIEW", value["reasons"])

    def test_unfilled_visa_name_stays_pending(self):
        text = '가람(, 1914~1986)은 미국의 수학자이다.\n\n비자가 ""이라는 이름으로 잘못 발급되었다고 한다.\n'
        self.assertEqual(self.value(text)["decision"], "PENDING")

    def test_unfilled_quoted_blog_name_stays_pending(self):
        text = "가람(, 1985년 1월 1일 ~)은 일본의 가수이다.\n\n그의 블로그 ''는 상을 받았다.\n"
        self.assertEqual(self.value(text)["decision"], "PENDING")

    def test_literal_empty_calls_are_not_named_value_holes(self):
        self.assertEqual(policy.literal_holes("가람은 컴퓨터 과학자이다.\n\n```python\nname = ''\nresult = f()\nvalue = a[0]\n```\n"), [])

    def test_unmatched_square_bracket_is_not_silently_accepted(self):
        text = "가람은 대한민국의 휴게소이다. 고속도로]의 시설이다.\n"
        self.assertIn("UNMATCHED_CLOSING_SQUARE_BRACKET_REQUIRES_SOURCE_REVIEW", policy.literal_holes(text))
        self.assertEqual(self.value(text)["decision"], "PENDING")

    def test_filled_next_line_name_is_not_an_empty_parenthetical_field(self):
        self.assertEqual(policy.literal_holes("명칭:\n가람 대표부\n"), [])

    def test_metadata_proof_does_not_clear_conflicting_birth(self):
        text = "가람(1890년 5월 13일 ~ 1980년 6월 12일)은 라이베리아의 정치인이다.\n\n같이 보기\n라이베리아의 역사\n\n1913년 출생\n1980년 사망\n라이베리아의 대통령\n"
        value = self.value(text)
        self.assertEqual(value["decision"], "PENDING")
        self.assertIn("INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED", value["reasons"])

    def test_composer_optional_alias_does_not_delete_a_populated_song_paragraph(self):
        text = "가람 공업()은 일본의 기업이다.\n\n사가\n'만Z(양산형)'()이 작곡한 이 회사의 사가는 2003년 10월 24일에 방송에서 처음 소개되었다.\n\n외부 링크\n가람 공업(폐쇄)\n\n1986년 설립된 기업\n요코하마시의 기업\n"
        value = self.value(text)
        clean = value.get("candidate", value["text"])
        self.assertIn("사가\n'만Z(양산형)'이 작곡한 이 회사의 사가는 2003년 10월 24일", clean)
        self.assertTrue(policy.ordered_deletion(text, clean))

    def test_quoted_function_in_technical_paragraph_is_not_a_nominal_alias(self):
        text = "가람은 일본의 기업이다.\n\n함수 'f'()의 반환값을 설명한다.\n"
        self.assertEqual(policy.quoted_nominal_aliases(text), (text, []))

    def test_actual_value_quarantine_cannot_borrow_new_metadata_release(self):
        paragraph = "작곡가가 만든 회사의 노래는 방송을 통해 알려졌다."
        text = "가람은 일본의 기업이다.\n\n" + paragraph + "\n\n외부 링크\n가람 공업(폐쇄)\n\n1986년 설립된 기업\n요코하마시의 기업\n"
        previous_value = dict(decision="PENDING", text=text, candidate=text.replace(paragraph, ""),
                              reasons=["APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT"],
                              changes=[dict(reason=policy.QUARANTINE, original=paragraph)])
        with patch.object(policy.previous, "propose", return_value=previous_value):
            value = self.value(text)
        self.assertEqual(value["decision"], "PENDING")
        self.assertIn("PARTIAL_QUARANTINE_CANNOT_BORROW_A_METADATA_BOUNDARY_RELEASE", value["reasons"])


if __name__ == "__main__":
    v15, v14 = inherited, inherited.inherited
    v13, v12 = v14.inherited, v14.inherited.inherited
    v11, v10 = v12.inherited, v12.inherited.inherited
    v9, v8 = v10.inherited, v10.inherited.inherited
    v7 = v8.inherited
    modules = [v15, v14, v13, v12, v11, v10, v9, v8, v7, v7.inherited, v7.local_inherited]
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
            unittest.defaultTestLoader.loadTestsFromTestCase(v11.ObservedTailContexts),
            unittest.defaultTestLoader.loadTestsFromTestCase(v12.NamedSourcesAndSubjects),
            unittest.defaultTestLoader.loadTestsFromTestCase(v13.SourceValuePreservation),
            unittest.defaultTestLoader.loadTestsFromTestCase(v14.FlatFieldsAndTenure),
            unittest.defaultTestLoader.loadTestsFromTestCase(v15.ScheduleAndNestedAliases),
            unittest.defaultTestLoader.loadTestsFromTestCase(SeparateMetadataAndLiteralHoles)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
