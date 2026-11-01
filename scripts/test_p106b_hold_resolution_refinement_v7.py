#!/usr/bin/env python3
"""An old terminal formula must be freshly checked against its source hole."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_refinement_v7 as refinement
from scripts import test_p106b_hold_resolution_refinement_v6 as inherited


class FormulaHoleReplay(unittest.TestCase):
    def test_old_component_hole_requires_actual_fresh_policy(self):
        raw = "그 성분 는 다음과 같다.\n.\n여기서\n 는 스칼라이다.\n"
        result, selector, calls, frozen, row = inherited.LocalLiteralReplay.make(self, raw)
        self.assertEqual(result["decision"], "PENDING")
        self.assertEqual(calls, [row["id"]])
        self.assertIs(selector.records[row["original_text_sha256"]], frozen)

    def test_actual_formula_can_still_reuse_the_literal(self):
        raw = "그 성분은 다음과 같다.\nT = x + y.\n여기서\nx는 스칼라이다.\n"
        result, _, calls, _, _ = inherited.LocalLiteralReplay.make(self, raw)
        self.assertEqual(result["decision"], "EDIT")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    v6, v5 = inherited, inherited.inherited
    v4, v3 = v5.inherited, v5.inherited.inherited
    v2, v1 = v3.inherited, v3.inherited.inherited
    r6 = refinement.previous
    r5, r4 = r6.previous, r6.previous.previous
    with patch.object(r6, "policy", refinement.policy), patch.object(r5, "policy", refinement.policy), \
            patch.object(r4, "policy", refinement.policy), patch.object(v3, "refinement", r4), \
            patch.object(v2, "refinement", r4), patch.object(v1, "refinement", r4):
        classes = [v1.FrozenDraftTests, v2.OriginalBoundaryCases, v3.RecheckChangedPreservation,
                   v4.RecheckLiteralHoles, v5.NewContextHoleReplay, v6.LocalLiteralReplay, FormulaHoleReplay]
        suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(value) for value in classes])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
