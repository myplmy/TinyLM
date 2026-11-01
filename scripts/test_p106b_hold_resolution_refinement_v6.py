#!/usr/bin/env python3
"""Old terminal calls must satisfy the new local evidence before reuse."""
from contextlib import contextmanager
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_refinement_v6 as refinement
from scripts import test_p106b_hold_resolution_refinement_v5 as inherited


@contextmanager
def fake_replay(*args):
    yield None


class LocalLiteralReplay(unittest.TestCase):
    def make(self, raw):
        r4 = refinement.previous.previous
        test_v3 = inherited.inherited.inherited
        with patch.object(r4, "policy", refinement.policy), patch.object(test_v3, "refinement", r4):
            row, selector, calls, frozen = test_v3.RecheckChangedPreservation.make(self, raw, raw)
            result = selector.propose(row)
        return result, selector, calls, frozen, row

    def test_global_program_word_cannot_reuse_an_unproved_abbreviation(self):
        result, selector, calls, frozen, row = self.make("ABC: 프로그래밍 언어\nABC(): 매체량공사기구\n")
        self.assertEqual(result["decision"], "PENDING")
        self.assertEqual(calls, [row["id"]])
        self.assertIs(selector.records[row["original_text_sha256"]], frozen)

    def test_actual_method_reference_still_reuses_the_identical_literal(self):
        result, _, calls, _, _ = self.make("clone() 메서드를 선언한다.\n")
        self.assertEqual(result["decision"], "EDIT")
        self.assertEqual(calls, [])

    def test_typed_declaration_is_not_rewritten_as_an_optional_alias(self):
        result, _, calls, _, _ = self.make("C++ programming\nint getData();\n")
        self.assertEqual(result["decision"], "EDIT")
        self.assertEqual(calls, [])

    def test_new_wrapper_restores_its_previous_policy_when_interrupted(self):
        before = refinement.previous.policy
        with patch.object(refinement.previous, "refinement", fake_replay):
            with self.assertRaisesRegex(ValueError, "context-end"):
                with refinement.refinement(None, "old", refinement.policy, []):
                    self.assertIs(refinement.previous.policy, refinement.policy)
                    raise ValueError("context-end")
        self.assertIs(refinement.previous.policy, before)


if __name__ == "__main__":
    v5, v4 = inherited, inherited.inherited
    v3, v2 = v4.inherited, v4.inherited.inherited
    v1 = v2.inherited
    r4 = refinement.previous.previous
    with patch.object(refinement.previous, "policy", refinement.policy), \
            patch.object(r4, "policy", refinement.policy), \
            patch.object(v3, "refinement", r4), patch.object(v2, "refinement", r4), \
            patch.object(v1, "refinement", r4):
        classes = [v1.FrozenDraftTests, v2.OriginalBoundaryCases, v3.RecheckChangedPreservation,
                   v4.RecheckLiteralHoles, v5.NewContextHoleReplay, LocalLiteralReplay]
        suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(value) for value in classes])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
