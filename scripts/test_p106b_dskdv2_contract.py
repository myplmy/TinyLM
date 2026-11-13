import hashlib
import unittest
import torch
from torch.nn import functional as F
from scripts import p106b_dskdv2_contract as d


def spans(raw,lengths,*,ids=None,owners=None,supervised=None):
    result=[];cursor=0
    for i,n in enumerate(lengths):
        result.append(dict(raw_index=i,byte_start=cursor,byte_end=cursor+n,
            bytes_sha256=hashlib.sha256(raw[cursor:cursor+n]).hexdigest().upper(),special_kind=None,
            token_id=(ids or list(range(10,10+len(lengths))))[i],
            turn_id=(owners or [0]+[1]*(len(lengths)-1))[i],
            supervised=(supervised or [False]+[True]*(len(lengths)-1))[i]))
        cursor+=n
    return result


class ExactByteAlignment(unittest.TestCase):
    def test_different_ids_match_same_complete_bytes_and_single_shift(self):
        a=spans(b'abcd',[1,1,2]);b=spans(b'abcd',[1,1,2],ids=[90,91,92])
        pairs,holds=d.exact_pairs('abcd',a,b)
        self.assertEqual(len(pairs),2);self.assertEqual(holds,[])
        self.assertEqual([(r['student_predictor_raw_index'],r['teacher_predictor_raw_index']) for r in pairs],[(0,0),(1,1)])
        self.assertTrue(all(r['lookahead_bytes']==0 for r in pairs))

    def test_first_subtoken_and_nearest_boundary_do_not_count_as_exact(self):
        a=spans(b'abcd',[1,1,2]);b=spans(b'abcd',[1,2,1])
        pairs,holds=d.exact_pairs('abcd',a,b);self.assertEqual(pairs,[]);self.assertEqual(len(holds),2)

    def test_utf8_fragment_requires_the_same_raw_byte_prefix_not_replacement_text(self):
        raw='a한'.encode();a=spans(raw,[1,1,2]);b=spans(raw,[1,1,2],ids=[99,100,101])
        pairs,holds=d.exact_pairs('a한',a,b);self.assertEqual(len(pairs),2);self.assertEqual(holds,[])
        self.assertEqual(pairs[-1]['prefix_bytes'],2)

    def test_owner_mismatch_is_hold_and_modified_or_incomplete_source_is_error(self):
        a=spans(b'abc',[1,1,1]);b=spans(b'abc',[1,1,1],owners=[0,2,2])
        self.assertEqual(len(d.exact_pairs('abc',a,b)[1]),2)
        for text,other in [('abd',b),('abcd',b)]:
            with self.subTest(text=text),self.assertRaises(ValueError):d.exact_pairs(text,a,other)


