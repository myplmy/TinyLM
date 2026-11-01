#!/usr/bin/env python3
"""Frozen bodies must retain proved source calls even after all signals vanish."""
from contextlib import ExitStack, contextmanager
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_refinement_v9 as refinement
from scripts import test_p106b_hold_resolution_refinement_v8 as inherited


@contextmanager
def fake_replay(*args):
    yield None


class FreshSourceCallReplay(unittest.TestCase):
    def make(self, source, candidate):
        v3 = inherited.inherited.inherited.inherited.inherited.inherited
        row, selector, calls, frozen = v3.RecheckChangedPreservation.make(self, source, candidate)
        value = selector.propose(row)
        return value, selector, calls, frozen, row

    def test_a_removed_function_call_has_no_remaining_empty_paren_signal(self):
        source = "int sprintf(char *s, const char *f, ...)\nsprintf()는 문자열을 쓴다.\n"
        value, selector, calls, frozen, row = self.make(source, source.replace("sprintf()는", "sprintf는"))
        self.assertEqual(calls, [row["id"]])
        self.assertEqual(value["decision"], "PENDING")
        self.assertIs(selector.records[row["original_text_sha256"]], frozen)
        self.assertEqual(selector.last["rechecked_source_function_parentheses_loss"], {"sprintf": 1})

    def test_the_same_proved_call_body_remains_exact_and_reusable(self):
        source = "int sprintf(char *s, const char *f, ...)\nsprintf()는 문자열을 쓴다.\n"
        value, _, calls, _, _ = self.make(source, source)
        self.assertEqual(calls, [])
        self.assertEqual(value["text"], source)

    def test_unicode_and_selector_bindings_restore_after_an_exception(self):
        selector, guard = refinement.v4.FrozenDraftSelector, refinement.base.guards.unicode_examples_preserved
        with patch.object(refinement.previous, "refinement", fake_replay):
            with self.assertRaisesRegex(ValueError, "context-end"):
                with refinement.refinement(None, "old", refinement.policy, []):
                    self.assertIs(refinement.v4.FrozenDraftSelector, refinement.FrozenDraftSelector)
                    self.assertIs(refinement.base.guards.unicode_examples_preserved, refinement.policy.unicode_examples_preserved)
                    self.assertTrue(refinement.policy.unicode_examples_preserved("U+1B001()", "U+1B001"))
                    raise ValueError("context-end")
        self.assertIs(refinement.v4.FrozenDraftSelector, selector)
        self.assertIs(refinement.base.guards.unicode_examples_preserved, guard)


if __name__ == "__main__":
    v7, v6 = inherited.inherited, inherited.inherited.inherited
    v5, v4 = v6.inherited, v6.inherited.inherited
    v3, v2 = v4.inherited, v4.inherited.inherited
    v1 = v2.inherited
    r8, r7 = refinement.previous, refinement.previous.previous
    r6, r5 = r7.previous, r7.previous.previous
    with ExitStack() as stack:
        for module in [r8, r7, r6, r5, refinement.v4]:
            stack.enter_context(patch.object(module, "policy", refinement.policy))
        for module in [v3, v2, v1]:
            stack.enter_context(patch.object(module, "refinement", refinement.v4))
        stack.enter_context(patch.object(refinement.v4, "FrozenDraftSelector", refinement.FrozenDraftSelector))
        classes = [v1.FrozenDraftTests, v2.OriginalBoundaryCases, v3.RecheckChangedPreservation,
                   v4.RecheckLiteralHoles, v5.NewContextHoleReplay, v6.LocalLiteralReplay,
                   v7.FormulaHoleReplay, inherited.ObservedTailReplay, FreshSourceCallReplay]
        suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(value) for value in classes])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
