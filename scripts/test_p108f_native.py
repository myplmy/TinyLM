"""Signed bits, exception rollback, cache rejection and exact head assembly."""
import unittest
from types import SimpleNamespace
import numpy as np
import torch
from scripts import p108f_native as native
from scripts import p108_weight_space as identity


class Norm(torch.nn.Module):
    def __init__(self):
        super().__init__();self.weight=torch.nn.Parameter(torch.tensor([.1,-.2,.3]));self.eps=1e-6
    def forward(self,x):return x*(x.square().mean(dim=-1,keepdim=True)+self.eps).rsqrt()*(1+self.weight)


class NativeTransportContracts(unittest.TestCase):
    def test_exact_after_including_cancellation_and_signed_zero(self):
        module=torch.nn.Linear(2,2,bias=False)
        with torch.no_grad():module.weight.copy_(torch.tensor([[1e20,-0.],[3.,-4.]]))
        before=identity.tensor_sha(module.weight);after=np.array([[1.,-0.],[6.,-8.]],np.float32)
        with native.temporary_after(module,after):
            self.assertEqual(identity.tensor_sha(module.weight),identity.tensor_sha(torch.from_numpy(after)))
        self.assertEqual(identity.tensor_sha(module.weight),before)

    def test_exception_restores_original(self):
        module=torch.nn.Linear(2,2,bias=False);before=identity.tensor_sha(module.weight)
        with self.assertRaisesRegex(RuntimeError,"sentinel"):
            with native.temporary_after(module,np.ones((2,2),np.float32)):raise RuntimeError("sentinel")
        self.assertEqual(identity.tensor_sha(module.weight),before)

    def test_unverified_cache_and_precision_rejected(self):
        module=torch.nn.Linear(2,2,bias=False).half()
        with self.assertRaises(ValueError):
            with native.temporary_after(module,np.ones((2,2),np.float32)):pass
        module=module.float();module._wq=torch.ones(2,2)
        with self.assertRaises(ValueError):
            with native.temporary_after(module,np.ones((2,2),np.float32)):pass

    def test_same_head_zero_direction(self):
        body=SimpleNamespace(model=SimpleNamespace(norm=Norm()),lm_head=torch.nn.Linear(3,5,bias=False),
                             config=SimpleNamespace(final_logit_softcapping=2.5))
        x=torch.tensor([1.,2.,3.]);zero=torch.zeros(3)
        expected=2.5*torch.tanh(body.lm_head(body.model.norm(x[None,None]))[0,0]/2.5)
        torch.testing.assert_close(native.gemma_head(body,x),expected)
        torch.testing.assert_close(native.gemma_linear_head(body,x,zero),expected)


if __name__=="__main__":unittest.main()
