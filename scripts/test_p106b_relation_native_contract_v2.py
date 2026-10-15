#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from scripts import diag_p106b_relation_interleaved_runtime_v2 as r


class NativeContract(unittest.TestCase):
    def test_actual_missing_marker_reproduced_and_real_reader_fixed(self):
        result=r.verify_native();self.assertTrue(result['original_missing_marker_reproduced']);self.assertTrue(result['real_reader_verified'])
        self.assertEqual(result['windows_compared'],16);self.assertEqual(result['full_schedule_windows'],5504)
        self.assertTrue(result['cache_read_only']);self.assertEqual(result['cache_copies'],0)

    def test_contract_repair_is_copy_not_data_mutation(self):
        original,source,fixed=r.metadata_contract();old=copy.deepcopy(original)
        self.assertNotIn('native_access',original);self.assertEqual(fixed['native_access'],'INDEXED_TRAIN_ONLY')
        self.assertEqual(r.repaired_contract(original,source),fixed);self.assertEqual(original,old)

    def test_changed_source_offsets_fail_closed(self):
        original,source,_=r.metadata_contract();source['native_train_offsets']=source['native_train_offsets'][1:]
        with self.assertRaisesRegex(ValueError,'unchanged'):r.repaired_contract(original,source)

    def test_legacy_or_unknown_modes_cannot_be_guessed(self):
        original,source,_=r.metadata_contract();source['native_access']='UNKNOWN'
        with self.assertRaisesRegex(ValueError,'exact original'):r.repaired_contract(original,source)

    def test_new_runtime_paths_same_immutable_data(self):
        self.assertEqual(r.CORPUS,r.data.CORPUS);self.assertNotEqual(r.EVIDENCE,r.data.EVIDENCE)
        self.assertEqual(r.PARENT_SHA,r.data.PARENT_SHA);self.assertEqual(r.training.data.digest(r.CORPUS/'report.json'),r.DATA_SHA)


if __name__=='__main__':unittest.main()
