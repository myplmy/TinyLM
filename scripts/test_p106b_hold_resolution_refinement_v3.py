#!/usr/bin/env python3
"""Changed preservation gates must reprocess affected frozen terminal drafts."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_refinement_v3 as refinement
from scripts import test_p106b_hold_resolution_refinement_v2 as inherited


class RecheckChangedPreservation(unittest.TestCase):
    def make(self, raw, clean, changes=None, raises=False):
        source = inherited.inherited.source(raw)
        frozen = {key: value for key, value in source.items() if key != 'text'}
        frozen.update(decision='EDIT', text=clean, clean_text_sha256=refinement.inv.sha(clean),
                      reasons=['frozen-proposal'], changes=changes or [])
        calls = []
        def propose(row, individual=False):
            calls.append(row['id'])
            if raises:
                raise ValueError('fresh-policy-error')
            return dict(decision='PENDING', text=row['text'], reasons=['not-admitted'], changes=[])
        selector = refinement.FrozenDraftSelector([frozen], SimpleNamespace(RULES='FRESH', propose=propose))
        return source, selector, calls, frozen

    def test_an_old_partial_quarantine_is_evaluated_with_the_new_gate(self):
        changes = [dict(reason=refinement.QUARANTINE, original='source paragraph')]
        row, selector, calls, frozen = self.make('완결 설명. 별도 문장.', '완결 설명.', changes)
        self.assertEqual(selector.propose(row)['decision'], 'PENDING')
        self.assertEqual(calls, [row['id']])
        self.assertIs(selector.records[row['original_text_sha256']], frozen)
        self.assertFalse(selector.last['reused'])

    def test_an_old_plain_bullet_cannot_borrow_a_frozen_terminal_pass(self):
        raw = '<span style="color:green;">●</span> 5번\n'
        row, selector, calls, _ = self.make(raw, '● 5번\n')
        self.assertEqual(selector.propose(row)['decision'], 'PENDING')
        self.assertEqual(calls, [row['id']])
        self.assertTrue(selector.last['rechecked_frozen_terminal']['style_loss'])

    def test_an_unaffected_terminal_body_still_avoids_reprocessing(self):
        row, selector, calls, _ = self.make('완결 설명. 빈 각주', '완결 설명.')
        self.assertEqual(selector.propose(row)['decision'], 'EDIT')
        self.assertEqual(calls, [])
        self.assertTrue(selector.last['integrity']['semantic_style_guard'])

    def test_original_record_is_restored_when_the_new_policy_fails(self):
        changes = [dict(reason=refinement.QUARANTINE, original='source paragraph')]
        row, selector, _, frozen = self.make('완결 설명. 별도 문장.', '완결 설명.', changes, raises=True)
        with self.assertRaisesRegex(ValueError, 'fresh-policy-error'):
            selector.propose(row)
        self.assertIs(selector.records[row['original_text_sha256']], frozen)
        self.assertEqual(frozen['decision'], 'EDIT')


if __name__ == '__main__':
    with patch.object(inherited, 'refinement', refinement), patch.object(inherited.inherited, 'refinement', refinement):
        suite = unittest.TestSuite([
            unittest.defaultTestLoader.loadTestsFromTestCase(inherited.inherited.FrozenDraftTests),
            unittest.defaultTestLoader.loadTestsFromTestCase(inherited.OriginalBoundaryCases),
            unittest.defaultTestLoader.loadTestsFromTestCase(RecheckChangedPreservation)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
