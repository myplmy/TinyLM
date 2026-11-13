import unittest
import torch
from scripts import p108_nullspace_write as n


class ProtectedInterpolation(unittest.TestCase):
    def test_exact_targets_and_unaffected_protected_inputs(self):
        k=torch.tensor([[1.,2.,0.,0.],[1.,0.,3.,0.]])
        v=torch.tensor([[.4,-.2],[.7,.3]])
        p=torch.tensor([[1.,0.,0.,0.],[0.,0.,0.,1.]])
        f,s=n.constrained_factors(k,v,p);d=n.dense_delta(f)
        self.assertTrue(torch.allclose(k@d.T,v,atol=1e-6))
        self.assertLess(float((p@d.T).norm()),1e-6)
        self.assertLess(s['target_relative_residual'],1e-10)

    def test_identical_causal_subject_keys_are_valid_with_same_value(self):
        k=torch.tensor([[0.,1.,1.],[0.,1.,1.]])
        v=torch.tensor([[2.,3.],[2.,3.]])
        f,_=n.constrained_factors(k,v,torch.tensor([[1.,0.,0.]]))
        self.assertTrue(torch.allclose(k@n.dense_delta(f).T,v,atol=1e-6))

    def test_inconsistent_duplicate_target_is_rejected(self):
        k=torch.tensor([[0.,1.,1.],[0.,1.,1.]])
        with self.assertRaises(ValueError):n.constrained_factors(k,torch.tensor([[2.],[3.]]),torch.tensor([[1.,0.,0.]]))

    def test_fully_protected_target_fails_closed(self):
        with self.assertRaises(ValueError):n.constrained_factors(torch.eye(2),torch.ones(2,1),torch.eye(2))

    def test_nan_and_zero_target_are_not_successful_noops(self):
        p=torch.tensor([[1.,0.,0.]])
        for k,v in ((torch.zeros(1,3),torch.ones(1,1)),(torch.ones(1,3),torch.zeros(1,1)),
                    (torch.full((1,3),float('nan')),torch.ones(1,1))):
            with self.assertRaises(ValueError):n.constrained_factors(k,v,p)

    def test_scale_equivariance_preserves_finite_constraint(self):
        k=torch.tensor([[0.,1.,2.]]);v=torch.tensor([[3.,4.]]);p=torch.tensor([[1.,0.,0.]])
        a,_=n.constrained_factors(k,v,p);b,_=n.constrained_factors(k*4000,v*4000,p*4000)
        self.assertTrue(torch.allclose(n.dense_delta(a),n.dense_delta(b),atol=1e-6))


if __name__=='__main__':unittest.main()
