"""CPU regression of numerical predicates used for saved-history replay."""
import unittest
import torch
from scripts import diag_p106b_longkv_saved as diag


class NumericContract(unittest.TestCase):
    def test_identical_logits(self):
        x=torch.tensor([[1.,2.,3.]])
        r=diag.compare_logits(x,x.clone(),torch)
        self.assertTrue(r['float_close'] and r['argmax_equal'])
        self.assertEqual(r['max_abs'],0.)

    def test_small_drift_with_same_argmax(self):
        x=torch.tensor([[1.,2.,3.]])
        r=diag.compare_logits(x,x+1e-6,torch)
        self.assertTrue(r['float_close'] and r['argmax_equal'])
        self.assertGreater(r['max_abs'],0.)

    def test_near_tie_argmax_is_separate(self):
        r=diag.compare_logits(torch.tensor([[1.,1.000001]]),torch.tensor([[1.000001,1.]]),torch)
        self.assertTrue(r['float_close'])
        self.assertFalse(r['argmax_equal'])

    def test_large_drift_is_not_silent(self):
        r=diag.compare_logits(torch.tensor([[1.,2.]]),torch.tensor([[1.,3.]]),torch)
        self.assertFalse(r['float_close'])
        self.assertTrue(r['argmax_equal'])

    def test_owner_and_shape(self):
        x=torch.ones(1,2,768,4)
        r=diag.compare_kv({(0,0):(x,x)},{(0,0):(x.clone(),x.clone())},torch)
        self.assertEqual(r[0]['owner'],'(0, 0)')
        self.assertTrue(all(v['float_close'] for v in r[0]['tensors']))

    def test_missing_owner_fails(self):
        x=torch.ones(1,2,2,4)
        with self.assertRaises(AssertionError):diag.compare_kv({0:(x,x)},{1:(x,x)},torch)

    def test_changed_cache_fails_predicate(self):
        x=torch.ones(1,2,2,4)
        r=diag.compare_kv({0:(x,x)},{0:(x,x+1.)},torch)
        self.assertFalse(r[0]['tensors'][1]['float_close'])

    def test_changed_shape_fails(self):
        x=torch.ones(1,2,2,4)
        with self.assertRaises(AssertionError):diag.compare_kv({0:(x,x)},{0:(x[:,:,:1],x)},torch)


if __name__=='__main__':unittest.main()
