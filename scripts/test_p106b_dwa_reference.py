import itertools
import unittest
import torch
from scripts import p106b_dwa_reference as d


class DwaIngredientContracts(unittest.TestCase):
    def setUp(self):torch.set_num_threads(1);torch.manual_seed(1337)
    def test_weights_normalize_to_each_sequence_length_and_detach(self):
        a=torch.randn(3,5,dtype=torch.float64,requires_grad=True);b=torch.randn(3,5,dtype=torch.float64,requires_grad=True);c=torch.randn(4,7,dtype=torch.float64,requires_grad=True)
        s,t=d.normalized_weights(a,b,c,detach=True);self.assertAlmostEqual(float(s.sum()),3.);self.assertAlmostEqual(float(t.sum()),4.);self.assertFalse(s.requires_grad);self.assertFalse(t.requires_grad)
    def test_explicit_differentiable_variant_is_not_silently_used(self):
        a=torch.randn(3,5,dtype=torch.float64,requires_grad=True);s,t=d.normalized_weights(a,a,torch.randn(4,7,dtype=torch.float64,requires_grad=True),detach=False)
        self.assertTrue(s.requires_grad);self.assertTrue(t.requires_grad)
    def test_uniform_teacher_zero_mass_requires_hold(self):
        with self.assertRaises(ValueError):d.normalized_weights(torch.randn(3,5),torch.randn(3,5),torch.zeros(4,7),detach=True)
    def test_soft_dtw_matches_exhaustive_tiny_paths(self):
        c=torch.tensor([[.2,.8],[.3,.4],[.9,.1]],dtype=torch.float64);values=[]
        def visit(i,j,total):
            total=total+c[i,j]
            if (i,j)==(2,1):values.append(total);return
            for di,dj in [(1,0),(0,1),(1,1)]:
                if i+di<3 and j+dj<2:visit(i+di,j+dj,total)
        visit(0,0,c.new_zeros(()));expected=-.3*torch.logsumexp(-torch.stack(values)/.3,dim=0)
        torch.testing.assert_close(d.soft_dtw(c,gamma=.3),expected,atol=1e-12,rtol=1e-12)
    def test_soft_dtw_gradient_matches_finite_difference(self):
        c=torch.randn(2,3,dtype=torch.float64,requires_grad=True);loss=d.soft_dtw(c,gamma=.2);g=torch.autograd.grad(loss,c)[0];eps=1e-6
        for i,j in itertools.product(range(2),range(3)):
            a=c.detach().clone();b=a.clone();a[i,j]+=eps;b[i,j]-=eps
            self.assertAlmostEqual(float(g[i,j]),float((d.soft_dtw(a,gamma=.2)-d.soft_dtw(b,gamma=.2))/(2*eps)),places=7)
    def test_unbanded_self_zero_and_symmetry(self):
        a=torch.randn(3,4,dtype=torch.float64);b=torch.randn(2,4,dtype=torch.float64)
        self.assertAlmostEqual(float(d.unbanded_divergence(a,a,gamma=.2)),0.,places=12)
        torch.testing.assert_close(d.unbanded_divergence(a,b,gamma=.2),d.unbanded_divergence(b,a,gamma=.2),atol=1e-12,rtol=1e-12)
    def test_band_uses_one_based_scaled_center_and_explicit_frozen_attention(self):
        c=torch.zeros(2,4,dtype=torch.float64,requires_grad=True);a=torch.tensor([[1.,0,0,0],[0,0,0,1.]],dtype=torch.float64,requires_grad=True)
        out=d.adaptive_band_cost(c,a,alpha=1.,base=0.,entropy_scale=0.,penalty=2.)
        self.assertEqual(out.detach().tolist(),[[0,2,2,2],[2,2,2,0]])
        self.assertIsNone(torch.autograd.grad(out.sum(),a,allow_unused=True)[0])
    def test_invalid_mass_dimension_and_unbounded_reference_fail(self):
        with self.assertRaises(ValueError):d.soft_dtw(torch.ones(65,65),gamma=.2)
        with self.assertRaises(ValueError):d.adaptive_band_cost(torch.zeros(2,3),torch.zeros(2,3))
        with self.assertRaises(ValueError):d.unbanded_divergence(torch.zeros(2,3),torch.ones(2,3),gamma=.2)


if __name__=='__main__':unittest.main()
