"""Exact empty annotations never authorize another body, alias, state or glyph."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
import unittest

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import guarded_reviewed_cache_v10 as current
import active_guard_v6_preflight_v1 as guard


class ExactUnicodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        guard.activate();cls.case=current.load_case()
        cls.source=(ROOT/cls.case['original']['path']).read_text(encoding='utf-8')
        cls.body=(ROOT/cls.case['body']['path']).read_text(encoding='utf-8')

    def object(self, ident='expanded_train:12122', state=3, blocked=False):
        return SimpleNamespace(current=(dict(id=ident,
            original_text_sha256=self.case['original']['sha256'],
            restricted_parent_body_not_decoded=blocked),state),
            guard=SimpleNamespace(unicode_empty_annotation_case=self.case))

    def call(self, **kwargs):
        return current.exact_annotation_code_guard(self.object(**kwargs),self.source,self.body)

    def test_actual_pair_old_unicode_negative_new_exact_positive(self):
        self.assertFalse(current.literal_policy.unicode_examples_preserved(self.source,self.body))
        self.assertTrue(current.literal_policy.code_preserved(self.source,self.body))
        self.assertTrue(current.exact_pair_preserved(self.source,self.body,self.case))

    def test_both_actual_parent_aliases_are_exactly_allowed(self):
        with patch.object(current,'BASE_CODE_GUARD',return_value=False):
            for ident in self.case['parent_alias_ids']:self.assertTrue(self.call(ident=ident))

    def test_baseline_or_other_parent_states_are_not_waived(self):
        with patch.object(current,'BASE_CODE_GUARD',return_value=False):
            for state in [1,2,4,5]:self.assertFalse(self.call(state=state))

    def test_other_identity_or_restricted_projection_is_not_waived(self):
        with patch.object(current,'BASE_CODE_GUARD',return_value=False):
            self.assertFalse(self.call(ident='expanded_train:99999'))
            self.assertFalse(self.call(blocked=True))

    def test_codepoint_or_filled_glyph_change_is_rejected(self):
        for value in [self.body.replace('U+302E','U+302F'),self.body+'ᄀ',self.body.replace('ퟅ','가')]:
            self.assertFalse(current.exact_pair_preserved(self.source,value,self.case))

    def test_source_body_or_code_version_difference_is_rejected(self):
        for a,b in [(self.source+' ',self.body),(self.source,self.body+' '),
                    (self.source,self.body+chr(10)+'```python'+chr(10)+'a=1'+chr(10)+'```')]:
            self.assertFalse(current.exact_pair_preserved(a,b,self.case))

    def test_normal_positive_guard_is_delegated(self):
        with patch.object(current,'BASE_CODE_GUARD',return_value=True) as delegated:
            self.assertTrue(self.call(ident='expanded_train:99999',state=1))
            delegated.assert_called_once()

    def test_exact_case_cannot_change_approved_empty_annotation_set(self):
        altered=dict(self.case,permitted_annotation_pairs=[])
        self.assertFalse(current.exact_pair_preserved(self.source,self.body,altered))

    def test_no_protected_source_views_were_opened(self):
        guard.assert_no_protected_opens()


if __name__=='__main__':unittest.main()
