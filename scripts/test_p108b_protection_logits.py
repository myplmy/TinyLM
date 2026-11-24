import unittest
import torch
from scripts.diag_p108b_protection_logits import compare

class ProtectionLogitTests(unittest.TestCase):
    def test_zero_comparison_is_zero(self):
        x=torch.tensor([[1.,2.],[3.,1.]])
        d=compare(x,x.clone(),torch.tensor([1,0]));self.assertEqual(d['max_absolute_logit_difference'],0)
        self.assertEqual(d['changed_argmax_positions'],0);self.assertEqual(d['mean_original_to_edited_kl'],0)
    def test_argmax_change_and_target_mass_are_measured(self):
        a=torch.tensor([[1.,2.]]);b=torch.tensor([[3.,1.]])
        d=compare(a,b,torch.tensor([1]));self.assertEqual(d['changed_argmax_positions'],1)
        self.assertGreater(d['mean_original_to_edited_kl'],0)
        self.assertLess(d['target_logp_after'][0],d['target_logp_before'][0])
    def test_shape_is_not_silently_broadcast(self):
        with self.assertRaises(ValueError):compare(torch.ones(2,3),torch.ones(1,3),torch.tensor([0,1]))

if __name__=='__main__':unittest.main()
