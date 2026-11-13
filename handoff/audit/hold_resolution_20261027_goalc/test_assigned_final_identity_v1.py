"""Own output identity metadata must not broaden the author source scope."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sys
import unittest

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import assigned_final_identity_v1 as current
import lossless_review_packet_v3 as actual


class OwnFinalIdentityTests(unittest.TestCase):
    def setUp(self):
        self.context=dict(source_id='expanded_train:12',role='legacy_review',
            cohort='remaining_field_title_page_016_counter_v1',original=dict(path='never_original',sha256='A'*64),
            candidate=dict(path='never_candidate',sha256='B'*64))
        self.core=SimpleNamespace(resolve_assignment=lambda *args:self.context,base=actual.base,require=actual.require)
        self.contract=dict(restricted_ids=[],restricted_hashes=['F'*64],trusted_metadata={})

    def call(self,pairs,read):
        return current.collect(AUDIT.parents[2],'legacy_review',self.context['cohort'],pairs,
            self.core,{},None,self.contract,read)

    def test_valid_output_opens_only_exact_own_generated_path(self):
        read=Mock(return_value='최종본문'.encode('utf-8'))
        result=self.call([('expanded_train:12','expanded_train_12_final_v1.txt')],read)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['final']['sha256'],actual.base.digest('최종본문'.encode('utf-8')))
        pin=read.call_args.args[1]
        self.assertIn('/agents/legacy_review/'+self.context['cohort']+'/',pin['path'])
        self.assertNotIn(pin['path'],['never_original','never_candidate'])

    def test_unsafe_basename_or_duplicate_denied_before_any_output_read(self):
        for pairs in [[('expanded_train:12','../foreign.txt')],
                      [('expanded_train:12','expanded_train_13_final.txt')],
                      [('expanded_train:12','expanded_train_12_v1.txt')]*2]:
            read=Mock()
            with self.assertRaises(ValueError):self.call(pairs,read)
            read.assert_not_called()

    def test_restricted_original_or_candidate_denied_before_output_read(self):
        for field in ['original','candidate']:
            saved=self.context[field]['sha256'];self.context[field]['sha256']='F'*64;read=Mock()
            with self.assertRaises(ValueError):self.call([('expanded_train:12','expanded_train_12_v1.txt')],read)
            read.assert_not_called();self.context[field]['sha256']=saved

    def test_every_assignment_is_checked_before_first_generated_output_read(self):
        calls=[]
        def resolve(*args):
            calls.append('metadata')
            if len(calls)==2:raise ValueError('second source belongs to another role')
            return self.context
        self.core.resolve_assignment=resolve;read=Mock()
        with self.assertRaises(ValueError):self.call([('expanded_train:12','expanded_train_12_v1.txt'),
            ('expanded_train:13','expanded_train_13_v1.txt')],read)
        read.assert_not_called()


if __name__=='__main__':unittest.main()
