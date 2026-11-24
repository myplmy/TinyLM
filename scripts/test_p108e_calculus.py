"""CPU central differences of an actual nonlinear two-matrix toy network."""
import unittest
import numpy as np
import torch
from scripts.p108e_calculus import projected_vjps


class NativeDerivativeContracts(unittest.TestCase):
    def test_projected_vjp_matches_nonlinear_fixed_rival_difference(self):
        torch.manual_seed(17)
        first=torch.nn.Parameter(torch.randn(3,4,dtype=torch.float64)*.2)
        second=torch.nn.Parameter(torch.randn(5,3,dtype=torch.float64)*.2)
        inputs=torch.randn(2,4,dtype=torch.float64)
        def model():return torch.tanh(inputs@first.T)@second.T
        right={0:np.eye(4)[:2],1:np.eye(3)[:2]}
        left={0:np.eye(3)[:,:2],1:np.eye(5)[:,:3]}
        original_first=first.detach().clone();original_second=second.detach().clone()
        logits=model();gold=[1,4]
        blocks,record=projected_vjps(logits,gold,{0:first,1:second},right,lefts=left)
        for layer,parameter in ((0,first),(1,second)):
            theta=np.arange(blocks[layer].shape[1]*blocks[layer].shape[2],dtype=float).reshape(blocks[layer].shape[1:])+1
            theta/=np.linalg.norm(theta)
            direction=torch.tensor(left[layer]@theta@right[layer],dtype=torch.float64)
            expected=float(np.sum(blocks[layer][0]*theta));observed=[]
            for sign in (-1,1):
                with torch.no_grad():parameter.add_(sign*1e-5*direction)
                value=model()[0]
                observed.append(float((value[gold[0]]-value[record["rivals"][0]]).detach()))
                with torch.no_grad():parameter.copy_(original_first if layer==0 else original_second)
            self.assertAlmostEqual((observed[1]-observed[0])/(2e-5),expected,places=8)
        self.assertIsNone(first.grad);self.assertIsNone(second.grad)
        torch.testing.assert_close(first,original_first,rtol=0,atol=0)
        torch.testing.assert_close(second,original_second,rtol=0,atol=0)

    def test_preexisting_persistent_gradient_is_rejected(self):
        weight=torch.nn.Parameter(torch.eye(2));weight.grad=torch.ones_like(weight)
        with self.assertRaises(ValueError):projected_vjps(weight@weight,[0,1],{0:weight},{0:np.eye(2)})


if __name__=="__main__":unittest.main()
