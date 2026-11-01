#!/usr/bin/env python3
"""Independent counter regressions for absent formulae and their variables."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v19 as policy
from scripts import test_p106b_hold_resolution_policy_v18 as inherited


class ActualFormulaCounter(unittest.TestCase):
    def test_component_definition_with_a_bare_period_is_not_terminal(self):
        text = "전자기 퍼텐셜(電磁氣potential, )은 전기 퍼텐셜과 자기 퍼텐셜로 이루어진 사차원 벡터다. 즉 그 성분 는 다음과 같다.\n.\n여기서\n 는 스칼라 전기 퍼텐셜\n 는 벡터 자기 퍼텐셜\n"
        value = policy.propose(dict(id="expanded_train:19", text=text, complete_eos=True, valid_utf8=True))
        self.assertEqual(value["decision"], "PENDING", value)
        self.assertIn("ANNOUNCED_FORMAL_DEFINITION_HAS_ONLY_BARE_PUNCTUATION", value["reasons"])
        self.assertIn("WHERE_BLOCK_FORMAL_VARIABLE_IS_ACTUALLY_ABSENT", value["reasons"])
        self.assertIn("사차원 벡터", value.get("candidate", value["text"]))

    def test_actual_formula_is_not_a_bare_period(self):
        text = "그 성분은 다음과 같다.\nT = x + y.\n여기서\nx는 스칼라이다.\n"
        self.assertEqual(policy.new_formula_holes(text), [])

    def test_a_where_block_with_actual_variables_is_not_missing(self):
        self.assertEqual(policy.new_formula_holes("여기서\nx는 스칼라이고 v는 벡터이다.\n"), [])

    def test_punctuation_teaching_without_a_formal_definition_is_not_a_formula_hole(self):
        self.assertEqual(policy.new_formula_holes("마침표는 다음과 같다.\n.\n"), [])

    def test_protected_code_literal_is_preserved(self):
        text = "```python\n# 함수는 다음과 같다.\n.\n```\n"
        self.assertEqual(policy.new_formula_holes(text), [])

    def test_bare_punctuation_is_retained_for_review_never_synthesized(self):
        text = "그 텐서는 다음과 같이 주어진다.\n\n.\n"
        self.assertIn("ANNOUNCED_FORMAL_DEFINITION_HAS_ONLY_BARE_PUNCTUATION", policy.new_formula_holes(text))

    def test_unknown_variable_references_do_not_become_names(self):
        self.assertIn("WHERE_BLOCK_FORMAL_VARIABLE_IS_ACTUALLY_ABSENT",
                      policy.new_formula_holes("여기서\n\n 는 벡터이다.\n"))


if __name__ == "__main__":
    modules, pending = [], [inherited]
    while pending:
        module = pending.pop()
        if module in modules:
            continue
        modules.append(module)
        pending.extend(value for name in ["inherited", "local_inherited"]
                       if (value := getattr(module, name, None)) is not None)
    classes = [ActualFormulaCounter]
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