class DualSpaceMath(unittest.TestCase):
    def setUp(self):torch.manual_seed(29);torch.set_num_threads(1)
    def fixtures(self,n=5):
        return [torch.randn(shape,dtype=torch.float64,requires_grad=True) for shape in
                [(n,3),(n,4),(3,7),(4,11),(4,3),(3,4)]]+[torch.arange(n)%7]
    def test_projector_initialization_matches_independent_lstsq_and_detaches(self):
        s=torch.randn(3,8,dtype=torch.float64,requires_grad=True);t=torch.randn(4,8,dtype=torch.float64,requires_grad=True)
        out=d.initialize_projectors(s,t)
        independent=torch.linalg.lstsq(s.T.detach(),t.T.detach(),driver='gelsd').solution.T
        torch.testing.assert_close(out['t2s'],independent,atol=1e-10,rtol=1e-9)
        self.assertFalse(out['t2s'].requires_grad);self.assertFalse(out['s2t'].requires_grad)
    def test_rank_deficient_head_reports_nonzero_unrecoverable_logit_error(self):
        s=torch.tensor([[1.,0.,0.],[2.,0.,0.]],dtype=torch.float64);t=torch.eye(3,dtype=torch.float64)
        out=d.initialize_projectors(s,t)
        self.assertEqual(out['stats']['student_overlap_rank'],1)
        self.assertGreater(out['stats']['t2s_relative_logit_error'],.5)
    def test_three_full_vocabulary_terms_match_independent_dense_oracle(self):
        hs,ht,ws,wt,pts,pst,labels=self.fixtures();out=d.dskd_sums(hs,ht,ws,wt,pts,pst,labels)
        tproj=ht.detach()@pts@ws.detach();sproj=hs@pst.detach()@wt.detach()
        kl=lambda a,b:F.kl_div(F.log_softmax(a,dim=-1),F.softmax(b.detach(),dim=-1),reduction='sum')
        expected=kl(hs@ws,tproj)+kl(sproj,ht.detach()@wt.detach())+F.cross_entropy(tproj,labels,reduction='sum')
        torch.testing.assert_close(out['total_sum'],expected,atol=1e-10,rtol=1e-10)
        self.assertEqual((out['student_vocab'],out['teacher_vocab']),(7,11))
    def test_projector_ce_only_updates_teacher_to_student_projector(self):
        args=self.fixtures();out=d.dskd_sums(*args);grads=torch.autograd.grad(out['projector_ce_sum'],args[:6],allow_unused=True)
        self.assertIsNotNone(grads[4]);self.assertGreater(float(grads[4].norm()),0.)
        self.assertTrue(all(x is None for i,x in enumerate(grads) if i!=4))
    def test_kd_terms_detach_teacher_projector_and_head_but_reach_student(self):
        args=self.fixtures();out=d.dskd_sums(*args);grads=torch.autograd.grad(out['student_kd_sum']+out['teacher_kd_sum'],args[:6],allow_unused=True)
        self.assertIsNotNone(grads[0]);self.assertIsNotNone(grads[2]);self.assertTrue(all(grads[i]is None for i in (1,3,4,5)))
    def test_chunk_sums_and_global_denominator_preserve_loss_and_every_live_gradient(self):
        args=self.fixtures(6);whole=d.normalized(d.dskd_sums(*args),global_positions=6)
        chunked=whole*0
        for a,b in ((0,2),(2,5),(5,6)):
            sliced=[args[0][a:b],args[1][a:b],*args[2:6],args[6][a:b]]
            chunked=chunked+d.normalized(d.dskd_sums(*sliced),global_positions=6)
        torch.testing.assert_close(whole,chunked,atol=1e-10,rtol=1e-10)
        g1=torch.autograd.grad(whole,[args[i] for i in (0,2,4)],retain_graph=True)
        g2=torch.autograd.grad(chunked,[args[i] for i in (0,2,4)])
        for a,b in zip(g1,g2):torch.testing.assert_close(a,b,atol=1e-10,rtol=1e-9)
    def test_extreme_finite_logits_do_not_need_probability_clipping(self):
        args=self.fixtures();args[2]=args[2]*1000;args[3]=args[3]*1000
        out=d.dskd_sums(*args);self.assertTrue(bool(torch.isfinite(out['total_sum'])))
        grads=torch.autograd.grad(out['total_sum'],[args[0],args[4]])
        self.assertTrue(all(bool(torch.isfinite(x).all()) for x in grads))
    def test_student_hidden_vjp_matches_finite_difference_with_frozen_teacher_targets(self):
        args=self.fixtures(2)
        fixed=[x.detach() for x in args[1:]]
        self.assertTrue(torch.autograd.gradcheck(lambda h:d.dskd_sums(h,*fixed)['total_sum'],
            (args[0],),eps=1e-6,atol=1e-5,rtol=1e-4))
    def test_invalid_denominator_shape_or_native_teacher_top1_mapping_is_rejected(self):
        args=self.fixtures();out=d.dskd_sums(*args)
        with self.assertRaises(ValueError):d.normalized(out,global_positions=4)
        args[-1]=torch.full((5,),7,dtype=torch.long)
        with self.assertRaises(ValueError):d.dskd_sums(*args)


if __name__=='__main__':unittest.main()
