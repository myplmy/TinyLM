"""Analytic counterexamples for ratio scores and normalized gradient utility."""
import unittest
import torch
from scripts import p108b_support as s
from scripts import p108b_policy as old


class SupportTests(unittest.TestCase):
    def test_ratio_can_favor_tiny_absolute_gain(self):
        g=torch.tensor([[-1.,-2.]]);p=torch.tensor([[1e-9,1.]]);c=torch.eye(2)
        ratio,_=old.coordinate_scores(g,p,c)
        self.assertEqual(int(ratio.argmax()),0)
        self.assertEqual(int(s.scores('ABSGAIN',g,p,c).argmax()),1)
        self.assertEqual(int(s.scores('GRADCOST',g,p,c).argmax()),1)

    def test_normalized_gradient_score_preserves_coordinate_rescaling(self):
        g=torch.tensor([[2.,3.]],dtype=torch.float64);p=torch.ones_like(g);c=torch.diag(torch.tensor([2.,5.],dtype=torch.float64))
        scale=torch.diag(torch.tensor([.01,100.],dtype=torch.float64))
        torch.testing.assert_close(s.scores('GRADCOST',g,p,c),s.scores('GRADCOST',g@scale,p,scale@c@scale))
        # The Euclidean parameter budget itself is not invariant to this change.

    def test_support_count_and_nonfinite_failure(self):
        g=torch.arange(32.).reshape(2,16);p=torch.ones_like(g);c=torch.eye(16)
        mask,stats=s.select('GRADCOST',8,g,p,c)
        self.assertEqual(mask.sum().item(),4)
        self.assertTrue(bool(mask[:,-2:].all()))
        g[0,0]=float('nan')
        with self.assertRaises(ValueError):s.select('ABSGAIN',8,g,p,c)


if __name__=='__main__':unittest.main()
