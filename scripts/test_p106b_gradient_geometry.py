import unittest
import torch
from scripts.p106b_gradient_geometry import geometry


class GeometryContracts(unittest.TestCase):
    def test_parallel_gradient_scale(self):
        r=geometry({'a':torch.tensor([3.,4.])},{'a':torch.tensor([6.,8.])})
        self.assertEqual(r['cosine'],1.);self.assertEqual(r['alpha_for_equal_norm'],.5);self.assertFalse(r['production_coefficient_selected'])
    def test_opposite_and_orthogonal(self):
        self.assertEqual(geometry({'a':torch.tensor([1.,0.])},{'a':torch.tensor([-1.,0.])})['cosine'],-1.)
        self.assertEqual(geometry({'a':torch.tensor([1.,0.])},{'a':torch.tensor([0.,1.])})['cosine'],0.)
    def test_zero_norm_is_not_confidence_or_perfect_alignment(self):
        r=geometry({'a':torch.zeros(2)},{'a':torch.zeros(2)});self.assertIsNone(r['cosine']);self.assertIsNone(r['alpha_for_equal_norm'])
    def test_mismatched_parameter_space_fails(self):
        with self.assertRaises(ValueError):geometry({'a':torch.ones(2)},{'b':torch.ones(2)})
    def test_nonfinite_or_shape_mismatch_fails(self):
        for t in [torch.tensor([float('nan')]),torch.ones(2)]:
            with self.assertRaises(ValueError):geometry({'a':torch.ones(1)},{'a':t})


if __name__=='__main__':unittest.main()
