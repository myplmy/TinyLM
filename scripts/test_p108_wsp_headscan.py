"""CPU-only tests for causal reference positions and separately scored EOT."""
import unittest
import torch
from scripts.diag_p108_wsp_headscan import components


class HeadscanReferenceTests(unittest.TestCase):
    def test_reference_positions_and_correct_eot_are_distinct(self):
        logits=torch.zeros(1,5,8)
        logits[0,2,5]=10;logits[0,3,6]=10;logits[0,4,4]=10
        good=components(logits,3,[5,6])
        self.assertLess(float(good.max()),.001)
        logits[0,4,4]=-10
        bad=components(logits,3,[5,6])
        self.assertEqual(float(good[0]),float(bad[0]))
        self.assertGreater(float(bad[1]),10)

    def test_invalid_positions_empty_and_terminal_body_fail(self):
        for prefix,answer in ((0,[5,6]),(3,[]),(3,[4,6]),(4,[5,6])):
            with self.assertRaises(ValueError):components(torch.zeros(1,5,8),prefix,answer)

    def test_nonfinite_reference_score_fails(self):
        logits=torch.zeros(1,5,8);logits[0,2,5]=float('nan')
        with self.assertRaises(ValueError):components(logits,3,[5,6])


if __name__=='__main__':unittest.main()
