"""CPU metadata and context tests; does not build or consume a token cache."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guarded_reviewed_cache_v8 as current


class Guard5RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.contract = current.checked_contract()
        self.original_contract = current.guard4_runtime.CONTRACT
        self.original_expected = current.guard4_runtime.EXPECTED
        self.prior = {'rows': [dict(id=key, original_text_sha256=str(index) * 64,
            selected=dict(decision='EDIT', body='approved-safe-body-' + str(index),
                          clean_text_sha256=str(index + 1) * 64))
            for index, key in enumerate(sorted(current.SAFE_IDS), 1)]}
        self.selection = deepcopy(self.prior)
        self.opaque = {'trusted_hold_metadata': {
            key: deepcopy(self.contract['trusted_metadata'][key])
            for item in self.contract['newly_quarantined_entries']
            for key in item['parent_alias_ids']}}

    def test_actual_contract_counts_and_restoration(self):
        with current.active_contract() as contract:
            self.assertEqual(len(contract['restricted_ids']), 11)
            self.assertEqual(len(contract['restricted_hashes']), 14)
            self.assertEqual(len(contract['trusted_metadata']), 19)
            self.assertEqual(current.guard4_runtime.EXPECTED, current.EXPECTED)
            self.assertEqual(current.guard4_runtime.checked_contract(), contract)
        self.assertEqual(current.guard4_runtime.CONTRACT, self.original_contract)
        self.assertEqual(current.guard4_runtime.EXPECTED, self.original_expected)
        self.assertIsNone(current.ACTIVE_CONTRACT)

    def test_nested_context_does_not_call_old_guard4_again(self):
        original = current.guard5.checked_contract
        with patch.object(current.guard5, 'checked_contract', wraps=original) as spy:
            with current.active_contract() as outer:
                with current.active_contract() as inner:
                    self.assertIs(inner, outer)
                    self.assertIs(current.checked_contract(), outer)
                self.assertEqual(current.guard4_runtime.EXPECTED, current.EXPECTED)
            self.assertEqual(spy.call_count, 1)

    def test_exception_restores_all_guard_globals(self):
        with self.assertRaisesRegex(RuntimeError, 'test exception'):
            with current.active_contract():
                raise RuntimeError('test exception')
        self.assertEqual(current.guard4_runtime.CONTRACT, self.original_contract)
        self.assertEqual(current.guard4_runtime.EXPECTED, self.original_expected)
        self.assertIsNone(current.ACTIVE_CONTRACT)
        self.assertEqual(current.checked_contract(), self.contract)

    def test_verify_keeps_guard5_during_entire_delegated_call(self):
        def delegated(*args):
            self.assertEqual(current.guard4_runtime.EXPECTED, current.EXPECTED)
            self.assertIs(current.previous.runtime, current.runtime)
            with current.active_contract():
                self.assertEqual(current.guard4_runtime.EXPECTED, current.EXPECTED)
            # This simulates verify's post-runtime proof section, not a cache run.
            self.assertEqual(current.guard4_runtime.EXPECTED, current.EXPECTED)
            return {'metadata_test': True}
        with patch.object(current.previous, 'verify', delegated):
            self.assertEqual(current.verify(*([None] * 6)), {'metadata_test': True})
        self.assertEqual(current.guard4_runtime.EXPECTED, self.original_expected)

    def test_current_pins_wrapper_keeps_guard5(self):
        def delegated(*args):
            self.assertEqual(current.guard4_runtime.EXPECTED, current.EXPECTED)
            self.assertIs(current.previous.runtime, current.runtime)
            return {'metadata_test': 'pins'}
        with patch.object(current.previous, 'current_pins', delegated):
            self.assertEqual(current.current_pins(None, None, None), {'metadata_test': 'pins'})
        self.assertEqual(current.guard4_runtime.EXPECTED, self.original_expected)

    def test_unchanged_three_safe_rows_accepted(self):
        current.validate_selection(self.selection, self.prior, self.contract)

    def test_changed_safe_body_rejected(self):
        self.selection['rows'][0]['selected']['body'] += '-changed'
        with self.assertRaisesRegex(Exception, 'safe derivative selection changed'):
            current.validate_selection(self.selection, self.prior, self.contract)

    def test_missing_safe_row_rejected(self):
        self.selection['rows'].pop()
        with self.assertRaisesRegex(Exception, 'three prior safe selections'):
            current.validate_selection(self.selection, self.prior, self.contract)

    def test_new_quarantined_body_rejected(self):
        self.selection['rows'].append(dict(id='expanded_train:32895',
            original_text_sha256=self.contract['newly_quarantined_entries'][0]['original']['sha256'],
            selected=dict(decision='EDIT', body='must-never-open', clean_text_sha256='A' * 64)))
        with self.assertRaisesRegex(Exception, 'cannot enter accepted selection'):
            current.validate_selection(self.selection, self.prior, self.contract)

    def test_new_candidate_hash_under_different_id_rejected(self):
        self.selection['rows'].append(dict(id='expanded_train:999999999',
            original_text_sha256='A' * 64, selected=dict(decision='EDIT', body='never-open',
            clean_text_sha256=self.contract['newly_quarantined_entries'][0]['derived_candidate']['sha256'])))
        with self.assertRaisesRegex(Exception, 'cannot enter accepted selection'):
            current.validate_selection(self.selection, self.prior, self.contract)

    def test_new_body_free_hold_does_not_become_admission(self):
        self.selection['rows'].append(dict(id='expanded_train:32895',
            original_text_sha256=self.contract['newly_quarantined_entries'][0]['original']['sha256'],
            selected=dict(decision='HOLD', body=None, clean_text_sha256=None)))
        current.validate_selection(self.selection, self.prior, self.contract)

    def test_all_four_new_aliases_are_exact_metadata_hold(self):
        self.assertEqual(len(current.validate_new_aliases(self.opaque, self.contract)), 4)

    def test_missing_opaque_alias_rejected(self):
        self.opaque['trusted_hold_metadata'].pop('historical_train:32895')
        with self.assertRaisesRegex(Exception, 'missing from opaque HOLD'):
            current.validate_new_aliases(self.opaque, self.contract)

    def test_changed_source_interval_rejected(self):
        self.opaque['trusted_hold_metadata']['expanded_train:74587']['source_ids'][1] += 1
        with self.assertRaisesRegex(Exception, 'alias metadata differs'):
            current.validate_new_aliases(self.opaque, self.contract)

    def test_changed_parent_decision_rejected(self):
        self.opaque['trusted_hold_metadata']['expanded_train:32895']['parent_decision'] = 'KEEP'
        with self.assertRaisesRegex(Exception, 'alias metadata differs'):
            current.validate_new_aliases(self.opaque, self.contract)

    def test_actual_root32_shards_and_prior_safe_identity_metadata_only(self):
        path = current.AUDIT/'ROOT_AUTHORED_SELECTIONS_V32.json'
        result = current.selection_binding(path, self.contract)
        self.assertEqual(result, [(path, '67A77EA21E4F98FE5FF5F27D906B0C8E08C0B702C2B852750A9C0825281DA5A8')])


if __name__ == '__main__':
    unittest.main(verbosity=2)
