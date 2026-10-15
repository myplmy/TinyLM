#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from unittest.mock import patch
import torch
from scripts import p106b_relation_auxiliary as a


def fixture():
    hidden=torch.randn(3,12,8,requires_grad=True);y=torch.full((3,12),-100);seg=torch.zeros_like(y)
    y[0,8:]=1;seg[0,8:]=1
    y[1,8:10]=1;seg[1,8:10]=1;y[1,10:]=2;seg[1,10:]=2
    labels=[dict(spans=[[0,1],[3,4]],queries=[dict(position=8,label=1,turn=1)]),
        dict(spans=[[0,1],[3,4]],queries=[dict(position=8,label=0,turn=1),dict(position=10,label=1,turn=2)]),None]
    return hidden,y,seg,labels


class Auxiliary(unittest.TestCase):
    def test_cpu_rng_and_cuda_seed_side_effect_absent(self):
        before=torch.random.get_rng_state().clone()
        with patch.object(torch.cuda,'manual_seed_all',side_effect=AssertionError('must not seed CUDA')):head=a.new_head(8,rank=4)
        self.assertTrue(torch.equal(before,torch.random.get_rng_state()));self.assertEqual(sum(p.numel() for p in head.parameters()),64)

    def test_finite_nonzero_gradient_only_known_rows(self):
        h,y,s,l=fixture();head=a.new_head(8,rank=4);value,n,q,c=a.auxiliary_sum(head,h,y,s,l)
        self.assertEqual((n,q),(2,3));value.backward()
        self.assertGreater(float(h.grad[:2].abs().sum()),0.);self.assertEqual(float(h.grad[2].abs().sum()),0.)
        self.assertTrue(all(bool(torch.isfinite(p.grad).all()) for p in head.parameters()))

    def test_zero_weight_zero_grad_and_unknown_no_labels(self):
        h,y,s,l=fixture();head=a.new_head(8,rank=4);value,*_=a.auxiliary_sum(head,h,y,s,l);(value*0).backward()
        self.assertEqual(float(h.grad.abs().sum()),0.);self.assertTrue(all(float(p.grad.abs().sum())==0 for p in head.parameters()))
        h,y,s,l=fixture();value,n,q,c=a.auxiliary_sum(head,h,y,s,[None]*3);self.assertEqual((n,q,c),(0,0,0))

    def test_never_uses_old_wrong_answer_as_source_key(self):
        h,y,s,l=fixture();l[0]['spans'][0]=[8]
        with self.assertRaisesRegex(ValueError,'ANY assistant'):a.auxiliary_sum(a.new_head(8,rank=4),h,y,s,l)

    def test_query_inside_answer_rejected(self):
        h,y,s,l=fixture();l[0]['queries'][0]['position']=9
        with self.assertRaisesRegex(ValueError,'first supervised'):a.auxiliary_sum(a.new_head(8,rank=4),h,y,s,l)

    def test_row_mean_and_global_update_normalization(self):
        h,y,s,l=fixture();g=h.detach().clone().requires_grad_();head=a.new_head(8,rank=4);other=copy.deepcopy(head)
        loss,n,_,_=a.auxiliary_sum(head,h,y,s,l);(loss/n).backward()
        for begin,end in ((0,1),(1,3)):
            value,_,_,_=a.auxiliary_sum(other,g[begin:end],y[begin:end],s[begin:end],l[begin:end]);(value/n).backward()
        self.assertTrue(torch.allclose(h.grad,g.grad,atol=1e-7,rtol=1e-5))
        for p,q in zip(head.parameters(),other.parameters()):self.assertTrue(torch.allclose(p.grad,q.grad,atol=1e-7,rtol=1e-5))

    def test_corrective_first_ignored_only_second_query_legal(self):
        h,y,s,l=fixture();y[0,:]=-100;s[0,:]=0;s[0,5:7]=1;s[0,9:]=2;y[0,9:]=3
        l[0]['queries']=[dict(position=9,label=1,turn=2)]
        value,n,q,c=a.auxiliary_sum(a.new_head(8,rank=4),h,y,s,l)
        self.assertEqual((n,q),(2,3));self.assertTrue(bool(torch.isfinite(value)))


if __name__=='__main__':unittest.main()
