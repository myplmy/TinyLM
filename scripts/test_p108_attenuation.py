"""Independent tiny algebra and calibration-scope oracles for P108 diagnosis."""
import unittest
import torch

from scripts import diag_p108_attenuation as audit


class AttenuationContract(unittest.TestCase):
    def test_identity_ridge_matches_closed_form(self):
        k=torch.eye(3,dtype=torch.float64)
        v=torch.tensor([[2.,1.],[-3.,4.],[5.,-6.]],dtype=torch.float64)
        full,residual,normal=audit.reference_ridge(k,v,.5)
        torch.testing.assert_close(full,v.T/1.5,rtol=1e-12,atol=1e-12)
        self.assertLess(normal,1e-12)
        self.assertAlmostEqual(residual,float((v/3).square().sum()),places=10)

    def test_explicit_eot_boundaries_and_no_holdout(self):
        rows=[dict(id='calib_a',targets=2,eot_targets=1),dict(id='calib_b',targets=3,eot_targets=1)]
        self.assertEqual(audit.partition_targets(rows,5),dict(all=list(range(5)),body=[0,2,3],eot=[1,4]))
        for invalid,total in (([dict(id='test_a',targets=2,eot_targets=1)],2),(rows,6),(rows+rows,10)):
            with self.assertRaises(ValueError):audit.partition_targets(invalid,total)

    def test_zero_change_preserves_signs_and_exact_target(self):
        margin=torch.tensor([-2.,0.,1.,3.],dtype=torch.float64)
        stats=audit.statistics(margin,torch.zeros_like(margin),{'all':list(range(4))})['all']
        self.assertEqual((stats['original_positive'],stats['predicted_positive']),(2,2))
        self.assertEqual((stats['predicted_new_positive'],stats['predicted_regressions']),(0,0))

    def test_scale_and_regression_counts_are_direction_sensitive(self):
        margin=torch.tensor([-1.,2.],dtype=torch.float64)
        gain=torch.tensor([2.,-3.],dtype=torch.float64)
        full=audit.statistics(margin,gain,{'all':[0,1]})['all']
        small=audit.statistics(margin,gain*.1,{'all':[0,1]})['all']
        self.assertEqual((full['predicted_new_positive'],full['predicted_regressions']),(1,1))
        self.assertEqual((small['predicted_new_positive'],small['predicted_regressions']),(0,0))

    def test_nonfinite_or_wrong_tensor_shape_is_rejected(self):
        packet=dict(keys=torch.eye(2),values=torch.eye(2),gradients=torch.eye(2),margins=torch.zeros(2),
            factors=dict(left=torch.eye(2),right=torch.eye(2)))
        audit.validate_packet(packet)
        for name,value in (('margins',torch.tensor([float('nan'),0.])),('gradients',torch.zeros(3,2))):
            wrong=dict(packet);wrong[name]=value
            with self.assertRaises(ValueError):audit.validate_packet(wrong)

    def test_zero_key_and_empty_or_invalid_groups_are_rejected(self):
        with self.assertRaises(ValueError):audit.reference_ridge(torch.zeros(2,2),torch.ones(2,2),.1)
        for positions in ([],[-1],[2]):
            with self.assertRaises(ValueError):audit.statistics(torch.zeros(2),torch.zeros(2),{'all':positions})


if __name__ == '__main__':
    unittest.main()
