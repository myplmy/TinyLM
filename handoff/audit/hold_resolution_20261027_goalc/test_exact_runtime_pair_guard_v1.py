"""Counterexamples for exact exceptions, baseline priority and context restoration."""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import re
import sys
import unittest

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import exact_runtime_pair_guard_v1 as exact
import guarded_reviewed_cache_v2 as adapter


class ExactPairs(unittest.TestCase):
    def case(self,original,cleaned,units=()):
        ident='expanded_train:689736'
        row=dict(id=ident,root_approved=True,original=dict(sha256=exact.sha(original)),
                 body=dict(sha256=exact.sha(cleaned)),required_nonwhitespace_code_units=list(units))
        return ident,{ident:row}

    def test_exact_known_source_body(self):
        ident,cases=self.case('Original prose.','Reviewed prose.')
        self.assertTrue(exact.exact_pair_preserved('Original prose.','Reviewed prose.',ident,cases))

    def test_unreviewed_source_cannot_borrow_pair(self):
        ident,cases=self.case('Original prose.','Reviewed prose.')
        self.assertFalse(exact.exact_pair_preserved('Another source.','Reviewed prose.',ident,cases))

    def test_new_body_version_cannot_borrow_pair(self):
        ident,cases=self.case('Original prose.','Reviewed prose.')
        self.assertFalse(exact.exact_pair_preserved('Original prose.','Reviewed prose. Added.',ident,cases))

    def test_nonempty_unicode_example_survives_even_with_erroneous_approval(self):
        source='U+0041(A)'
        clean='U+0041'
        ident,cases=self.case(source,clean)
        self.assertFalse(exact.exact_pair_preserved(source,clean,ident,cases))

    def test_empty_glyph_shell_is_not_a_nonempty_example(self):
        source='U+0041()'
        clean='U+0041'
        ident,cases=self.case(source,clean)
        self.assertTrue(exact.exact_pair_preserved(source,clean,ident,cases))

    def test_complete_source_code_unit_cannot_disappear(self):
        source='Description. print(1)'
        clean='Description.'
        ident,cases=self.case(source,clean,['print(1)'])
        self.assertFalse(exact.exact_pair_preserved(source,clean,ident,cases))

    def test_complete_source_code_unit_count_cannot_change(self):
        source='print(1)'
        clean='print(1) print(1)'
        ident,cases=self.case(source,clean,['print(1)'])
        self.assertFalse(exact.exact_pair_preserved(source,clean,ident,cases))

    def instance(self,state):
        instance=adapter.GuardedResolutionEngine.__new__(adapter.GuardedResolutionEngine)
        instance.current=(dict(id='expanded_train:17',text=''),state)
        instance.exact_cases={}
        return instance

    def test_typed_alias_only_preserves_other_calls(self):
        source='자리올림 가산기()는 가산기이다.\n\n```python\nfoo()\n```\n'
        clean=source.replace('()','',1)
        with patch.object(adapter.previous.GuardedResolutionEngine,'code_guard',return_value=False):
            self.assertTrue(self.instance(3).code_guard(source,clean))
            self.assertFalse(self.instance(3).code_guard(source,clean.replace('foo()','foo')))

    def test_typed_alias_cannot_change_existing_baseline(self):
        source='자리올림 가산기()는 가산기이다.'
        with patch.object(adapter.previous.GuardedResolutionEngine,'code_guard',return_value=False):
            self.assertFalse(self.instance(1).code_guard(source,source.replace('()','')))

    def test_verify_context_uses_original_context_once_and_restores_state(self):
        entered=[]

        @contextmanager
        def original_context(selection):
            entered.append(selection)
            yield object()

        def old_verify(base,roster,output,selection):
            with adapter.previous.runtime(selection):
                return 'UNIT_FIXTURE_ONLY'

        old_runtime=adapter.previous.runtime
        with patch.object(adapter,'ORIGINAL_RUNTIME',original_context), \
                patch.object(adapter.exact,'load_registry',return_value={}), \
                patch.object(adapter.previous,'verify',old_verify):
            self.assertEqual(adapter.verify(None,None,None,'fixture'), 'UNIT_FIXTURE_ONLY')
        self.assertEqual(entered,['fixture'])
        self.assertIsNone(adapter.CASES)
        self.assertIs(adapter.previous.runtime,old_runtime)


if __name__=='__main__':
    unittest.main()
