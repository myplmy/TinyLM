#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import unittest
import copy
import json
import subprocess
from scripts import diag_p106b_dualqa_curriculum as d


class Runtime(unittest.TestCase):
    def test_parent_and_main_settings_explicit(self):
        self.assertEqual(d.TAG,'p106b_dualqa_curriculum_v1_s1337')
        self.assertEqual(d.producer.PARENT_SHA,'180104A965CAA84379802D9862A74B59895537EB8B8905DA6E0AA84293E91337')
        self.assertEqual(d.data.ARMS,('repeat','contrast'))

    def test_new_checkpoint_names_do_not_alias_parent(self):
        paths=[d.checkpoint(a,e) for a in d.data.ARMS for e in (None,1,2,3)]
        self.assertEqual(len(paths),len(set(paths)));self.assertNotIn(d.producer.PARENT,paths)

    def test_exact_whole_update_exposure_math(self):
        self.assertEqual(4*(1536+4096)//128,176)
        self.assertEqual(176*8192,1441792)
        self.assertEqual(4*3072,12288)

    def test_code_auxiliary_never_reads_future_teacher_labels(self):
        from scripts import test_p106b_dualqa_course as fixture
        fixture.Course.setUpClass();row=fixture.Course().student()
        self.assertIsNone(d.data.binding.binding_bit(row,{}))

    def test_check_only_is_a_real_nonloading_cli(self):
        before=(d.CORPUS.parent.exists(),d.EVIDENCE.exists())
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(d.__file__)),
            '--mode','cost','--arm','contrast','--check-only'],cwd=ROOT,text=True,capture_output=True,timeout=30)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout.split('] ',1)[1])['expected_updates'],176)
        self.assertEqual(before,(d.CORPUS.parent.exists(),d.EVIDENCE.exists()))

    def test_whole_update_gradient_matches_micro_accumulation(self):
        import torch
        torch.manual_seed(47)
        body=torch.nn.Linear(3,4);word=torch.nn.Linear(4,5);head=torch.nn.Linear(4,2)
        modules=torch.nn.ModuleList([body,word,head]);other=copy.deepcopy(modules)
        x=torch.randn(7,3);gold=torch.tensor([1,2,3,4,0,2,1]);bits=torch.tensor([0,1,0])
        indices=torch.tensor([0,3,6]);native=torch.randn(5,3);ng=torch.tensor([0,4,3,2,1])
        def loss(m,parts):
            for ids in parts:
                hidden=m[0](x[ids]);ws=torch.nn.functional.cross_entropy(m[1](hidden),gold[ids],reduction='sum')
                selected=[(p,int((indices==idx).nonzero()[0])) for p,idx in enumerate(ids.tolist()) if bool((indices==idx).any())]
                extra=(torch.nn.functional.cross_entropy(m[2](hidden[[a for a,b in selected]]),
                    bits[[b for a,b in selected]],reduction='sum') if selected else hidden.sum()*0)
                d.sft_objective(ws,7,extra,3).backward()
            nh=m[0](native);(torch.nn.functional.cross_entropy(m[1](nh),ng,reduction='sum')/5).backward()
        loss(modules,[torch.arange(7)]);loss(other,[torch.arange(2),torch.arange(2,5),torch.arange(5,7)])
        for p,q in zip(modules.parameters(),other.parameters()):
            self.assertTrue(torch.allclose(p.grad,q.grad,atol=2e-7,rtol=2e-6))

    def test_unknown_source_has_zero_auxiliary_gradient(self):
        import torch
        head=d.data.binding.new_head(4);hidden=torch.randn(2,6,4,requires_grad=True)
        y=torch.full((2,6),-100);y[:,4:]=1
        value,n,correct,events=d.data.binding.suffix_auxiliary_sum(head,hidden,y,[None,None],[None,None],dense=True)
        self.assertEqual((n,correct,events),(0,0,0));value.backward()
        self.assertEqual(float(hidden.grad.abs().sum()),0.)
        self.assertTrue(all(float(p.grad.abs().sum())==0. for p in head.parameters()))

    def test_known_auxiliary_rejects_future_positions(self):
        import torch
        head=d.data.binding.new_head(4);hidden=torch.randn(1,6,4);y=torch.full((1,6),-100);y[:,3:]=1
        with self.assertRaisesRegex(ValueError,'never later'):
            d.data.binding.suffix_auxiliary_sum(head,hidden,y,[0],[[2,3,4]],dense=True)

    def test_zero_head_preserves_cpu_rng(self):
        import torch
        before=torch.random.get_rng_state().clone();head=d.data.binding.new_head(4)
        self.assertTrue(torch.equal(before,torch.random.get_rng_state()))
        self.assertEqual(sum(float(p.detach().abs().sum()) for p in head.parameters()),0.)


if __name__=='__main__':unittest.main()
