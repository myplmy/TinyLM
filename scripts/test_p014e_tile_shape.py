"""CPU-only numeric diagnosis statistics; no model/checkpoint/GPU execution."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

import torch
from scripts import diag_p014e_tile_shape as shape


class ShapeContract(unittest.TestCase):
    def test_same_argmax_is_not_a_relaxed_logit_gate(self):
        expected=torch.tensor([[0.0,10.0]])
        actual=torch.tensor([[7.6e-6,10.0]])
        result=shape.difference(actual,expected)
        self.assertTrue(result["argmax_equal"])
        self.assertFalse(result["original_allclose"])
        self.assertFalse(result["exact_equal"])
        self.assertEqual(result["outside_original_tolerance"],1)
        self.assertEqual(result["tolerance_unchanged"],dict(rtol=2e-5,atol=2e-6))

    def test_exact_control_is_separate_from_tolerance(self):
        tensor=torch.tensor([[1.0,-2.0,3.0]])
        result=shape.difference(tensor,tensor.clone())
        self.assertTrue(result["exact_equal"])
        self.assertEqual(result["max_abs"],0)
        self.assertEqual(result["relative_l2"],0)

    def test_bad_shape_dtype_and_nonfinite_refused(self):
        for tensor in (torch.zeros(2),torch.zeros(1,2,dtype=torch.float64),torch.tensor([[float("nan"),0.0]])):
            with self.assertRaises(ValueError):shape.difference(tensor,torch.zeros(1,2))


if __name__=="__main__":unittest.main()
