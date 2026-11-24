import unittest
import torch
from scripts import p108b_hf_suffix_forecast as forecast


class Norm(torch.nn.Module):
    def __init__(self,weight):
        super().__init__();self.weight=torch.nn.Parameter(weight);self.eps=1e-6
    def forward(self,x):return x*(x.square().mean()+self.eps).rsqrt()*(1+self.weight)


class TestTwoNormSuffix(unittest.TestCase):
    def test_two_learned_scales_and_softcap_derivative(self):
        generator=torch.Generator().manual_seed(81)
        vector=lambda:torch.randn(7,generator=generator,dtype=torch.float64)
        post,final=Norm(vector()*.2),Norm(vector()*.2)
        head=torch.nn.Linear(7,13,bias=False).double();head.weight.data.copy_(torch.randn(13,7,generator=generator,dtype=torch.float64))
        residual,y,d=vector(),vector(),vector()
        def function(x):return forecast.cap_logits(head(final(residual+post(x))),2.5)
        exact,linear=forecast.predict(post,final,head,residual,y,d,2.5)
        torch.testing.assert_close(exact,function(y+d),atol=1e-12,rtol=1e-12)
        derivative=(function(y+1e-5*d)-function(y-1e-5*d))/2e-5
        # Production gains are FP32 by the actual Gemma contract.
        torch.testing.assert_close(linear-function(y),derivative,atol=2e-7,rtol=2e-6)

    def test_zero_change(self):
        p,f=Norm(torch.zeros(3)),Norm(torch.zeros(3));head=torch.nn.Linear(3,4,bias=False)
        h=torch.tensor([1.,2.,3.]);v=torch.tensor([2.,1.,-1.])
        exact,linear=forecast.predict(p,f,head,h,v,torch.zeros(3))
        torch.testing.assert_close(exact,head(f(h+p(v))))
        torch.testing.assert_close(exact,linear)

    def test_invalid_softcap(self):
        for x in (0,-1,float('nan')):
            with self.assertRaises(ValueError):forecast.cap_logits(torch.ones(3),x)

    def test_nonlinear_large_change(self):
        p,f=Norm(torch.zeros(3)),Norm(torch.zeros(3));head=torch.nn.Linear(3,3,bias=False)
        head.weight.data.copy_(torch.eye(3));h=torch.tensor([1.,-2.,1.]);v=torch.tensor([2.,3.,-1.]);d=-2*v
        exact,linear=forecast.predict(p,f,head,h,v,d)
        self.assertGreater(float((exact-linear).norm()),.1)


if __name__=='__main__':unittest.main()
