#!/usr/bin/env python3
"""Source context regressions for v15, including all inherited v14 tests."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v15 as policy
from scripts import test_p106b_hold_resolution_policy_v14 as inherited


class ScheduleAndNestedAliases(unittest.TestCase):
    def value(self, text):
        return policy.propose(dict(id="expanded_train:15", text=text, complete_eos=True, valid_utf8=True))

    def test_weekday_repeats_are_kept_in_their_distinct_contexts(self):
        text = "가람은 대한민국의 라디오 프로그램이다.\n\n화요일\n닥터 Q(가정의학과 전문의)\n\n목요일\n닥터 Q(가정의학과 전문의)\n"
        self.assertTrue(policy.explicit_schedule_repetition(text))
        self.assertEqual(self.value(text)["decision"], "KEEP")
        self.assertEqual(self.value(text)["text"], text)

    def test_directions_do_not_delete_identical_shared_route_values(self):
        text = "가람은 대한민국의 휴게소이다.\n\n서산 방면\n예산 휴게소←가람휴게소→공주휴게소\n\n영덕 방면\n예산 휴게소←가람휴게소→공주휴게소\n"
        self.assertTrue(policy.explicit_schedule_repetition(text))
        self.assertEqual(self.value(text)["text"], text)

    def test_repeat_twice_inside_one_day_stays_pending(self):
        text = "가람은 대한민국의 라디오 프로그램이다.\n\n화요일\n같은 프로그램 이름\n같은 프로그램 이름\n\n목요일\n다른 프로그램 이름\n"
        self.assertFalse(policy.explicit_schedule_repetition(text))
        self.assertEqual(self.value(text)["decision"], "PENDING")

    def test_two_unlabelled_paragraphs_are_not_distinct_schedule_contexts(self):
        text = "가람은 대한민국의 라디오 프로그램이다.\n\n같은 프로그램 이름\n\n같은 프로그램 이름\n"
        self.assertFalse(policy.explicit_schedule_repetition(text))
        self.assertEqual(self.value(text)["decision"], "PENDING")

    def test_balanced_nested_abbreviation_stays_literal(self):
        text = "가람 대표부(, , 준말: DECM (OMC))는 마카오의 기구이다.\n"
        clean, changes = policy.initial_balanced_alias(text)
        self.assertEqual(clean, "가람 대표부(준말: DECM (OMC))는 마카오의 기구이다.\n")
        self.assertEqual(len(changes), 1)
        self.assertTrue(policy.ordered_deletion(text, clean))

    def test_named_novel_with_literal_tilde_loses_only_empty_alias(self):
        text = "진화의 열매 ~모르는 사이 성공한 인생~()는 일본의 소설 작품이다.\n"
        clean, _ = policy.initial_balanced_alias(text)
        self.assertEqual(clean, text.replace("()", ""))
        self.assertEqual(self.value(text)["decision"], "EDIT")

    def test_filled_foreign_names_and_dates_are_unchanged(self):
        text = "가람(甲, Garam, 1900년 1월 1일 ~)은 대한민국의 작가이다.\n"
        self.assertEqual(policy.initial_balanced_alias(text), (text, []))

    def test_empty_function_arguments_are_not_optional_foreign_names(self):
        for text in ["가람()은 함수이다.\n", "가람(, , x(y))은 수학의 함수이다.\n"]:
            self.assertEqual(policy.initial_balanced_alias(text), (text, []))

    def test_empty_measured_quantity_is_never_erased(self):
        text = "인구()는 도시의 인구 수이다.\n"
        self.assertEqual(policy.initial_balanced_alias(text), (text, []))
        self.assertEqual(self.value(text)["decision"], "PENDING")

    def test_unbalanced_nested_parenthesis_requires_authored_review(self):
        text = "가람 대표부(, , 준말: DECM (OMC)는 마카오의 기구이다.\n"
        self.assertEqual(policy.initial_balanced_alias(text), (text, []))

    def test_missing_subject_predicate_is_not_repaired_by_alias_deletion(self):
        text = "가람(, 1985년 8월 16일 ~)는 일본의.\n"
        self.assertEqual(policy.initial_balanced_alias(text), (text, []))
        self.assertEqual(self.value(text)["decision"], "PENDING")

    def test_multiple_outer_groups_are_not_guessed_into_one_alias(self):
        text = "가람(), (), (1999년 4월 27일 ~)은 대한민국의 가수이다.\n"
        self.assertEqual(policy.initial_balanced_alias(text), (text, []))


if __name__ == "__main__":
    v14, v13 = inherited, inherited.inherited
    v12, v11 = v13.inherited, v13.inherited.inherited
    v10, v9 = v11.inherited, v11.inherited.inherited
    v8, v7 = v9.inherited, v9.inherited.inherited
    modules = [v14, v13, v12, v11, v10, v9, v8, v7, v7.inherited, v7.local_inherited]
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
            unittest.defaultTestLoader.loadTestsFromTestCase(ScheduleAndNestedAliases)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
