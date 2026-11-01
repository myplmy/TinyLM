"""Previously terminal frozen bodies must be checked for a missing role too."""
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_refinement_v10 as refinement
from scripts import test_p106b_hold_resolution_refinement_v9 as inherited
from scripts import test_p106b_hold_resolution_refinement as original_tests
from scripts import p106b_hold_resolution_policy_v24 as current_policy


class ObservedFormalRoleReplay(unittest.TestCase):
    def make(self, text, raises=False):
        row = original_tests.source(text)
        frozen = {key: value for key, value in row.items() if key != "text"}
        frozen.update(decision="KEEP", clean_text_sha256=refinement.previous.base.inv.sha(text),
                      reasons=["old-terminal"], changes=[])
        calls = []
        def propose(fresh, individual=False):
            calls.append(fresh["id"])
            if raises:
                raise ValueError("fresh-role-recheck")
            return dict(decision="PENDING", text=fresh["text"], reasons=["missing-source-role"], changes=[])
        selector = refinement.FrozenDraftSelector([frozen], SimpleNamespace(RULES="NEW", propose=propose))
        return row, frozen, selector, calls

    def test_old_keep_with_missing_coefficient_is_reprocessed(self):
        row, frozen, selector, calls = self.make("여기서 은 주어진 계수들이다.\n")
        self.assertEqual(selector.propose(row)["decision"], "PENDING")
        self.assertEqual(calls, [row["id"]])
        self.assertIs(selector.records[row["original_text_sha256"]], frozen)
        self.assertEqual(len(selector.last["rechecked_frozen_terminal_observed_formal_roles"]), 1)

    def test_actual_symbol_can_reuse_its_exact_body(self):
        row, frozen, selector, calls = self.make("여기서 a는 주어진 계수이다.\n")
        self.assertEqual(selector.propose(row)["text"], row["text"])
        self.assertEqual(calls, [])

    def test_frozen_identity_restores_after_the_new_check_fails(self):
        row, frozen, selector, calls = self.make("여기서 에 따라 방정식의 해를 구한다.\n", raises=True)
        with self.assertRaisesRegex(ValueError, "fresh-role-recheck"):
            selector.propose(row)
        self.assertIs(selector.records[row["original_text_sha256"]], frozen)
        self.assertEqual(frozen["decision"], "KEEP")



class EnglishFormalRoleReplay(ObservedFormalRoleReplay):
    def test_missing_english_role_in_frozen_keep_is_reprocessed(self):
        row, frozen, selector, calls = self.make("The data set consists of points with .")
        self.assertEqual(selector.propose(row)["decision"], "PENDING")
        self.assertEqual(calls, [row["id"]])
        self.assertIs(selector.records[row["original_text_sha256"]], frozen)

if __name__ == "__main__":
    refinement.policy = current_policy
    r9 = refinement.previous
    v8, v7 = inherited.inherited, inherited.inherited.inherited
    v6, v5 = v7.inherited, v7.inherited.inherited
    v4, v3 = v5.inherited, v5.inherited.inherited
    v2, v1 = v3.inherited, v3.inherited.inherited
    r8, r7 = r9.previous, r9.previous.previous
    r6, r5 = r7.previous, r7.previous.previous
    with ExitStack() as stack:
        for module in [r9, r8, r7, r6, r5, r9.v4]:
            stack.enter_context(patch.object(module, "policy", refinement.policy))
        for module in [v3, v2, v1]:
            stack.enter_context(patch.object(module, "refinement", r9.v4))
        stack.enter_context(patch.object(r9.v4, "FrozenDraftSelector", refinement.FrozenDraftSelector))
        classes = [v1.FrozenDraftTests, v2.OriginalBoundaryCases, v3.RecheckChangedPreservation,
                   v4.RecheckLiteralHoles, v5.NewContextHoleReplay, v6.LocalLiteralReplay,
                   v7.FormulaHoleReplay, v8.ObservedTailReplay, inherited.FreshSourceCallReplay,
                   ObservedFormalRoleReplay, EnglishFormalRoleReplay]
        result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(
            unittest.defaultTestLoader.loadTestsFromTestCase(value) for value in classes))
    raise SystemExit(0 if result.wasSuccessful() else 1)
