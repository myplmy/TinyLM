import copy
import math
import unittest
import torch
from scripts import p106b_alm_logtail as stable
from scripts import p106b_gsq_coordinates as coordinates
from scripts.test_p106b_gsq_objective import tiny,data
from tinylm.train import alm


class LogTailContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(1)

    def test_moderate_loss_and_gradient_match_original_formula(self):
        z=torch.tensor([[.2,-.3,.8],[1.,.1,-.7]],dtype=torch.float64,requires_grad=True)
        y=torch.tensor([1,0]);teacher=torch.tensor([-.02,-.03],dtype=torch.float64)
        ordinary=torch.nn.functional.cross_entropy(z,y,reduction='none')
        original=alm.binary_kl_logq(-ordinary/100.,teacher).sum()
        s,b=stable.student_log_pair(stable.log_nll_from_logits(z,y)-math.log(100.))
        current=stable.binary_kl_logpair(s,b,teacher).sum()
        torch.testing.assert_close(current,original,atol=1e-13,rtol=1e-12)
        a,=torch.autograd.grad(original,z,retain_graph=True);c,=torch.autograd.grad(current,z)
        torch.testing.assert_close(a,c,atol=1e-13,rtol=1e-11)

    def test_finite_margin100_and1000_recover_tail_without_probability_clip(self):
        teacher=torch.tensor([-.01],dtype=torch.float64)
        for margin in (100.,1000.):
            z=torch.tensor([[margin,0.]],dtype=torch.float64,requires_grad=True);y=torch.tensor([0])
            ordinary=torch.nn.functional.cross_entropy(z,y,reduction='none')
            self.assertEqual(float(ordinary.detach()),0.)
            with self.assertRaises(alm.StudentProbabilityBoundary):alm.binary_kl_logq(-ordinary/100,teacher)
            s,b=stable.student_log_pair(stable.log_nll_from_logits(z,y)-math.log(100.))
            loss=stable.binary_kl_logpair(s,b,teacher).sum();gradient,=torch.autograd.grad(loss,z)
            expected=torch.exp(teacher)*teacher+(-torch.expm1(teacher))*(alm.log1mexp(teacher)+margin+math.log(100.))
            torch.testing.assert_close(loss,expected.sum(),atol=1e-12,rtol=1e-12)
            self.assertAlmostEqual(float(gradient[0,0]),1-math.exp(-.01),places=12)
            self.assertTrue(bool(torch.isfinite(gradient).all()))

    def test_teacher_one_masks_undefined_negative_term(self):
        loga=torch.tensor([-1000.,0.,3.],dtype=torch.float64,requires_grad=True)
        s,b=stable.student_log_pair(loga);loss=stable.binary_kl_logpair(s,b,torch.zeros_like(s))
        torch.testing.assert_close(loss,torch.exp(loga))
        loss.sum().backward();self.assertTrue(bool(torch.isfinite(loga.grad).all()))

    def test_multitoken_chunk_sum_and_original_validation(self):
        nll=torch.tensor([[1.,2.,0.]],requires_grad=True);logn=torch.tensor([[0.,math.log(2.),-1000.]],requires_grad=True)
        mask=torch.ones(1,3,dtype=torch.bool);chunks=[dict(row=0,positions=[0,1],teacher_logprob=-4.)]
        a,count,_=stable.chunk_kl(nll,logn,mask,chunks)
        b,_=alm.chunk_kl(nll,mask,chunks)
        torch.testing.assert_close(a,b,atol=1e-9,rtol=1e-7);self.assertEqual(count,1)
        with self.assertRaises(ValueError):stable.chunk_kl(nll,logn,mask,chunks*2)
        with self.assertRaises(ValueError):stable.chunk_kl(nll,logn,torch.zeros_like(mask),chunks)

    def test_nonfinite_logits_and_invalid_teacher_are_rejected(self):
        for x in (math.inf,math.nan):
            with self.assertRaises(ValueError):stable.log_nll_from_logits(torch.tensor([[x,0.]]),torch.tensor([0]))
        with self.assertRaises(ValueError):stable.log_nll_from_logits(torch.ones(1,1),torch.tensor([0]))
        with self.assertRaises(ValueError):stable.binary_kl_logpair(torch.tensor([-.1]),torch.tensor([-.2]),torch.tensor([.1]))
        with self.assertRaises(ValueError):stable.binary_kl_logpair(torch.tensor([-.1]),torch.tensor([-.2]),torch.tensor([-.1]))

    def test_masked_positions_have_zero_nll_and_no_head_call(self):
        class NoHead:
            def _head_logits(self,_):raise AssertionError('masked head should not run')
        h=torch.ones(1,3,2,requires_grad=True);y=torch.full((1,3),-100)
        nll,logn,mask=stable.target_dual(NoHead(),h,y)
        self.assertFalse(bool(mask.any()));(nll.sum()+logn.sum()).backward()
        self.assertTrue(torch.equal(h.grad,torch.zeros_like(h)))

    def test_real_gsq_layer_and_head_checkpoint_preserve_finite_gradients(self):
        results=[];x,y,chunks=data()
        for cp in (False,True):
            model=tiny(cp).train();bridge=coordinates.scaled_bridge(model)
            with bridge.installed(),bridge.realization(614):
                h=model(x,return_hidden=True);nll,logn,mask=stable.target_dual(model,h,y,chunk=1)
                kl,count,_=stable.chunk_kl(nll,logn,mask,chunks)
                loss=alm.normalized_loss(nll.sum(),int(mask.sum()),kl,count,weight=1.)
                bridge.backward(loss)
            gradients={k:p.grad.clone() for k,p in bridge.banks.named_parameters()}
            self.assertTrue(all(bool(torch.isfinite(g).all()) for g in gradients.values()))
            results.append((loss.detach(),gradients))
        torch.testing.assert_close(results[0][0],results[1][0],atol=1e-7,rtol=1e-6)
        for key in results[0][1]:torch.testing.assert_close(results[0][1][key],results[1][1][key],atol=2e-6,rtol=2e-5)


if __name__=='__main__':unittest.main()
