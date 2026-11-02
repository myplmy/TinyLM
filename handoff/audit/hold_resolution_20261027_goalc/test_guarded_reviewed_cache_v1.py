"""Counterexamples for opaque source handling and exact safe-view admission."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
import unittest

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
import guarded_reviewed_cache_v1 as adapter


class RestrictedAdmission(unittest.TestCase):
    def setUp(self):
        self.raw_sha = 'A'*64
        self.body = 'A complete independent safe-view sentence.'
        self.row = dict(id='expanded_train:1250821', text='', original_text_sha256=self.raw_sha,
                        restricted_parent_body_not_decoded=True)
        self.safe = {self.raw_sha:dict(clean_text_sha256=adapter.inv.sha(self.body))}

    def test_exact_safe_edit(self):
        adapter.validate_outcome(self.row, 'EDIT', self.body, self.safe)

    def test_same_sha_other_position(self):
        adapter.validate_outcome(dict(self.row,id='historical_train:71'), 'EDIT', self.body, self.safe)

    def test_keep_is_forbidden_even_if_body_matches(self):
        with self.assertRaisesRegex(ValueError, 'KEEP/source slice'):
            adapter.validate_outcome(self.row, 'KEEP', self.body, self.safe)

    def test_unknown_safe_source_is_forbidden(self):
        with self.assertRaisesRegex(ValueError, 'exact approved'):
            adapter.validate_outcome(dict(self.row,original_text_sha256='B'*64), 'EDIT', self.body, self.safe)

    def test_changed_body_is_forbidden(self):
        with self.assertRaisesRegex(ValueError, 'exact approved'):
            adapter.validate_outcome(self.row, 'EDIT', self.body + ' Added.', self.safe)

    def test_empty_safe_body_is_forbidden(self):
        with self.assertRaisesRegex(ValueError, 'exact approved'):
            adapter.validate_outcome(self.row, 'EDIT', '', self.safe)

    def test_unprojected_full_original_is_forbidden(self):
        with self.assertRaisesRegex(ValueError, 'absent-body'):
            adapter.validate_outcome(dict(self.row,text='Never inspect this body'), 'EXCLUDE', '', self.safe)

    def test_explicit_absent_body_flag_required(self):
        with self.assertRaisesRegex(ValueError, 'absent-body'):
            adapter.validate_outcome(dict(self.row,restricted_parent_body_not_decoded=False), 'EDIT', self.body, self.safe)

    def test_hold_stays_unadmitted(self):
        adapter.validate_outcome(self.row, 'HOLD', '', {})

    def test_exclusion_needs_no_safe_body(self):
        adapter.validate_outcome(self.row, 'EXCLUDE', '', {})

    def engine(self, proposal, state=3):
        instance = adapter.GuardedResolutionEngine.__new__(adapter.GuardedResolutionEngine)
        instance.index = SimpleNamespace(state=lambda row:state)
        instance.guard = SimpleNamespace(safe=self.safe,
            safe_texts={self.raw_sha:(self.body,self.body)}, metadata={self.row['id']:self.row},
            contract_sha='C'*64)
        instance.roster = {self.raw_sha:proposal}
        return instance

    def test_keep_rejected_before_old_engine_can_reconstruct(self):
        instance = self.engine(dict(decision='KEEP'))
        with patch.object(adapter.reviewed.ReviewedResolutionEngine, 'pick') as old:
            with self.assertRaisesRegex(ValueError, 'KEEP/source slice'):
                instance.pick(self.row,{})
            old.assert_not_called()

    def test_admitted_baseline_cannot_be_replaced(self):
        instance = self.engine(dict(decision='EDIT',text=self.body), state=1)
        with patch.object(adapter.reviewed.ReviewedResolutionEngine, 'pick') as old:
            with self.assertRaisesRegex(ValueError, 'admitted baseline'):
                instance.pick(self.row,{})
            old.assert_not_called()

    def test_exact_edit_can_be_deduplicated_without_source_read(self):
        instance = self.engine(dict(decision='EDIT',text=self.body))
        expected = ('EXCLUDE', self.body, ['EXACT_DUPLICATE'], None)
        with patch.object(adapter.reviewed.ReviewedResolutionEngine, 'pick', return_value=expected):
            self.assertEqual(instance.pick(self.row,{}), expected)

    def test_old_engine_returning_keep_is_rejected(self):
        instance = self.engine(dict(decision='EDIT',text=self.body))
        with patch.object(adapter.reviewed.ReviewedResolutionEngine, 'pick', return_value=('KEEP',self.body,[],None)):
            with self.assertRaisesRegex(ValueError, 'KEEP/source slice'):
                instance.pick(self.row,{})

    def test_safe_view_code_guard_has_no_whole_parent_fallback(self):
        instance = self.engine(dict(decision='EDIT',text=self.body))
        instance.current = (self.row,3)
        with patch.object(adapter.reviewed.ReviewedResolutionEngine, 'code_guard', side_effect=AssertionError('parent fallback')):
            self.assertTrue(instance.code_guard('',self.body))

    def test_safe_view_changed_code_is_rejected(self):
        original = '```python\nprint(1)\n```\n'
        clean = '```python\nprint(2)\n```\n'
        instance = self.engine(dict(decision='EDIT',text=clean))
        instance.guard.safe = {self.raw_sha:dict(clean_text_sha256=adapter.inv.sha(clean))}
        instance.guard.safe_texts = {self.raw_sha:(original,clean)}
        instance.current = (self.row,3)
        self.assertFalse(instance.code_guard('',clean))

    def test_source_slice_annotation_rejected(self):
        instance = self.engine(dict(decision='EDIT',text=self.body))
        event = dict(self.row,decision='EDIT',clean_text_sha256=adapter.inv.sha(self.body),
                     serialization_mode='SOURCE_SLICE')
        with patch.object(adapter.reviewed.ReviewedResolutionEngine, 'annotate', return_value=dict(event)):
            with self.assertRaisesRegex(ValueError, 'source slice'):
                instance.annotate(event)


if __name__ == '__main__':
    unittest.main()
