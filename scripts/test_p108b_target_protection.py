import unittest
import torch
from scripts import p108b_target_protection as helper

class TargetProtectionTests(unittest.TestCase):
    def test_protected_direction_is_zero_at_matched_norm(self):
        k=torch.tensor([[1.,1.],[2.,-1.],[1.,2.]],dtype=torch.float64)
        v=torch.tensor([[3.,4.],[1.,-2.]],dtype=torch.float64)
        p=torch.tensor([[1.,0.,0.]],dtype=torch.float64)
        d,s=helper.candidate(k,v,p,.25,protect=True)
        self.assertAlmostEqual(float(d.double().norm()),.25*(1-1e-6),places=7)
        self.assertLess(float((d.double()@p.T).norm()),1e-12)
        self.assertTrue(s['protection_used'])

    def test_unprotected_control_changes_only_constraint(self):
        k=torch.eye(3,dtype=torch.float64)[:,:2];v=torch.ones(2,2,dtype=torch.float64)
        p=torch.tensor([[1.,0.,0.]],dtype=torch.float64)
        d,s=helper.candidate(k,v,p,.25,protect=False)
        self.assertGreater(float((d.double()@p.T).norm()),0)
        self.assertEqual(s['protected_rank'],0)

    def test_infeasible_full_protection_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'infeasible'):
            helper.candidate(torch.eye(2),torch.eye(2),torch.eye(2),.25,protect=True)

    def test_input_contract_rejects_nonboolean_and_nonfinite(self):
        for budget,protect in [(float('nan'),True),(.25,1),(-.25,True)]:
            with self.assertRaises(ValueError):helper.candidate(torch.eye(2),torch.eye(2),torch.ones(1,2),budget,protect=protect)

if __name__=='__main__':unittest.main()
