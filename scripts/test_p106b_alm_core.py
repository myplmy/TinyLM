#!/usr/bin/env python3
"""Synthetic CPU scalar/gradient oracles; no real data, checkpoint, or GPU."""
from __future__ import annotations
import copy
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
import torch
import torch.nn.functional as F
from tinylm.train import alm
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer


def tiny():
    torch.manual_seed(19)
    return TiedMLPTransformer(TMTConfig(vocab_size=31,dim=16,ffn_dim=32,
        n_prelude=1,n_middle=2,n_coda=1,n_q_heads=4,n_kv_heads=2,
        emb_rank=8,max_seq_len=32,tie_mlp=False,micro_group=4,mlp_group=2,cla_group=1))


class ALMTests(unittest.TestCase):
    def test_same_distribution_kl_and_gradient_zero_not_entropy(self):
        s=torch.tensor([-.01,-.5,-2.,-1000.],dtype=torch.double,requires_grad=True)
        v=alm.binary_kl_logq(s,s.detach())
        self.assertTrue(torch.equal(v,torch.zeros_like(v)))
        v.sum().backward()
        self.assertTrue(torch.allclose(s.grad,torch.zeros_like(s),atol=1e-14,rtol=0))

    def test_scalar_oracle_and_finite_difference(self):
        for sv,tv in [(-.1,-.3),(-2.,-.3),(-.3,-2.),(-20.,-40.)]:
            s=torch.tensor([sv],dtype=torch.double,requires_grad=True)
            t=torch.tensor([tv],dtype=torch.double)
            v=alm.binary_kl_logq(s,t);v.sum().backward()
            qs,qt=math.exp(sv),math.exp(tv)
            expected=qt*math.log(qt/qs)+(1-qt)*math.log((1-qt)/(1-qs))
            self.assertAlmostEqual(float(v.detach()),expected,places=13)
            e=1e-6
            finite=float((alm.binary_kl_logq(s.detach()+e,t)-alm.binary_kl_logq(s.detach()-e,t))/(2*e))
            self.assertAlmostEqual(float(s.grad),finite,places=8)

    def test_teacher_has_no_gradient_and_teacher_one(self):
        s=torch.tensor([-.7,0.],dtype=torch.double,requires_grad=True)
        t=torch.tensor([0.,0.],dtype=torch.double,requires_grad=True)
        v=alm.binary_kl_logq(s,t);v.sum().backward()
        self.assertTrue(torch.equal(v,torch.tensor([.7,0.],dtype=torch.double)))
        self.assertTrue(torch.equal(s.grad,torch.tensor([-1.,-1.],dtype=torch.double)))
        self.assertIsNone(t.grad)
        with self.assertRaises(FloatingPointError):
            alm.binary_kl_logq(torch.tensor([0.]),torch.tensor([-.1]))

    def test_log1mexp_extreme_gradients(self):
        x=torch.tensor([-1e-12,-.001,-.8,-1000.],dtype=torch.double,requires_grad=True)
        v=alm.log1mexp(x);v.sum().backward()
        self.assertTrue(torch.isfinite(v).all() and torch.isfinite(x.grad).all())
        for bad in [0.,.1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError): alm.log1mexp(torch.tensor([bad]))

    def test_original_tied_head_ce_and_all_gradient_parity(self):
        x=torch.tensor([[1,2,3,4,0],[5,6,7,8,9]])
        y=torch.tensor([[-100,3,4,-100,-100],[6,-100,8,9,10]])
        base=tiny(); gradients=[];losses=[]
        for mode in ['full','chunk','checkpoint']:
            model=copy.deepcopy(base);hidden=model(x,return_hidden=True)
            if mode=='full':
                loss=F.cross_entropy(model._head_logits(hidden).reshape(-1,31).float(),y.reshape(-1),ignore_index=-100,reduction='sum')
            else:
                values,mask=alm.target_nll(model,hidden,y,chunk=2,checkpoint_head=mode=='checkpoint')
                self.assertEqual(int(mask.sum()),6)
                self.assertTrue(torch.equal(values[~mask],torch.zeros_like(values[~mask])))
                loss=values.sum()
            loss.backward();losses.append(loss.detach())
            gradients.append({k:p.grad.clone() for k,p in model.named_parameters() if p.grad is not None})
        for loss in losses[1:]:self.assertTrue(torch.allclose(loss,losses[0],atol=2e-6,rtol=1e-5))
        self.assertIn('emb.weight',gradients[0])
        for g in gradients[1:]:
            self.assertEqual(set(g),set(gradients[0]))
            for key in g:self.assertTrue(torch.allclose(g[key],gradients[0][key],atol=2e-6,rtol=1e-5),key)

    def test_zero_targets_never_evaluates_head(self):
        class NoHead:
            def _head_logits(self,_):raise AssertionError('head must not run')
        h=torch.randn(2,3,4,requires_grad=True);y=torch.full((2,3),-100)
        v,mask=alm.target_nll(NoHead(),h,y);v.sum().backward()
        self.assertEqual(int(mask.sum()),0);self.assertTrue(torch.equal(h.grad,torch.zeros_like(h)))

    def test_whole_update_micro_accumulation_parity(self):
        raw=torch.tensor([[.2,.4,.8],[.3,.7,.6]],dtype=torch.double)
        mask=torch.ones_like(raw,dtype=torch.bool)
        chunks=[dict(row=0,positions=[0,1],teacher_logprob=-.9),dict(row=1,positions=[1,2],teacher_logprob=-.8)]
        a=raw.clone().requires_grad_();k,n=alm.chunk_kl(a,mask,chunks,temperature=2.)
        full=alm.normalized_loss(a.sum(),6,k,n,weight=.3);full.backward()
        b=raw.clone().requires_grad_();parts=[]
        for i in range(2):
            c=[dict(chunks[i],row=0)]
            k,n=alm.chunk_kl(b[i:i+1],mask[i:i+1],c,temperature=2.)
            parts.append(alm.normalized_loss(b[i:i+1].sum(),6,k,2,weight=.3))
        sum(parts).backward()
        self.assertTrue(torch.allclose(full,sum(parts),atol=1e-14,rtol=0))
        self.assertTrue(torch.allclose(a.grad,b.grad,atol=1e-14,rtol=0))

    def test_unequal_micro_target_and_chunk_counts_including_zero_kd(self):
        raw=torch.tensor([[.2,.4,.8],[.3,.7,.6]],dtype=torch.double)
        mask=torch.tensor([[True,False,False],[True,True,True]])
        chunks=[dict(row=1,positions=[0],teacher_logprob=-.9),
                dict(row=1,positions=[1,2],teacher_logprob=-.8)]
        a=raw.clone().requires_grad_();k,n=alm.chunk_kl(a,mask,chunks,temperature=2.)
        full=alm.normalized_loss(a[mask].sum(),4,k,2,weight=.3);full.backward()
        b=raw.clone().requires_grad_();parts=[]
        for i in range(2):
            c=[] if i==0 else [dict(chunk,row=0) for chunk in chunks]
            k,count=alm.chunk_kl(b[i:i+1],mask[i:i+1],c,temperature=2.)
            self.assertEqual(count,0 if i==0 else 2)
            parts.append(alm.normalized_loss(b[i:i+1][mask[i:i+1]].sum(),4,k,2,weight=.3))
        sum(parts).backward()
        self.assertTrue(torch.allclose(full,sum(parts),atol=1e-14,rtol=0))
        self.assertTrue(torch.allclose(a.grad,b.grad,atol=1e-14,rtol=0))

    def test_nonlinear_kl_through_original_tied_head_all_gradient_parity(self):
        x=torch.tensor([[1,2,3,4],[5,6,7,8]])
        y=torch.tensor([[-100,3,4,5],[6,-100,8,9]])
        chunks=[dict(row=0,positions=[1,2],teacher_logprob=-.3),
                dict(row=1,positions=[0],teacher_logprob=-4.),
                dict(row=1,positions=[2,3],teacher_logprob=-1.2)]
        gradients=[];losses=[];base=tiny()
        for full in (True,False):
            model=copy.deepcopy(base);hidden=model(x,return_hidden=True);mask=y.ne(-100)
            if full:
                nll=F.cross_entropy(model._head_logits(hidden).reshape(-1,31).float(),
                    y.reshape(-1),ignore_index=-100,reduction='none').reshape_as(y)
            else:nll,_=alm.target_nll(model,hidden,y,chunk=2,checkpoint_head=True)
            k,count=alm.chunk_kl(nll,mask,chunks,temperature=2.)
            loss=alm.normalized_loss(nll.sum(),6,k,count,weight=.7)
            loss.backward();losses.append(loss.detach())
            gradients.append({name:p.grad.clone() for name,p in model.named_parameters() if p.grad is not None})
        self.assertTrue(torch.allclose(losses[0],losses[1],atol=2e-6,rtol=1e-5))
        self.assertEqual(set(gradients[0]),set(gradients[1]))
        for name in gradients[0]:
            self.assertTrue(torch.allclose(gradients[0][name],gradients[1][name],atol=2e-6,rtol=1e-5),name)

    def test_sampler_underflow_sentinel_rejected_and_q1_classified(self):
        nll=torch.tensor([[0.]],requires_grad=True);mask=torch.tensor([[True]])
        for value in (-3.402823466e38,-1e30):
            with self.assertRaises(ValueError):
                alm.chunk_kl(nll,mask,[dict(row=0,positions=[0],teacher_logprob=value)])
        with self.assertRaisesRegex(alm.StudentProbabilityBoundary,'ROUNDED_OR_EXACT_STUDENT_Q1'):
            alm.chunk_kl(nll,mask,[dict(row=0,positions=[0],teacher_logprob=-.1)])

    def test_chunks_reject_mask_overlap_bad_probability_and_empty(self):
        a=torch.ones(1,3,requires_grad=True);mask=torch.tensor([[True,False,True]])
        for chunks in [[dict(row=0,positions=[1],teacher_logprob=-1.)],
                       [dict(row=0,positions=[0],teacher_logprob=-1.)]*2,
                       [dict(row=0,positions=[0],teacher_logprob=.1)],
                       [dict(row=True,positions=[0],teacher_logprob=-1.)]]:
            with self.assertRaises(ValueError):alm.chunk_kl(a,mask,chunks)
        k,n=alm.chunk_kl(a,mask,[]);self.assertEqual(n,0);k.backward()
        self.assertTrue(torch.equal(a.grad,torch.zeros_like(a)))
        with self.assertRaises(ValueError):alm.normalized_loss(a.sum(),2,k,0,weight=.1)

    def test_chunk_positions_are_original_contiguous_and_ordered(self):
        nll=torch.ones(1,4,requires_grad=True);mask=torch.ones_like(nll,dtype=torch.bool)
        for positions in ([0,2],[2,1],[0,1,3]):
            with self.subTest(positions=positions),self.assertRaises(ValueError):
                alm.chunk_kl(nll,mask,[dict(row=0,positions=positions,teacher_logprob=-1.)])


if __name__=='__main__':unittest.main()
