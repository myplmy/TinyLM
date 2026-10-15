#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import subprocess
import unittest
import torch
from scripts import diag_p106b_original_qa3_train as t


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
        paths=[t.checkpoint(arm,e) for arm in t.course.ARMS for e in (None,1,2,3)]
        self.assertEqual(len(set(paths)),8);self.assertNotIn(t.course.PARENT,paths)
        self.assertEqual(t.course.PARENT_SHA,'687EBCC5E30EA674EF4742BFC2BA6B98BCAB937541BD5498F567A9084387E831')

    def test_explicit_batch_schedule_and_objectives(self):
        r=t.info();self.assertEqual((r['micro_bs'],r['accum'],r['epochs'],r['updates']),(8,16,4,200))
        self.assertFalse(r['student_mtp']);self.assertFalse(r['fact_head_updated']);self.assertEqual(r['fact_weight'],0.)

    def test_cli_check_only_no_namespace_created(self):
        before=(t.course.CORPUS.parent.exists(),t.course.EVIDENCE.exists())
        p=subprocess.run([sys.executable,'-B','-X','utf8',t.__file__,'--mode','cost','--arm','three','--check-only'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(p.returncode,0,p.stderr);self.assertIn('ORIGINAL_QA3',p.stdout)
        self.assertEqual(before,(t.course.CORPUS.parent.exists(),t.course.EVIDENCE.exists()))


if __name__=='__main__':unittest.main()
