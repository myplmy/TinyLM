#!/usr/bin/env python3
"""Original interval boundaries and inherited-HOLD assertions remain distinct."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_refinement_v2 as refinement
from scripts import test_p106b_hold_resolution_refinement as inherited


class OriginalBoundaryCases(unittest.TestCase):
    def make(self, ident, complete=False, reason=None):
        row = inherited.source("原文 fragment")
        row.update(id=ident, source=ident.split(":", 1)[0], complete_eos=complete)
        frozen = {key: value for key, value in row.items() if key != "text"}
        reasons = [reason or refinement.BOUNDARY_REASON]
        frozen.update(decision="EXCLUDE", reasons=reasons, changes=[], clean_text_sha256=None)
        def propose(fresh, individual=False):
            return dict(decision="EXCLUDE", text=fresh["text"], reasons=reasons, changes=[])
        policy = SimpleNamespace(RULES="BOUNDARY_TEST", propose=propose)
        return row, refinement.FrozenDraftSelector([frozen], policy)

    def test_all_three_actual_boundary_ids_can_remain_excluded_under_inherited_hold(self):
        for ident in refinement.BOUNDARIES:
            with self.subTest(ident=ident):
                row, selector = self.make(ident, complete=ident == "validation:0")
                self.assertEqual(selector.propose(row, True)["decision"], "EXCLUDE")
                self.assertIsNone(selector.last["candidate"])

    def test_another_source_cannot_borrow_a_boundary_exclusion(self):
        row, selector = self.make("expanded_train:1")
        with self.assertRaisesRegex(ValueError, "three evidenced"):
            selector.propose(row, True)

    def test_a_complete_last_boundary_source_is_rejected(self):
        row, selector = self.make("historical_train:709976", complete=True)
        with self.assertRaisesRegex(ValueError, "three evidenced"):
            selector.propose(row, True)

    def test_a_different_exclusion_reason_is_not_reused(self):
        row, selector = self.make("validation:0", complete=True, reason="different-reason")
        with self.assertRaisesRegex(ValueError, "three evidenced"):
            selector.propose(row, True)

    def test_source_interval_checks_precede_boundary_reuse(self):
        row, selector = self.make("validation:0", complete=True)
        row["source_ids"] = [1, 18]
        with self.assertRaisesRegex(ValueError, "identity/interval"):
            selector.propose(row, True)


if __name__ == "__main__":
    with patch.object(inherited, "refinement", refinement):
        suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(inherited.FrozenDraftTests),
                                   unittest.defaultTestLoader.loadTestsFromTestCase(OriginalBoundaryCases)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
