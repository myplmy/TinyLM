#!/usr/bin/env python3
"""Source value/call-loss and complete-structure counters with old regressions."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v21 as policy
from scripts import test_p106b_hold_resolution_policy_v20 as inherited
from scripts import test_p106b_hold_resolution_structure_v1 as structure_tests
from scripts import test_p106b_hold_resolution_preservation_v1 as preservation_tests
from scripts import test_p106b_hold_resolution_policy_v13 as style_tests


class ActualSourceCallValues(unittest.TestCase):
    def test_pointer_assignment_and_its_actual_comment_prove_getch(self):
        self.assertTrue(policy.local_calls_proven("*piaddr = getch(); // getch 함수로 키를 읽는다.\n"))

    def test_unrelated_comment_role_does_not_prove_an_alias(self):
        self.assertFalse(policy.local_calls_proven("ABC(): agency. // 다른 메서드 설명\n"))

    def test_language_usage_row_has_a_real_bounded_heading(self):
        text = "printf를 이용하는 프로그래밍 언어\n Vala (print() 및 FileStream.printf()을 통해)\n"
        self.assertTrue(policy.local_calls_proven(text))
        self.assertFalse(policy.local_calls_proven("Vala (print() 및 FileStream.printf()을 통해)\n"))
        self.assertFalse(policy.local_calls_proven(text.split(chr(10))[0] + "\n같이 보기\n" + text.split(chr(10))[1]))

    def test_an_exact_source_sql_function_reference_is_not_an_empty_alias(self):
        self.assertTrue(policy.local_calls_proven("Alternative Queries 문제 RECURSIVE(CTE: Common Table Expressions) 와 REPEAT( )"))
        self.assertFalse(policy.local_calls_proven("Alternative Queries 문제 ABC()"))

    def test_adding_another_missing_value_does_not_borrow_call_evidence(self):
        text = "*piaddr = getch(); // getch 함수\n좌표(, )는 점이다.\n"
        self.assertFalse(policy.local_calls_proven(text))

    def test_source_function_parentheses_cannot_silently_disappear(self):
        source = "int sprintf(char *s, const char *f, ...)\nsprintf()는 문자열을 쓴다.\n"
        broken = source.replace("sprintf()는", "sprintf는")
        self.assertEqual(policy.proven_source_call_losses(source, broken), {"sprintf": 1})
        repaired, changes, unresolved = policy.calls.restore_source_call_anchors(source, broken)
        self.assertEqual(repaired, source)
        self.assertFalse(unresolved)
        self.assertEqual(len(changes), 1)

    def test_another_korean_particle_is_not_the_same_source_anchor(self):
        source = "sprintf에서부터 파생되었다.\nint sprintf(char *s, const char *f, ...)sprintf()는 문자열을 쓴다.\n"
        repaired, _, unresolved = policy.calls.restore_source_call_anchors(source, source.replace("sprintf()는", "sprintf는"))
        self.assertEqual(repaired, source)
        self.assertFalse(unresolved)

    def test_another_unfilled_alias_does_not_hide_a_proved_source_call_loss(self):
        source = "int sprintf(char *s, const char *f, ...)\nsprintf()는 문자열을 쓴다.\n미상(): 설명\n"
        self.assertEqual(policy.proven_source_call_losses(source, source.replace("sprintf()는", "sprintf는")), {"sprintf": 1})

    def test_existing_bare_source_word_makes_restoration_ambiguous(self):
        source = "int sprintf(char *s, const char *f, ...)\nsprintf()는 문자열을 쓴다.\nsprintf는 별도 원문이다.\n"
        broken = source.replace("sprintf()는", "sprintf는")
        repaired, changes, unresolved = policy.calls.restore_source_call_anchors(source, broken)
        self.assertEqual(repaired, broken)
        self.assertFalse(changes)
        self.assertEqual(unresolved, {"sprintf": 1})

    def test_removed_whole_call_statement_is_not_filled_from_knowledge(self):
        source = "int work();\nwork();\n"
        repaired, changes, unresolved = policy.calls.restore_source_call_anchors(source, "int work();\n")
        self.assertEqual(repaired, "int work();\n")
        self.assertFalse(changes)
        self.assertEqual(unresolved, {"work": 1})

    def test_named_api_definition_only_removes_an_empty_alias(self):
        text = "윈도우 API()는 운영 체제용 API이다.\n"
        clean, changes = policy.source_api_definition(text)
        self.assertEqual(clean, "윈도우 API는 운영 체제용 API이다.\n")
        self.assertEqual(len(changes), 1)
        for bad in ["윈도우 API()는 함수의 인수이다.\n", "함수 API()는 API이다.\n", "윈도우 API(값)는 API이다.\n"]:
            self.assertEqual(policy.source_api_definition(bad), (bad, []))

    def test_proven_calls_do_not_remove_other_source_risks(self):
        risks = policy.structural_reasons("*piaddr = getch(); // getch 함수\n", {"INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED", "OBSERVED_MISSING_MEASURED_QUANTITY"})
        self.assertEqual(risks, {"INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED", "OBSERVED_MISSING_MEASURED_QUANTITY"})

    def test_actual_printf_source_keeps_sprintf_and_source_format_bytes(self):
        path = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_candidate_context_v19_v1/originals/expanded_train_317013_original.txt"
        source = path.read_text(encoding="utf-8")
        value = policy.propose(dict(id="expanded_train:317013", text=source, complete_eos=True, valid_utf8=True))
        clean = value.get("candidate", value["text"])
        self.assertIn("sprintf()는", clean)
        self.assertIn('printf("%s",text);', clean)
        self.assertIn("print() 및 FileStream.printf()", clean)
        self.assertFalse(policy.proven_source_call_losses(source, clean))

    def test_actual_question_ui_counter_is_not_an_automatic_complete_body(self):
        path = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc/draft_proposals_v11/review_packets/expanded_train_940988_original.txt"
        value = policy.propose(dict(id="expanded_train:940988", text=path.read_text(), complete_eos=True, valid_utf8=True))
        self.assertEqual(value["decision"], "PENDING")
        self.assertIn("OBSERVED_QUESTION_ANSWER_OR_JOIN_UI_REQUIRES_CONTEXT", value["reasons"])

    def test_quoted_and_fenced_join_text_are_literal_examples(self):
        for text in ["The banner says:\nJoin to answer this question\n", "```text\nJoin to answer this question\n```\n"]:
            self.assertNotIn("OBSERVED_QUESTION_ANSWER_OR_JOIN_UI_REQUIRES_CONTEXT", policy.literal_holes(text))

    def test_actual_baseball_counter_keeps_missing_record_legend_pending(self):
        path = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_profile_v14_v1/review_packets/expanded_train_166766_original.txt"
        value = policy.propose(dict(id="expanded_train:166766", text=path.read_text(), complete_eos=True, valid_utf8=True))
        self.assertEqual(value["decision"], "PENDING")
        self.assertIn("UNBOUND_SOURCE_RECORD_STYLE_LEGEND_REQUIRES_CONTEXT", value["reasons"])


class RetainedStyleInsteadOfRenderedLoss(style_tests.SourceValuePreservation):
    """The v13 loss case now retains the original color and item together.

    All other v13 assertions remain inherited. This one expectation changes
    because the renderer no longer removes the value; it never waives a loss.
    """
    def test_lost_route_colour_keeps_the_proposal_pending(self):
        source = '가람여객은 대한민국의 버스 회사이다.\n\n운행 노선\n<span style="color:#6EBF46;">●</span> 5번: 항구 ~ 역\n'
        value = self.value(source)
        clean = value.get("candidate", value["text"])
        self.assertEqual(clean, source)
        self.assertEqual(value["decision"], "KEEP")
        self.assertTrue(policy.semantic_style_preserved(source, clean))


if __name__ == "__main__":
    modules, pending = [], [inherited, structure_tests, preservation_tests]
    while pending:
        module = pending.pop()
        if module in modules:
            continue
        modules.append(module)
        pending.extend(value for name in ["inherited", "local_inherited"] if (value := getattr(module, name, None)) is not None)
    classes = [ActualSourceCallValues]
    for module in modules:
        classes += [(RetainedStyleInsteadOfRenderedLoss if value.__name__ == "SourceValuePreservation" else value)
                    for value in vars(module).values() if isinstance(value, type)
                    and issubclass(value, unittest.TestCase) and value.__module__ == module.__name__]
    with ExitStack() as stack:
        for module in modules:
            if hasattr(module, "policy"):
                stack.enter_context(patch.object(module, "policy", policy))
        suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(value) for value in classes])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
