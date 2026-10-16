#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import subprocess
import unittest
import torch
from scripts import diag_p106b_repair_role_train as t


class Runtime(unittest.TestCase):
    def test_word_binary_and_native_gradient_accumulation(self):
        torch.manual_seed(7);a=torch.nn.Parameter(torch.randn(3));b=torch.nn.Parameter(a.detach().clone());x=torch.randn(7,3);native=torch.randn(4,3)
        weights=torch.tensor([1.,2.,1.,3.,1.,1.,1.]);known={0,4}
        def backward(p,parts):
            for ids in parts:
                pred=x[ids]@p;word=(pred.square()*weights[ids]).sum();binary=sum((pred[j]-1).square() for j,i in enumerate(ids.tolist()) if i in known) if any(i in known for i in ids.tolist()) else pred.sum()*0
                t.loss_sum(word,10,binary,2).backward()
            ((native@p).square().sum()/4).backward()
        backward(a,[torch.arange(7)]);backward(b,[torch.arange(3),torch.arange(3,7)])
        self.assertTrue(torch.allclose(a.grad,b.grad,atol=2e-6,rtol=1e-5))

    def test_new_checkpoints_and_common_fixed_parent(self):
        paths=[t.checkpoint(arm) for arm in t.course.ARMS]
        self.assertEqual(len(set(paths)),4);self.assertNotIn(t.course.PARENT,paths)
        self.assertEqual(t.course.PARENT_SHA,'567D379E3F8F1B8BBE1F65303DE9AAF1D1F3A33AFE5F9EA51CD12EE06069F9AF')

    def test_explicit_batch_schedule_and_objectives(self):
        r=t.info();self.assertEqual((r['micro_bs'],r['accum'],r['epochs'],r['updates']),(8,16,4,216))
        self.assertFalse(r['student_mtp']);self.assertFalse(r['fact_head_updated']);self.assertEqual(r['fact_weight'],0.)

    def test_train_and_dev_use_original_producer_signature(self):
        import inspect
        self.assertIn('course.conversation_signature',inspect.getsource(t.run))
        self.assertIn('course.conversation_signature',inspect.getsource(t.evaluate_loss))
        self.assertNotIn('course.factory.sha',inspect.getsource(t.run))

    def test_cli_check_only_no_namespace_created(self):
        before=(t.course.CORPUS.parent.exists(),t.course.EVIDENCE.exists())
        p=subprocess.run([sys.executable,'-B','-X','utf8',t.__file__,'--mode','cost','--arm','repair_role','--check-only'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(p.returncode,0,p.stderr);self.assertIn('REPAIR_ROLE',p.stdout)
        self.assertEqual(before,(t.course.CORPUS.parent.exists(),t.course.EVIDENCE.exists()))


if __name__=='__main__':unittest.main()
