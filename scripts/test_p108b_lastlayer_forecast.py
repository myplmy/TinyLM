import unittest
import torch
from scripts import p108b_lastlayer_forecast as math_tools


class TestLastNormForecast(unittest.TestCase):
    def test_finite_difference(self):
        generator=torch.Generator().manual_seed(7)
        h=torch.randn(17,generator=generator,dtype=torch.float64);d=torch.randn(17,generator=generator,dtype=torch.float64)
        norm=lambda x:x*(x.square().mean()+1e-5).rsqrt()
        central=(norm(h+1e-6*d)-norm(h-1e-6*d))/2e-6
        torch.testing.assert_close(math_tools.rms_direction(h,d,1e-5),central,atol=1e-8,rtol=1e-7)

    def test_large_radial_change_is_nonlinear(self):
        h=torch.tensor([1.,2.,3.],dtype=torch.float64);d=-1.5*h
        norm=lambda x:x*(x.square().mean()+1e-5).rsqrt()
        exact=norm(h+d);linear=norm(h)+math_tools.rms_direction(h,d,1e-5)
        self.assertGreater(float((linear-exact).norm()),1.)

    def test_zero_direction(self):
        h=torch.arange(1.,5.);self.assertTrue(torch.equal(math_tools.rms_direction(h,torch.zeros_like(h),1e-5),torch.zeros(4,dtype=torch.float64)))

    def test_nonfinite_rejected(self):
        for eps in (-1,0,float('nan')):
            with self.assertRaises(ValueError):math_tools.rms_direction(torch.ones(3),torch.ones(3),eps)
        with self.assertRaises(ValueError):math_tools.rms_direction(torch.ones(3),torch.tensor([0.,1.,float('nan')]),1e-5)

    def test_exact_vocabulary_prediction(self):
        r=math_tools.compare(torch.tensor([1.,0.]),torch.tensor([0.,2.]),torch.tensor([0.,2.]))
        self.assertEqual(r['logit_rmse'],0.);self.assertTrue(r['exact_argmax'])


if __name__=='__main__':unittest.main()
