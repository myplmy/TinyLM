"""Synthetic regression tests; no corpus bodies or training TXT are created."""
from pathlib import Path
from types import SimpleNamespace
import json
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guarded_scan_metadata_v1 import IDENTITY_FIELDS
from opaque_hold_metadata_v1 import guarded_or_opaque_row, validate_hold_outcome
import guarded_reviewed_cache_v6 as adapter


class OpaqueHoldTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(id='expanded_train:7', ordinal=7, source='expanded_train', split='train',
            source_ids=[10, 20], source_ids_sha256='B'*64, original_text_sha256='A'*64,
            input_ids=10, complete_eos=True, valid_utf8=True,
            original_signals={}, language_proxy={}, text='ORIGINAL_BODY')
        self.trusted = {key: self.row[key] for key in IDENTITY_FIELDS}
        self.trusted['parent_decision'] = 'HOLD'
        self.options = dict(restricted_ids=set(), restricted_hashes=set(), restricted_metadata={},
            hold_metadata={self.row['id']: self.trusted}, hold_hashes={'A'*64})

    def encoded(self, **changes):
        return json.dumps(dict(self.row, **changes)).encode()

    def test_ordinary_hold_is_not_labeled_restricted(self):
        row = guarded_or_opaque_row(self.encoded(), **self.options)
        self.assertEqual(row['text'], '')
        self.assertTrue(row['unadopted_hold_body_not_decoded'])
        self.assertNotIn('restricted_parent_body_not_decoded', row)

    def test_invalid_utf8_inside_opaque_body_is_never_decoded(self):
        raw = self.encoded().replace(b'ORIGINAL_BODY', b'\xff')
        self.assertEqual(guarded_or_opaque_row(raw, **self.options)['text'], '')

    def test_restricted_hold_keeps_both_annotations(self):
        options = dict(self.options, restricted_ids={self.row['id']},
            restricted_hashes={'A'*64}, restricted_metadata={self.row['id']: self.trusted})
        row = guarded_or_opaque_row(self.encoded(), **options)
        self.assertTrue(row['restricted_parent_body_not_decoded'])
        self.assertTrue(row['unadopted_hold_body_not_decoded'])

    def test_restricted_identity_conflict_fails(self):
        other = dict(self.trusted, input_ids=11)
        options = dict(self.options, restricted_ids={self.row['id']},
            restricted_metadata={self.row['id']: other})
        with self.assertRaises(ValueError): guarded_or_opaque_row(self.encoded(), **options)

    def test_unknown_hash_alias_fails(self):
        with self.assertRaises(ValueError):
            guarded_or_opaque_row(self.encoded(id='historical_train:9', ordinal=9), **self.options)

    def test_source_hash_change_fails(self):
        with self.assertRaises(ValueError):
            guarded_or_opaque_row(self.encoded(original_text_sha256='C'*64), **self.options)

    def test_interval_change_fails(self):
        with self.assertRaises(ValueError):
            guarded_or_opaque_row(self.encoded(source_ids=[11, 21]), **self.options)

    def test_parent_decision_change_fails(self):
        options = dict(self.options, hold_metadata={self.row['id']: dict(self.trusted, parent_decision='EDIT')})
        with self.assertRaises(ValueError): guarded_or_opaque_row(self.encoded(), **options)

    def test_accepted_ordinary_source_uses_existing_decode(self):
        row = guarded_or_opaque_row(self.encoded(), **dict(self.options, hold_metadata={}, hold_hashes=set()))
        self.assertEqual(row, self.row)
        raw = self.encoded().replace(b'ORIGINAL_BODY', b'\xff')
        with self.assertRaises(UnicodeDecodeError):
            guarded_or_opaque_row(raw, **dict(self.options, hold_metadata={}, hold_hashes=set()))

    def test_restricted_nonhold_path_uses_existing_guard(self):
        options = dict(self.options, hold_metadata={}, hold_hashes=set(),
            restricted_ids={self.row['id']}, restricted_hashes={'A'*64},
            restricted_metadata={self.row['id']: self.trusted})
        row = guarded_or_opaque_row(self.encoded(), **options)
        self.assertTrue(row['restricted_parent_body_not_decoded'])
        self.assertNotIn('unadopted_hold_body_not_decoded', row)

    def test_missing_numeric_metadata_fails_before_output(self):
        with self.assertRaises(ValueError):
            guarded_or_opaque_row(self.encoded(original_signals={'bad': 'not numeric'}), **self.options)

    def test_projection_never_becomes_adoption(self):
        row = guarded_or_opaque_row(self.encoded(), **self.options)
        validate_hold_outcome(row, 3, {'decision': 'HOLD'}, ('HOLD', '', [], None))
        for state, proposal, value in [(1, {'decision': 'HOLD'}, None),
            (3, {'decision': 'KEEP'}, None), (3, {'decision': 'EDIT', 'text': 'x'}, None),
            (3, {'decision': 'HOLD', 'clean_text_sha256': 'A'*64}, None),
            (3, {'decision': 'HOLD'}, ('EXCLUDE', '', [], None)),
            (3, {'decision': 'HOLD'}, ('HOLD', 'leaked', [], None))]:
            with self.subTest(state=state, proposal=proposal, value=value):
                with self.assertRaises(ValueError): validate_hold_outcome(row, state, proposal, value)

    def test_engine_checks_actual_pick_return(self):
        obj = object.__new__(adapter.GuardedResolutionEngine)
        obj.index = SimpleNamespace(state=lambda row: 3)
        obj.roster = {'A'*64: {'decision': 'HOLD'}}
        row = guarded_or_opaque_row(self.encoded(), **self.options)
        with patch.object(adapter.BASE_ENGINE, 'pick', return_value=('HOLD', '', [], None)):
            self.assertEqual(obj.pick(row, {})[0], 'HOLD')
        with patch.object(adapter.BASE_ENGINE, 'pick', return_value=('EDIT', 'bad', [], None)):
            with self.assertRaises(ValueError): obj.pick(row, {})

    def test_engine_refuses_adoption_guard_for_opaque_row(self):
        obj = object.__new__(adapter.GuardedResolutionEngine)
        obj.current = (guarded_or_opaque_row(self.encoded(), **self.options), 3)
        with self.assertRaises(ValueError): obj.code_guard('', 'new')

    def test_engine_annotates_only_exact_hold(self):
        obj = object.__new__(adapter.GuardedResolutionEngine)
        obj.guard = SimpleNamespace(hold_metadata={self.row['id']: self.trusted}, opaque_sha='F'*64)
        event = dict(id=self.row['id'], decision='HOLD', clean_text_sha256=None)
        with patch.object(adapter.BASE_ENGINE, 'annotate', side_effect=lambda row, ledger=False: dict(row)):
            result = obj.annotate(event, ledger=True)
            self.assertEqual(result['opaque_hold_metadata_contract_sha256'], 'F'*64)
            self.assertNotIn('restricted_parent_body_not_decoded', result)
            for change in [dict(decision='KEEP'), dict(cache={'shard': 'x'}), dict(clean_text_sha256='A'*64)]:
                with self.assertRaises(ValueError): obj.annotate(dict(event, **change))

    def test_guard4_is_current_and_new_aliases_are_exact(self):
        contract = adapter.checked_contract()
        self.assertEqual(len(contract['restricted_ids']), 9)
        self.assertEqual(contract['new_restricted_entry']['parent_alias_ids'],
                         ['expanded_train:267902', 'historical_train:267904'])


if __name__ == '__main__': unittest.main(verbosity=2)
