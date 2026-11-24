"""CMA scalar oracle, explicit next-target ownership and full-update gradients."""
from __future__ import annotations

import math
import unittest

from scripts import p106b_dwa_cma as core


def fixture():
    import torch
    torch.manual_seed(37)
    make=lambda n,d:torch.randn(n,d,dtype=torch.float64,requires_grad=True)
    student=core.NativeView(make(2,3),make(2,3),make(2,3),torch.tensor([0,2]),(1,4),(2,5))
    teacher=core.NativeView(make(3,4),make(3,4),make(3,4),torch.tensor([1,2,0]),(0,3,5),(1,4,6))
    projects=dict(query=torch.nn.Linear(6,8,bias=False).double(),
        t2s=torch.nn.Linear(4,3,bias=False).double(),s2t=torch.nn.Linear(3,4,bias=False).double(),
        embedding_t2s=torch.nn.Linear(4,3,bias=False).double(),
        student_head=torch.nn.Parameter(torch.randn(5,3,dtype=torch.float64)),
        teacher_head=torch.nn.Parameter(torch.randn(7,4,dtype=torch.float64)))
    return torch,student,teacher,projects


def logits(student,teacher,projects):
    return student.hidden@projects['student_head'].T,teacher.hidden@projects['teacher_head'].T


