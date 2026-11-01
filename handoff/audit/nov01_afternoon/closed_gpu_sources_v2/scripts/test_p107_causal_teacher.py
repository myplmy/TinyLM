"""Independent same-vocabulary causal KL, masks, gradients and frozen teacher."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import tinylm
import copy
import unittest
import torch
import torch.nn.functional as F
from tinylm.train.causal_teacher import CausalTeacherKL
from tinylm.train.hybrid_mntp import causal_batch,mntp_batch,uniform_mntp_selection,objective_mean
from scripts.test_p107_adaptive_training import ToyAttention

torch.set_num_threads(1)


def fixture():
    torch.manual_seed(7)
    student=ToyAttention();teacher=ToyAttention().eval().requires_grad_(False)
    tokens=torch.arange(35,45).repeat(2,1)
    docs=torch.tensor([0,0,0,0,0,1,1,1,-1,-1]).repeat(2,1)
    batch=causal_batch(tokens,docs,vocab_size=64)
    kd=CausalTeacherKL(teacher,vocab_size=64,student_tokenizer_sha256='A'*64,
        teacher_tokenizer_sha256='A'*64,teacher_identity_sha256='B'*64,chunk_rows=3)
    kd.bind_student(student,64)
    return student,teacher,batch,kd


class CausalTeacherTests(unittest.TestCase):
    def test_loss_matches_independent_double_formula_and_teacher_unchanged(self):
        student,teacher,batch,kd=fixture();student.eval()
        before=copy.deepcopy(teacher.state_dict())
        logits=student(batch.inputs,attention_mask=batch.attention_mask)
        ce,count=objective_mean(logits,batch.targets)
        result,metrics=kd.loss(logits,batch,ce)
        valid=batch.targets!=-100
        with torch.no_grad():t=teacher(batch.inputs,attention_mask=batch.attention_mask)[valid].double()
        s=logits[valid].double()
        p=t.softmax(-1)
        exact=(p*(p.log()-s.log_softmax(-1))).sum(-1).mean()
        self.assertAlmostEqual(metrics['kl'],float(exact.detach()),places=6)
        self.assertAlmostEqual(float(result.detach()),float((ce+.1*exact).detach()),places=6)
        self.assertEqual(metrics['targets'],count)
        result.backward()
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in student.parameters()))
        self.assertTrue(all(p.grad is None for p in teacher.parameters()))
        for key,value in before.items():self.assertTrue(torch.equal(value,teacher.state_dict()[key]))

    def test_ignored_targets_do_not_enter_kl(self):
        student,_,batch,kd=fixture();student.eval()
        logits=student(batch.inputs,attention_mask=batch.attention_mask)
        ce,_=objective_mean(logits,batch.targets)
        _,before=kd.loss(logits,batch,ce)
        changed=logits.detach().clone();changed[batch.targets==-100]=torch.randn_like(changed[batch.targets==-100])*100
        _,after=kd.loss(changed,batch,ce)
        self.assertEqual(before['kl'],after['kl'])

    def test_mntp_never_calls_teacher(self):
        _,teacher,batch,kd=fixture()
        tokens=torch.arange(35,45).repeat(2,1);docs=torch.zeros_like(tokens)
        selected=uniform_mntp_selection(tokens,docs,vocab_size=64,probability=.5,generator=torch.Generator().manual_seed(1))
        masked=mntp_batch(tokens,docs,selected,vocab_size=64)
        with self.assertRaises(ValueError):kd.loss(torch.zeros(2,9,64),masked,torch.tensor(1.))

    def test_shared_parameters_or_tokenizer_mismatch_refused(self):
        _,teacher,_,kd=fixture()
        with self.assertRaises(ValueError):kd.bind_student(teacher,64)
        with self.assertRaises(ValueError):
            CausalTeacherKL(teacher,vocab_size=64,student_tokenizer_sha256='A'*64,
                teacher_tokenizer_sha256='C'*64,teacher_identity_sha256='B'*64)

    def test_training_teacher_refused(self):
        _,teacher,_,kd=fixture();teacher.train()
        with self.assertRaises(ValueError):kd.bind_student(ToyAttention(),64)

    def test_distinct_parameter_with_shared_storage_refused(self):
        student,teacher,_,_=fixture()
        teacher.embedding.weight=torch.nn.Parameter(student.embedding.weight.detach(),requires_grad=False)
        kd=CausalTeacherKL(teacher,vocab_size=64,student_tokenizer_sha256='A'*64,
            teacher_tokenizer_sha256='A'*64,teacher_identity_sha256='B'*64)
        with self.assertRaises(ValueError):kd.bind_student(student,64)

    def test_future_visible_mask_refused(self):
        from dataclasses import replace
        _,_,batch,kd=fixture()
        future=replace(batch,attention_mask=torch.ones_like(batch.attention_mask))
        with self.assertRaises(ValueError):kd.loss(torch.zeros(2,9,64),future,torch.tensor(1.))


if __name__=='__main__':unittest.main()
