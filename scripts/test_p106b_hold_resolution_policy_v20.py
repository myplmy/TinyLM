#!/usr/bin/env python3
"""Regression counters for local syntax, retained values, and real UI tails."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v20 as policy
from scripts import test_p106b_hold_resolution_policy_v19 as inherited


class SourceLocalSyntax(unittest.TestCase):
    def test_dart_main_definition_is_proved_on_its_actual_line(self):
        self.assertTrue(policy.local_calls_proven("main() {\n  print('Hello World!');\n}\n"))

    def test_java_assignment_keeps_chained_empty_argument_methods(self):
        text = "Class type = ClassLoader.getSystemClassLoader().loadClass(name);\nObject obj = type.newInstance();\n"
        self.assertTrue(policy.local_calls_proven(text))

    def test_function_reference_is_linked_to_an_actual_source_declaration(self):
        text = "int sprintf(char *str, const char *format, ...)\nsprintf()는 문자열 변환에 쓰인다.\n"
        self.assertTrue(policy.local_calls_proven(text))

    def test_member_in_same_class_explanation_is_retained(self):
        self.assertTrue(policy.local_calls_proven("The class object of the service (e.g. service.getClass()) can be inspected.\n"))

    def test_a_programming_word_elsewhere_cannot_prove_an_abbreviation(self):
        self.assertFalse(policy.local_calls_proven("Programming uses functions.\n\nABC(): agency.\n"))

    def test_one_proved_call_does_not_excuse_an_unfilled_field(self):
        self.assertFalse(policy.local_calls_proven("main() {\n}\nABC(): agency.\n"))

    def test_coordinates_are_not_local_calls(self):
        self.assertFalse(policy.local_calls_proven("좌표(, )는 점의 위치이다.\n"))

    def test_empty_tuple_teaching_does_not_acquire_an_identifier(self):
        self.assertFalse(policy.local_calls_proven("Python의 빈 튜플 ()를 설명한다.\n"))

    def test_alias_preserves_the_real_semicolon_and_both_names(self):
        text = "프로그램 언어의 다형성(多形性, ; 폴리모피즘)은 자료형 체계의 성질이다. 반댓말은 단형성()으로, 한 형태만 허용한다.\n"
        clean, changes = policy.source_nominal_separators(text)
        self.assertEqual(clean, "프로그램 언어의 다형성(多形性 ; 폴리모피즘)은 자료형 체계의 성질이다. 반댓말은 단형성으로, 한 형태만 허용한다.\n")
        self.assertEqual(len(changes), 2)

    def test_numeric_fields_and_formal_values_are_not_aliases(self):
        for text in ["좌표(3, ; 4)는 순서쌍이다.\n", "함수(函數, ; 정의역)는 식이다.\n"]:
            self.assertEqual(policy.source_nominal_separators(text), (text, []))

    def test_exact_assessment_cta_removes_both_copies(self):
        line = "To get assessed to see what infection you may have, click here!\n"
        text = "A complete introduction.\n" + line + "A separate explanation.\n" + line
        clean, changes = policy.source_cta(text)
        self.assertEqual(clean, "A complete introduction.\nA separate explanation.\n")
        self.assertEqual(len(changes), 2)

    def test_quoted_cta_and_protected_literal_are_not_removed(self):
        for text in ["The banner says:\nTo order these tests, click here!\n", "```text\nTo order these tests, click here!\n```\n"]:
            self.assertEqual(policy.source_cta(text), (text, []))

    def test_actual_subscription_tail_requires_fresh_context(self):
        self.assertIn("OBSERVED_SEARCH_SUBSCRIPTION_OR_PROMOTIONAL_PREVIEW_REQUIRES_CONTEXT",
                      policy.literal_holes("An independent math explanation.\nAlgebra Lessons on DVD\n"))

    def test_legitimate_reference_and_empty_formula_guards_remain(self):
        self.assertNotIn("OBSERVED_SEARCH_SUBSCRIPTION_OR_PROMOTIONAL_PREVIEW_REQUIRES_CONTEXT",
                         policy.literal_holes("참고 문헌\nJournal of Algebra, volume 3, pages 4–9.\n"))
        self.assertIn("ANNOUNCED_FORMAL_DEFINITION_HAS_ONLY_BARE_PUNCTUATION",
                      policy.literal_holes("그 텐서는 다음과 같다.\n.\n"))


if __name__ == "__main__":
    modules, pending = [], [inherited]
    while pending:
        module = pending.pop()
        if module in modules:
            continue
        modules.append(module)
        pending.extend(value for name in ["inherited", "local_inherited"]
                       if (value := getattr(module, name, None)) is not None)
    classes = [SourceLocalSyntax]
    for module in modules:
        classes += [value for value in vars(module).values() if isinstance(value, type)
                    and issubclass(value, unittest.TestCase) and value.__module__ == module.__name__]
    with ExitStack() as stack:
        for module in modules:
            if hasattr(module, "policy"):
                stack.enter_context(patch.object(module, "policy", policy))
        suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(value) for value in classes])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
