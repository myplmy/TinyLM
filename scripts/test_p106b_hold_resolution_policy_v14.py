#!/usr/bin/env python3
"""Regression coverage for source-labelled values and explicitly typed dates."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v14 as policy
from scripts import test_p106b_hold_resolution_policy_v13 as inherited


class FlatFieldsAndTenure(unittest.TestCase):
    def value(self, text, **extra):
        return policy.propose(dict(id="expanded_train:14", text=text, complete_eos=True, valid_utf8=True, **extra))

    def sample(self, fields="", suffix=None):
        return ("{{축구 선수 정보\n|이름=가람\n|출생일=\n" + fields +
                "}}" + (suffix or "가람(, 1960년 7월 17일 ~)은 대한민국의 전 축구 선수이다.\n\n1960년 출생\n살아있는 사람\n"))

    def test_filled_parallel_arrays_remain_separate_and_literal(self):
        source = self.sample("|클럽 연도=1979–1980  1980–1981  합계\n|클럽=토리노  아탈란타\n|출장수(골)=27 (0)34 (1)  61 (1)\n")
        value = self.value(source)
        self.assertEqual(value["decision"], "EDIT", value)
        for record in ["클럽 연도=1979–1980  1980–1981  합계", "클럽=토리노  아탈란타", "출장수(골)=27 (0)34 (1)  61 (1)"]:
            self.assertIn(record, value["text"])
        self.assertNotIn("{{", value["text"])
        self.assertNotIn("|", value["text"])
        self.assertTrue(policy.ordered_deletion(source, value["text"]))
        self.assertFalse(value["changes"][0]["array_pairing_inferred"])

    def test_prefix_fields_have_independent_paragraph_boundaries(self):
        flat = policy.flat_football(self.sample("|키=178cm\n|포지션=감독 (과거 수비수)\n"))
        self.assertIn("키=178cm\n\n포지션=감독", flat["prefix"])
        self.assertEqual(flat["populated"], ["이름=가람", "키=178cm", "포지션=감독 (과거 수비수)"])

    def test_nested_template_is_not_flat(self):
        source = self.sample("|클럽={{다른 틀}}\n")
        self.assertIsNone(policy.flat_football(source))
        self.assertEqual(self.value(source)["decision"], "PENDING")

    def test_unclosed_template_stays_pending(self):
        source = self.sample().replace("}}", "")
        self.assertIsNone(policy.flat_football(source))
        self.assertEqual(self.value(source)["decision"], "PENDING")

    def test_duplicate_label_cannot_silently_replace_a_value(self):
        self.assertIsNone(policy.flat_football(self.sample("|키=178cm\n|키=179cm\n")))

    def test_unknown_label_requires_observed_context(self):
        self.assertIsNone(policy.flat_football(self.sample("|새로운 필드=값\n")))

    def test_no_independent_named_biography_is_not_an_admission(self):
        source = self.sample(suffix="각주\n외부 링크\n")
        self.assertIsNone(policy.flat_football(source))
        self.assertEqual(self.value(source)["decision"], "PENDING")

    def test_labelled_name_must_be_the_actual_body_subject(self):
        self.assertIsNone(policy.flat_football(self.sample(suffix="나래는 대한민국의 축구 선수이다.\n")))

    def test_a_name_mentioned_as_an_opponent_is_not_the_body_subject(self):
        self.assertIsNone(policy.flat_football(self.sample(suffix="나래는 가람과 경기한 대한민국의 축구 선수이다.\n")))

    def test_empty_nickname_with_two_topic_particles_needs_authored_repair(self):
        source = self.sample(suffix="가람은 흔히 가람'()는 대한민국의 전 축구 선수이다.\n")
        self.assertIsNone(policy.flat_football(source))
        self.assertEqual(self.value(source)["decision"], "PENDING")

    def test_actual_birth_field_conflict_is_not_hidden(self):
        source = self.sample().replace("|출생일=", "|출생일=1970년 7월 17일")
        self.assertIsNone(policy.flat_football(source))
        self.assertEqual(self.value(source)["decision"], "PENDING")

    def test_source_styling_needs_separate_literal_handling(self):
        source = self.sample('|포지션=<span style="color:red">수비수</span>\n')
        self.assertIsNone(policy.flat_football(source))
        self.assertEqual(self.value(source)["decision"], "PENDING")

    def test_template_grammar_in_a_lesson_remains_literal(self):
        source = "```wiki\n" + self.sample() + "```\n"
        value = self.value(source)
        self.assertEqual(value.get("candidate", value["text"]), source)
        self.assertTrue(policy.code_preserved(source, value.get("candidate", value["text"])))

    def test_existing_individual_hold_is_never_auto_released(self):
        value = self.value(self.sample(), previous_holds=["individual source review"])
        self.assertEqual(value["decision"], "PENDING")

    def test_explicit_tenure_is_not_birth(self):
        source = "가람은 정치인이다. 가람(재임: 2000년 1월 1일 ~ 2004년 1월 1일)은 의장을 지냈다.\n\n1900년 출생\n"
        self.assertTrue(policy.ORIGINAL_CONFLICT(source))
        self.assertFalse(policy.conflicting_birth_year(source))
        self.assertNotIn("INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED", self.value(source)["reasons"])

    def test_real_lifespan_conflict_remains(self):
        source = "가람(1900년 1월 1일 ~ 1980년 1월 1일)은 정치인이다.\n\n1901년 출생\n"
        self.assertTrue(policy.conflicting_birth_year(source))
        self.assertIn("INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED", self.value(source)["reasons"])

    def test_tenure_elsewhere_cannot_release_a_birth_conflict(self):
        source = "가람(1900년 1월 1일 ~)은 정치인이다. 가람(재위: 2000년 1월 1일 ~ 2004년 1월 1일)은 왕이다.\n\n1901년 출생\n"
        self.assertTrue(policy.conflicting_birth_year(source))

    def test_conflicting_birth_categories_remain(self):
        source = "가람(재위: 2000년 1월 1일 ~ 2004년 1월 1일)은 왕이다.\n\n1900년 출생\n1901년 출생\n"
        self.assertTrue(policy.conflicting_birth_year(source))

    def test_untyped_date_is_not_a_tenure_proof(self):
        source = "가람(2000년 1월 1일 ~ 2004년 1월 1일)은 정치인이다.\n\n1900년 출생\n"
        self.assertTrue(policy.conflicting_birth_year(source))


if __name__ == "__main__":
    v13, v12 = inherited, inherited.inherited
    v11, v10 = v12.inherited, v12.inherited.inherited
    v9, v8 = v10.inherited, v10.inherited.inherited
    v7 = v8.inherited
    modules = [v13, v12, v11, v10, v9, v8, v7, v7.inherited, v7.local_inherited]
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
            unittest.defaultTestLoader.loadTestsFromTestCase(FlatFieldsAndTenure)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
