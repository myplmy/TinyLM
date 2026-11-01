#!/usr/bin/env python3
"""Regress retained names, missing operands and misleading program words."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v18 as policy
from scripts import test_p106b_hold_resolution_policy_v17 as inherited


class FirstNominalAndLocalCalls(unittest.TestCase):
    def test_new_typed_nominal_body_is_actually_terminal(self):
        source = "로봇(, )은 작업을 수행하는 기계장치다.\n"
        value = policy.propose(dict(id="expanded_train:18", text=source, complete_eos=True, valid_utf8=True))
        self.assertEqual(value["decision"], "EDIT", value)
        self.assertEqual(value["text"], source.replace("(, )", ""))

    def test_a_new_alias_cannot_remove_a_real_later_value_hole(self):
        source = "로봇(, )은 작업을 수행하는 기계장치다.\n\n질량은 kg이다.\n"
        value = policy.propose(dict(id="expanded_train:18", text=source, complete_eos=True, valid_utf8=True))
        self.assertEqual(value["decision"], "PENDING", value)

    def test_quoted_title_retains_both_name_and_phonetic_value(self):
        source = "〈Grip!〉(그립, )는 어느 그룹의 싱글이다.\n"
        clean, changes = policy.first_nominal_alias(source)
        self.assertEqual(clean, "〈Grip!〉(그립)는 어느 그룹의 싱글이다.\n")
        self.assertTrue(changes)
        self.assertTrue(policy.ordered_deletion(source, clean))

    def test_han_alias_survives_a_technical_word_elsewhere(self):
        source = "벡터 공간(線型空間, )은 여러 성질이 있는 공간이다.\n"
        clean, changes = policy.first_nominal_alias(source)
        self.assertEqual(clean, source.replace(", )", ")"))
        self.assertTrue(changes)

    def test_typed_machine_definition_can_remove_empty_optional_comma_fields(self):
        source = "로봇(, )은 작업을 수행하는 기계장치다.\n"
        self.assertEqual(policy.first_nominal_alias(source)[0], source.replace("(, )", ""))

    def test_coordinate_operand_hole_is_not_an_alias(self):
        source = "좌표(, )는 두 성분의 순서쌍이다.\n"
        self.assertEqual(policy.first_nominal_alias(source), (source, []))

    def test_populated_number_and_operator_never_enter_the_new_alias_proof(self):
        for fields in [", 3", "a + b,", "←, 원어", "[, 한자"]:
            source = "가람(" + fields + ")은 어느 기계장치다.\n"
            self.assertEqual(policy.first_nominal_alias(source), (source, []))

    def test_literal_comma_glyph_is_preserved(self):
        source = "반점(,)은 문장 부호이다.\n"
        self.assertEqual(policy.first_nominal_alias(source), (source, []))

    def test_normal_empty_call_without_a_comma_is_not_a_name_edit(self):
        source = "후킹()은 메서드 호출을 설명하는 용어이다.\n"
        self.assertEqual(policy.first_nominal_alias(source), (source, []))

    def test_incomplete_definition_is_not_used_to_release_an_alias(self):
        source = "가람(, )은 작업을 수행하는 기계장치로"
        self.assertEqual(policy.first_nominal_alias(source), (source, []))

    def test_protected_code_is_never_an_article_intro(self):
        source = "```text\n가람(, )은 어느 기계장치다.\n```\n"
        self.assertEqual(policy.first_nominal_alias(source), (source, []))

    def test_explicit_method_reference_preserves_every_call(self):
        text = "clone() 메소드를 선언한다. clone() 메소드의 구현을 설명한다.\n"
        self.assertTrue(policy.local_calls_proven(text))

    def test_typed_declaration_and_standalone_call_are_literal_syntax(self):
        text = "C++ programming\nint getData();\ngetData();\n"
        self.assertTrue(policy.local_calls_proven(text))

    def test_other_programming_entry_does_not_turn_an_abbreviation_into_a_call(self):
        text = "ABC: 프로그래밍 언어\nABC(): 매체량공사기구\n"
        self.assertFalse(policy.local_calls_proven(text))
        self.assertIn("GLOBAL_PROGRAM_WORD_DOES_NOT_PROVE_EACH_EMPTY_PAREN_LITERAL", policy.literal_holes(text))

    def test_one_unproved_slot_prevents_whole_article_call_release(self):
        text = "clone() 메서드를 설명한다.\n저자의 이름은 ()이다.\n"
        self.assertFalse(policy.local_calls_proven(text))

    def test_a_call_cannot_excuse_an_empty_title(self):
        self.assertFalse(policy.local_calls_proven("clone() 메서드와 《》를 설명한다.\n"))

    def test_two_filled_aliases_remain_in_their_source_order(self):
        source = "《가람》(별칭, , 다른 별칭)는 어느 앨범이다.\n"
        clean, _ = policy.first_nominal_alias(source)
        self.assertIn("(별칭, 다른 별칭)", clean)
        self.assertTrue(policy.ordered_deletion(source, clean))


if __name__ == "__main__":
    modules = []
    pending = [inherited]
    while pending:
        module = pending.pop()
        if module in modules:
            continue
        modules.append(module)
        for name in ["inherited", "local_inherited"]:
            value = getattr(module, name, None)
            if value is not None:
                pending.append(value)
    classes = [FirstNominalAndLocalCalls]
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
