from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import diag_p106b_night_question_bundles_v3 as d
from scripts.test_p106b_night_question_bundles import distinct


class CensusLifecycleTests(unittest.TestCase):
    def test_metadata_policy_and_actual_storage_do_not_overlap(self):
        with patch.object(d.qa.data,'digest',return_value='A'*64):metadata=d.info()
        self.assertIn('storage_policy',metadata)
        self.assertNotIn('storage',metadata)
        self.assertFalse(set(metadata)&{'status','cuda_initialized','censuses','storage','review_bundle_ids','review_selection'})

    def test_synthetic_prepare_then_read_inputs_roundtrip(self):
        train=distinct(suffix='_train');test=distinct(suffix='_test')
        with tempfile.TemporaryDirectory(prefix='p106b_bundle_lifecycle_') as folder:
            root=Path(folder)
            with patch.object(d,'FROZEN',root/'source'),patch.object(d,'EVIDENCE',root/'evidence'),\
                    patch.object(d.old,'sources',return_value=(train,test)),\
                    patch.object(d.qa.data,'digest',return_value='A'*64):
                self.assertEqual(d.prepare(),0)
                frozen,actual,census=d.read_inputs()
                self.assertEqual(actual,test)
                self.assertEqual(census,d.method.census(test))
                self.assertIsInstance(frozen['storage'],dict)
                self.assertIsInstance(frozen['storage_policy'],str)
                self.assertFalse(frozen['cuda_initialized'])

    def test_previous_completed_or_failed_namespaces_not_reused(self):
        from scripts import diag_p106b_night_question_bundles_v2 as v2
        self.assertNotEqual(d.TAG,v2.TAG)
        self.assertNotEqual(d.FROZEN,v2.FROZEN)
        self.assertNotEqual(d.EVIDENCE,v2.EVIDENCE)


if __name__=='__main__':unittest.main()
