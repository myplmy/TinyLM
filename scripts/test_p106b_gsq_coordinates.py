"""Synthetic CPU contracts for the unfinished coordinate/Lion diagnostic.

No checkpoint, real dataset, model-quality evaluation or CUDA is opened.
"""
import math
import unittest
import torch
from scripts import p106b_gsq_coordinates as c
from scripts import p106b_gsq_objective as core
from scripts.test_p106b_gsq_objective import tiny,bytes_of


class CoordinateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(1)

    def test_coordinate_gain_preserves_initial_hard_matrix(self):
        m=tiny();w=m.emb_up.weight.detach();group=m.cfg.micro_group
        a=core.GSQBank(w,group,m.cfg,logit_strength=4.6).eval()
        for gain in (1.,20.,200.):
            b=c.ScaledGSQBank(w,group,m.cfg,logit_strength=4.6,gain=gain).eval()
            self.assertTrue(torch.equal(a.matrix(),b.matrix()))

    def test_seeded_stochastic_forward_and_scaled_chain_gradient(self):
        m=tiny();w=m.emb_up.weight.detach();group=m.cfg.micro_group
        a=core.GSQBank(w,group,m.cfg,logit_strength=4.6).train()
        b=c.ScaledGSQBank(w,group,m.cfg,logit_strength=4.6,gain=200.).train()
        results=[]
        for bank in (a,b):
            torch.manual_seed(39117);value=bank.matrix();value.sum().backward();results.append(value.detach())
        self.assertTrue(torch.equal(*results))
        torch.testing.assert_close(b.mask_logit.grad,a.mask_logit.grad*200,rtol=2e-5,atol=2e-5)
        torch.testing.assert_close(b.scale.grad,a.scale.grad,rtol=0,atol=0)

    def test_factory_patch_is_scoped_and_shared_banks_are_unique(self):
        m=tiny().eval();original=core.GSQBank;before=bytes_of(m)
        bridge=c.scaled_bridge(m)
        self.assertIs(core.GSQBank,original)
        self.assertTrue(all(isinstance(b,c.ScaledGSQBank) for b in bridge.banks.values()))
        self.assertEqual(len(bridge.banks),len({id(v) for v in bridge.masters.values()}))
        with bridge.installed(),torch.no_grad(),bridge.realization(17):
            self.assertIs(m._emb_w(),bridge._current[bridge.embedding])
        for key,value in bytes_of(m).items():self.assertTrue(torch.equal(value,before[key]),key)

    def test_invalid_gain_and_nonfinite_projection_fail_closed(self):
        m=tiny();w=m.emb_up.weight.detach()
        for gain in (0,-1,math.inf,math.nan):
            with self.assertRaises(ValueError):c.ScaledGSQBank(w,4,m.cfg,gain=gain)
        bank=c.ScaledGSQBank(w,4,m.cfg)
        with torch.no_grad():bank.sign_logit[0,0,0]=math.nan
        with self.assertRaises(FloatingPointError):bank.bound()

    def test_bound_is_in_effective_confidence_coordinates(self):
        m=tiny();bank=c.ScaledGSQBank(m.emb_up.weight.detach(),4,m.cfg,gain=200.)
        with torch.no_grad():bank.mask_logit.fill_(1);bank.sign_logit.fill_(-1);bank.scale.fill_(-1)
        bank.bound()
        self.assertLessEqual(float(bank.mask_logit.detach().max()),.06000001)
        self.assertGreaterEqual(float(bank.sign_logit.detach().min()),-.06000001)
        self.assertTrue(bool(bank.scale.gt(0).all()))

    def test_fresh_adam_bound_and_invalid_assumptions(self):
        self.assertEqual(c.adam_coordinate_bound(0,1e-5),0)
        self.assertLess(c.adam_coordinate_bound(256,1e-5),4.6)
        for n,lr,betas in ((-1,1e-5,(.9,.95)),(3,-1,(.9,.95)),(3,1,(.99,.5))):
            with self.assertRaises(ValueError):c.adam_coordinate_bound(n,lr,betas)

    def test_optimizer_groups_keep_logits_and_scale_rates_separate(self):
        bridge=c.scaled_bridge(tiny())
        for arm in ('adamw','lion'):
            logits,others=c.optimizer_pair(bridge,arm)
            ids=lambda opt:{id(p) for g in opt.param_groups for p in g['params']}
            self.assertFalse(ids(logits)&ids(others))
            self.assertEqual(logits.param_groups[0]['lr'],1e-4)
            self.assertEqual(others.param_groups[0]['lr'],1e-5)


class LionTests(unittest.TestCase):
    def test_two_steps_match_sign_and_single_momentum_formula(self):
        p=torch.nn.Parameter(torch.tensor([1.,-2.]));opt=c.CoordinateLion([p],lr=.1)
        expected=p.detach().clone();momentum=torch.zeros_like(p)
        for g in (torch.tensor([2.,-3.]),torch.tensor([-4.,1.])):
            expected-=.1*(.9*momentum+.1*g).sign();momentum=.95*momentum+.05*g
            p.grad=g;opt.step()
            torch.testing.assert_close(p,expected,rtol=0,atol=0)
            torch.testing.assert_close(opt.state[p]['momentum'],momentum)
        self.assertEqual(set(opt.state[p]),{'momentum'})

    def test_none_gradient_and_closure(self):
        p=torch.nn.Parameter(torch.tensor([1.]));opt=c.CoordinateLion([p],lr=.1)
        opt.step();self.assertEqual(len(opt.state),0)
        def closure():
            loss=p.square().sum();loss.backward();return loss
        value=opt.step(closure)
        self.assertEqual(float(value.detach()),1.);self.assertAlmostEqual(float(p.detach()),.9,places=6)

    def test_invalid_later_gradient_rejected_before_any_update(self):
        p=torch.nn.Parameter(torch.tensor([1.]));q=torch.nn.Parameter(torch.tensor([2.]))
        opt=c.CoordinateLion([p,q],lr=.1);p.grad=torch.ones_like(p);q.grad=torch.full_like(q,math.nan)
        with self.assertRaises((ValueError,FloatingPointError)):opt.step()
        self.assertEqual(float(p.detach()),1.);self.assertEqual(float(q.detach()),2.);self.assertEqual(len(opt.state),0)

    def test_sparse_later_gradient_rejected_before_any_update(self):
        p=torch.nn.Parameter(torch.tensor([1.]));q=torch.nn.Parameter(torch.tensor([2.]))
        opt=c.CoordinateLion([p,q],lr=.1);p.grad=torch.ones_like(p)
        q.grad=torch.sparse_coo_tensor(torch.tensor([[0]]),torch.tensor([1.]),(1,))
        with self.assertRaises(ValueError):opt.step()
        self.assertEqual(float(p.detach()),1.);self.assertEqual(len(opt.state),0)

    def test_scaled_margin_can_cross_in_controlled_256_steps(self):
        # A constructed constant-gradient mechanism test, not real model learning.
        raw=torch.nn.Parameter(torch.tensor([4.6]));scaled=torch.nn.Parameter(torch.tensor([4.6/200]))
        a=c.CoordinateLion([raw],lr=1e-4);b=c.CoordinateLion([scaled],lr=1e-4)
        for _ in range(256):
            raw.grad=torch.ones_like(raw);scaled.grad=torch.ones_like(scaled);a.step();b.step()
        self.assertGreater(float(raw.detach()),0);self.assertLess(float(scaled.detach()),0)


if __name__=='__main__':unittest.main()
