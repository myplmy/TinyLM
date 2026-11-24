"""Independent tiny full-softmax and changing-competitor controls."""
import math
import unittest
import torch
from scripts import p108b_margin as m


class MarginContracts(unittest.TestCase):
    def test_content_and_terminal_contributions_sum_to_full_loss(self):
        logits = torch.zeros(2,5,dtype=torch.float64)
        logits[0,1] = math.log(3)
        logits[1,4] = math.log(5)
        result = m.summarize(logits,torch.tensor([1,4]))
        self.assertAlmostEqual(result["content_ce"],math.log(7/3))
        self.assertAlmostEqual(result["eot_ce"],math.log(9/5))
        self.assertAlmostEqual(result["mean_ce"],result["content_contribution"]+result["eot_contribution"])
        self.assertAlmostEqual(result["first_gold_probability"],3/7)
        self.assertAlmostEqual(result["first_eot_probability"],1/7)

    def test_frozen_competitor_can_be_beaten_while_new_competitor_wins(self):
        logits=torch.zeros(2,5)
        logits[0,1]=2
        logits[0,2]=3
        result=m.summarize(logits,torch.tensor([1,4]),reference_competitor=0)
        self.assertEqual(result["reference_margin"],2.)
        self.assertEqual(result["true_margin"],-1.)
        self.assertEqual(result["first_argmax"],2)
        self.assertEqual(result["first_gold_rank"],2)

    def test_projection_uses_actual_delta_and_accumulates_without_param_grad(self):
        gradient=torch.tensor([[1.,2.],[-3.,4.]])
        delta=torch.tensor([[2.,1.],[1.,-1.]])
        self.assertEqual(m.directional_projection(gradient,delta),-3.)
        self.assertIsNone(gradient.grad)

    def test_missing_terminal_and_invalid_reference_rejected(self):
        with self.assertRaises(ValueError):m.summarize(torch.zeros(2,5),torch.tensor([1,2]))
        with self.assertRaises(ValueError):m.summarize(torch.zeros(2,5),torch.tensor([1,4]),reference_competitor=1)


if __name__=="__main__":unittest.main()
