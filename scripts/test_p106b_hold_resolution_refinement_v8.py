#!/usr/bin/env python3
"""Regression of fresh UI checks and locally proved frozen code references."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_refinement_v8 as refinement
from scripts import test_p106b_hold_resolution_refinement_v7 as inherited


class ObservedTailReplay(unittest.TestCase):
    def test_old_subscription_tail_is_not_reused_as_a_clean_body(self):
        value, selector, calls, frozen, row = inherited.inherited.LocalLiteralReplay.make(
            self, "An independent explanation.\nAlgebra Lessons on DVD\n")
        self.assertEqual(value["decision"], "PENDING")
        self.assertEqual(calls, [row["id"]])
        self.assertIs(selector.records[row["original_text_sha256"]], frozen)

    def test_locally_proved_member_syntax_can_reuse_literal_body(self):
        value, _, calls, _, _ = inherited.inherited.LocalLiteralReplay.make(
            self, "Object obj = type.newInstance();\n")
        self.assertEqual(value["decision"], "EDIT")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    v7, v6 = inherited, inherited.inherited
    v5, v4 = v6.inherited, v6.inherited.inherited
    v3, v2 = v4.inherited, v4.inherited.inherited
    v1 = v2.inherited
    r7, r6 = refinement.previous, refinement.previous.previous
    r5, r4 = r6.previous, r6.previous.previous
    with ExitStack() as stack:
        for module in [r7, r6, r5, r4]:
            stack.enter_context(patch.object(module, "policy", refinement.policy))
        for module in [v3, v2, v1]:
            stack.enter_context(patch.object(module, "refinement", r4))
        classes = [v1.FrozenDraftTests, v2.OriginalBoundaryCases, v3.RecheckChangedPreservation,
                   v4.RecheckLiteralHoles, v5.NewContextHoleReplay, v6.LocalLiteralReplay,
                   v7.FormulaHoleReplay, ObservedTailReplay]
        suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(value) for value in classes])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
