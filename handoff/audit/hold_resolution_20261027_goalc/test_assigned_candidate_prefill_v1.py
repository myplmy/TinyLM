"""A prefill can never overwrite an output or copy an unassigned source."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock
import sys
import unittest

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import assigned_candidate_prefill_v1 as current
import lossless_review_packet_v3 as actual


class CandidatePrefillTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.role='legacy_review';self.cohort='remaining_field_title_page_016_counter_v1'
        self.folder=self.root/actual.base.DATA_ROOT/'agents'/self.role/self.cohort;self.folder.mkdir(parents=True)
        self.raw='후보 원형 바이트'.encode('utf-8')
        self.context=dict(source_id='expanded_train:12',role=self.role,cohort=self.cohort,
            original=dict(path='never_open_original',sha256='A'*64),
            candidate=dict(path='assigned_candidate',sha256=actual.base.digest(self.raw)))
        self.core=SimpleNamespace(resolve_assignment=lambda *args:self.context,base=actual.base,require=actual.require)
        self.contract=dict(restricted_ids=[],restricted_hashes=['F'*64],trusted_metadata={})

    def call(self,read,name='expanded_train_12_final_v1.txt'):
        return current.prefill(self.root,self.role,self.cohort,[('expanded_train:12',name)],
            self.core,{},None,self.contract,read)

    def test_exact_candidate_becomes_one_final_output(self):
        read=Mock(return_value=self.raw);result=self.call(read)
        self.assertEqual((self.folder/'expanded_train_12_final_v1.txt').read_bytes(),self.raw)
        self.assertEqual(result[0]['final']['sha256'],actual.base.digest(self.raw))
        self.assertEqual(read.call_args.args[1],self.context['candidate'])
        self.assertEqual(len(list(self.folder.iterdir())),1)

    def test_existing_file_is_not_opened_or_overwritten(self):
        target=self.folder/'expanded_train_12_final_v1.txt';target.write_bytes(b'keep')
        read=Mock()
        with self.assertRaises(ValueError):self.call(read)
        read.assert_not_called();self.assertEqual(target.read_bytes(),b'keep')

    def test_changed_candidate_creates_no_output(self):
        with self.assertRaises(ValueError):self.call(Mock(return_value=b'changed'))
        self.assertEqual(list(self.folder.iterdir()),[])

    def test_restricted_source_and_foreign_target_denied_before_payload(self):
        read=Mock();self.context['original']['sha256']='F'*64
        with self.assertRaises(ValueError):self.call(read)
        read.assert_not_called();self.context['original']['sha256']='A'*64
        with self.assertRaises(ValueError):self.call(read,'expanded_train_13_final.txt')
        read.assert_not_called()


if __name__=='__main__':unittest.main()
