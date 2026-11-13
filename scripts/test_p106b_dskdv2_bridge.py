import unittest
import torch
from scripts import p106b_dskdv2_bridge as b
from scripts import p106b_dskdv2_contract as reference


class NativeBridgeContracts(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1);torch.manual_seed(1337)
        self.hs=torch.randn(7,3,dtype=torch.float64,requires_grad=True)
        self.ht=torch.randn(7,4,dtype=torch.float64,requires_grad=True)
        self.up=torch.randn(3,2,dtype=torch.float64,requires_grad=True)
        self.emb=torch.randn(9,2,dtype=torch.float64,requires_grad=True)
        self.wt=torch.randn(11,4,dtype=torch.float64,requires_grad=True)
        self.pt=torch.randn(4,3,dtype=torch.float64,requires_grad=True)
        self.ps=torch.randn(3,4,dtype=torch.float64,requires_grad=True)
        self.labels=torch.tensor([0,1,2,3,4,5,6])
    def parts(self,start=0,end=7,**kwargs):
        return b.native_sums(self.hs[start:end],self.ht[start:end],self.up,self.emb,self.wt,self.pt,self.ps,self.labels[start:end],**kwargs)
    def test_native_factored_losses_and_vjps_match_independent_dense_reference(self):
        actual=self.parts();dense=reference.dskd_sums(self.hs,self.ht,self.up@self.emb.T,self.wt.T,self.pt,self.ps,self.labels)
        for k in ['student_kd_sum','teacher_kd_sum','projector_ce_sum','total_sum']:
            torch.testing.assert_close(actual[k],dense[k],atol=1e-10,rtol=1e-10)
        args=[self.hs,self.up,self.emb,self.pt]
        a=torch.autograd.grad(actual['total_sum'],args,retain_graph=True)
        c=torch.autograd.grad(dense['total_sum'],args,retain_graph=True)
        for left,right in zip(a,c):torch.testing.assert_close(left,right,atol=1e-10,rtol=1e-10)
    def test_teacher_hidden_head_and_reverse_projector_have_no_gradients_and_projector_ce_does(self):
        parts=self.parts();g=torch.autograd.grad(parts['total_sum'],[self.ht,self.wt,self.ps,self.pt],allow_unused=True,retain_graph=True)
        self.assertTrue(all(x is None for x in g[:3]));self.assertGreater(float(g[3].norm()),0)
        self.assertIsNone(torch.autograd.grad(parts['student_kd_sum'],self.pt,allow_unused=True)[0])
    def test_fixed_head_scatter_gather_preserves_unsorted_position_order_and_vjp(self):
        h=self.ht[:3];indices=torch.tensor([7,2,4]);actual=b.teacher_logits(h,self.wt,indices=indices,width=9)
        direct=torch.nn.functional.linear(h,self.wt)
        torch.testing.assert_close(actual,direct,atol=1e-10,rtol=1e-10)
        a=torch.autograd.grad(actual.square().sum(),h,retain_graph=True)[0]
        c=torch.autograd.grad(direct.square().sum(),h)[0];torch.testing.assert_close(a,c,atol=1e-10,rtol=1e-10)
    def test_duplicate_or_out_of_frame_original_teacher_indices_are_rejected(self):
        for indices in [torch.tensor([1,1,2]),torch.tensor([1,2,9])]:
            with self.assertRaises(ValueError):b.teacher_logits(self.ht[:3],self.wt,indices=indices,width=9)
    def test_chunked_global_denominator_preserves_whole_loss_and_hidden_gradient(self):
        whole=reference.normalized(self.parts(),global_positions=7)
        chunks=sum(reference.normalized(self.parts(start,min(start+3,7)),global_positions=7)for start in range(0,7,3))
        torch.testing.assert_close(whole,chunks,atol=1e-10,rtol=1e-10)
        a=torch.autograd.grad(whole,self.hs,retain_graph=True)[0];c=torch.autograd.grad(chunks,self.hs)[0]
        torch.testing.assert_close(a,c,atol=1e-10,rtol=1e-10)
    def test_wrong_complete_token_labels_fail_closed(self):
        bad=self.labels.clone();bad[-1]=9
        with self.assertRaises(ValueError):b.native_sums(self.hs,self.ht,self.up,self.emb,self.wt,self.pt,self.ps,bad)


if __name__=='__main__':unittest.main()