class CMACoreContracts(unittest.TestCase):
    def test_next_target_gather_keeps_disjoint_assistant_positions(self):
        import torch
        embedding=torch.nn.Embedding(10,3)
        hidden=torch.arange(18,dtype=torch.float32).reshape(6,3)
        view=core.native_next_view(torch,[0,1,2,3,4,5],[False,False,True,True,False,True],hidden,embedding)
        self.assertEqual(view.prediction_positions,(1,2,4))
        self.assertEqual(view.target_positions,(2,3,5))
        self.assertEqual(view.targets.tolist(),[2,3,5])
        self.assertTrue(torch.equal(view.hidden,hidden[[1,2,4]]))
        self.assertFalse(torch.equal(view.hidden,hidden[:3]))

    def test_ignored_padding_is_not_an_extra_ce_or_prefix_row(self):
        import torch
        embedding=torch.nn.Embedding(10,3)
        hidden=torch.arange(18,dtype=torch.float32).reshape(6,3)
        ids,mask=[0,1,2,3,4,5],[False,False,True,True,False,True]
        first=core.native_next_view(torch,ids,mask,hidden,embedding)
        second=core.native_next_view(torch,ids+[0,0],mask+[False,False],torch.cat((hidden,torch.zeros(2,3))),embedding)
        self.assertEqual(first.target_positions,second.target_positions)
        self.assertTrue(torch.equal(first.hidden,second.hidden))
        self.assertTrue(torch.equal(first.target_embeddings,second.target_embeddings))

    def test_empty_supervision_is_hold(self):
        import torch
        with self.assertRaisesRegex(core.AdmissionHold,'no original next-target'):
            core.native_next_view(torch,[1,2],[False,False],torch.ones(2,3),torch.nn.Embedding(4,3))

    def test_cma_attention_matches_independent_scalar_std_and_nested_dot_products(self):
        torch,student,teacher,projects=fixture()
        actual=core.cross_model_attention(torch,student,teacher,**{k:v for k,v in projects.items() if k!='embedding_t2s'})
        sx=torch.cat((student.input_embeddings,student.target_embeddings),-1).detach().tolist()
        tx=torch.cat((teacher.input_embeddings,teacher.target_embeddings),-1).detach().tolist()
        weights=projects['query'].weight.detach().tolist()
        flat=[v for row in tx for v in row];mean=sum(flat)/len(flat)
        scale=math.sqrt(sum((v-mean)**2 for v in flat)/(len(flat)-1))
        queries=[[sum(w*v for w,v in zip(row,source)) for row in weights] for source in sx]
        keys=[[v/scale for v in row] for row in tx]
        scores=[[sum(q*k for q,k in zip(query,key))/math.sqrt(8) for key in keys] for query in queries]
        def softmax(row):
            exps=[math.exp(v-max(row)) for v in row]
            return [v/sum(exps) for v in exps]
        expected=torch.tensor([softmax(row) for row in scores],dtype=torch.float64)
        reverse=torch.tensor([softmax(list(row)) for row in zip(*scores)],dtype=torch.float64)
        self.assertTrue(torch.allclose(actual['attention'],expected,atol=1e-12,rtol=1e-12))
        self.assertTrue(torch.allclose(actual['reverse_attention'],reverse,atol=1e-12,rtol=1e-12))

    def test_zero_scalar_std_is_not_silently_replaced(self):
        import torch
        with self.assertRaisesRegex(core.AdmissionHold,'zero mass'):
            core.scalar_std_normalize(torch,torch.ones(2,3))

    def test_confidence_is_applied_after_entropy_normalization(self):
        torch,student,teacher,projects=fixture()
        sl,tl=logits(student,teacher,projects)
        packet=core.loss_components(torch,student,teacher,sl,tl,**projects,kd_gate_scale=1.)
        entropy_weight=packet['student_entropy_weight']
        effective=entropy_weight*packet['student_confidence_gate']
        self.assertAlmostEqual(float(entropy_weight.sum()),2.,places=8)
        self.assertLess(float(effective.sum()),1.999)
        self.assertFalse(entropy_weight.requires_grad)
        self.assertFalse(packet['student_confidence_gate'].requires_grad)

    def test_uniform_teacher_is_explicit_hold(self):
        import torch
        with self.assertRaisesRegex(core.AdmissionHold,'zero weight mass'):
            core.source_token_weights(torch,torch.randn(2,5),torch.zeros(3,7))

    def test_auxiliary_ce_does_not_update_native_heads_or_detached_embeddings(self):
        torch,student,teacher,projects=fixture()
        cma=core.cross_model_attention(torch,student,teacher,**{k:v for k,v in projects.items() if k!='embedding_t2s'})
        torch.nn.functional.cross_entropy(cma['student_logits'],student.targets,reduction='sum').backward()
        self.assertIsNone(projects['student_head'].grad)
        self.assertIsNone(projects['teacher_head'].grad)
        self.assertIsNone(student.input_embeddings.grad)
        self.assertIsNone(student.target_embeddings.grad)
        self.assertIsNone(teacher.hidden.grad)
        self.assertIsNone(teacher.target_embeddings.grad)
        self.assertGreater(float(projects['query'].weight.grad.abs().sum()),0.)
        self.assertGreater(float(projects['t2s'].weight.grad.abs().sum()),0.)

    def test_auxiliary_query_gradient_matches_independent_finite_difference(self):
        torch,student,teacher,projects=fixture()
        def objective():
            cma=core.cross_model_attention(torch,student,teacher,**{k:v for k,v in projects.items() if k!='embedding_t2s'})
            return torch.nn.functional.cross_entropy(cma['student_logits'],student.targets,reduction='sum')
        objective().backward()
        parameter=projects['query'].weight
        automatic=float(parameter.grad[0,0]);before=parameter.detach().clone();step=1e-5
        with torch.no_grad():
            parameter[0,0]=before[0,0]+step;plus=float(objective())
            parameter[0,0]=before[0,0]-step;minus=float(objective())
            parameter.copy_(before)
        numerical=(plus-minus)/(2*step)
        self.assertAlmostEqual(automatic,numerical,places=7)
        self.assertTrue(torch.equal(parameter.detach(),before))

    def test_source_zero_based_band_does_not_reuse_old_one_based_coordinates(self):
        import torch
        from scripts.p106b_dwa_reference import adaptive_band_cost
        cost=torch.zeros(2,4,dtype=torch.float64);attention=torch.full((2,4),.25,dtype=torch.float64)
        current=core.source_band_cost(torch,cost,attention,alpha=0.,base=0.,entropy_scale=0.,penalty=1.)
        old=adaptive_band_cost(cost,attention,alpha=0.,base=0.,entropy_scale=0.,penalty=1.)
        self.assertEqual(current.tolist(),[[0.,1.,1.,1.],[1.,1.,0.,1.]])
        self.assertFalse(torch.equal(current,old))

    def test_both_representation_losses_share_hidden_projection_and_keep_teacher_frozen(self):
        torch,student,teacher,projects=fixture()
        from scripts.p106b_dwa_reference import soft_dtw
        sl,tl=logits(student,teacher,projects)
        packet=core.loss_components(torch,student,teacher,sl,tl,**projects,kd_gate_scale=1.,
            dtw=lambda cost:soft_dtw(cost,gamma=.1,max_cells=64),
            band=dict(alpha=.7,base=5.,entropy_scale=2.,penalty=1.))
        loss=core.update_loss([packet],global_student_targets=2)
        loss.backward()
        self.assertTrue(bool(torch.isfinite(loss)))
        for name in ('query','t2s','s2t','embedding_t2s'):
            gradient=projects[name].weight.grad
            self.assertIsNotNone(gradient,name)
            self.assertTrue(bool(torch.isfinite(gradient).all()),name)
        self.assertIsNotNone(student.hidden.grad)
        self.assertIsNotNone(student.target_embeddings.grad)
        self.assertIsNone(teacher.hidden.grad)
        self.assertIsNone(teacher.target_embeddings.grad)
        self.assertIsNone(projects['teacher_head'].grad)
        self.assertTrue(bool(torch.isfinite(projects['student_head'].grad).all()))

    def test_unequal_microbatches_use_one_actual_update_denominator(self):
        def packet(count,total):
            return dict(student_count=count,raw=dict(student_ce=total,projector_ce=0.,student_kd=0.,
                teacher_kd=0.,dtw_hidden=0.,dtw_embedding=0.))
        packets=[packet(2,2.),packet(3,9.)]
        self.assertEqual(core.update_loss(packets,global_student_targets=5),2.2)
        self.assertNotEqual(core.update_loss(packets,global_student_targets=5),2./2+9./3)
        with self.assertRaisesRegex(core.AdmissionHold,'target accounting'):
            core.update_loss(packets,global_student_targets=4)


if __name__=='__main__':unittest.main()
