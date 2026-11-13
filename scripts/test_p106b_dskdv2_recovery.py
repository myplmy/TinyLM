import unittest
import numpy as np
from scripts import p106b_dskdv2_recovery as r


class RecoveryContracts(unittest.TestCase):
    def test_feature_header_shape_dtype_contiguity_and_finite_values_are_required(self):
        r.feature_contract(np.ones((3,4),dtype=np.float32),tokens=3,width=4)
        for bad in [np.ones((2,4),dtype=np.float32),np.ones((3,4),dtype=np.float64),np.full((3,4),np.nan,dtype=np.float32)]:
            with self.assertRaises(ValueError):r.feature_contract(bad,tokens=3,width=4)
    def test_first_subtoken_mode_is_still_held_and_false_acceptance_is_rejected(self):
        mapping=[7,8,9];modes=[1,2,3]
        def row(token,good):return dict(teacher_native_argmax=token,accepted=good,mapping_mode=modes[token],
            mapped_student_argmax=mapping[token]if good else None,teacher_native_argmax_logit=1.,teacher_native_logsumexp=2.)
        self.assertTrue(r.acceptance_contract(row(0,True),mapping,modes))
        self.assertFalse(r.acceptance_contract(row(1,False),mapping,modes))
        self.assertTrue(r.acceptance_contract(row(2,True),mapping,modes))
        with self.assertRaises(ValueError):r.acceptance_contract(row(1,True),mapping,modes)
    def test_empty_trace_finalizer_error_does_not_hide_other_manifest_or_raise_before_report_writer(self):
        calls=[]
        class Broken:
            def close(self,*,lineage):calls.append('broken');raise ValueError('empty')
        class Good:
            def close(self,*,lineage):calls.append('good');return dict(rows=128,lineage=lineage)
        manifests,errors=r.close_outputs([('trace',Broken()),('positions',Good())],lineage=dict(tag='fixture'))
        self.assertEqual(calls,['broken','good']);self.assertEqual(manifests['positions']['rows'],128)
        self.assertIn('trace',errors);self.assertNotIn('positions',errors)


if __name__=='__main__':unittest.main()
