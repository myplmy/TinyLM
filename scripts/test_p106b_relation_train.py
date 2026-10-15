#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import json
import subprocess
import unittest
import torch
from scripts import diag_p106b_relation_train as d


class Runtime(unittest.TestCase):
    def test_parent_prelocked_and_new_checkpoint_names(self):
        self.assertEqual(d.course.PARENT_SHA,'B1484726ACF786AF6B65F8A94AF66A0E8D192897BFF3553B9EE2A7EF11559515')
        paths=[d.checkpoint(a,e) for a in d.ARMS for e in (None,1,2,3)]
        self.assertEqual(len(set(paths)),8);self.assertNotIn(d.course.PARENT,paths)

    def test_view_and_exposure_arithmetic(self):
        self.assertEqual((16384+1536+4096)//128*4,688)
        self.assertEqual(688*8192,5636096)
        self.assertEqual(16384*4,65536);self.assertEqual(16384*7,114688)

    def test_all_objectives_use_whole_update_denominators(self):
        torch.manual_seed(12);w=torch.nn.Parameter(torch.randn(4));v=torch.nn.Parameter(w.detach().clone())
        x=torch.randn(7,4);native=torch.randn(5,4)
        word_weights=torch.tensor([1.,2.,1.,1.,3.,1.,1.])
        binary_idx={0,4};fact_idx={1,2,5}
        def backward(p,parts):
            for ids in parts:
                score=x[ids]@p
                word=(score.square()*word_weights[ids]).sum()
                binary=sum((score[j]-1).square() for j,i in enumerate(ids.tolist()) if i in binary_idx) if any(i in binary_idx for i in ids.tolist()) else score.sum()*0
                fact=sum((score[j]+1).square() for j,i in enumerate(ids.tolist()) if i in fact_idx) if any(i in fact_idx for i in ids.tolist()) else score.sum()*0
                d.normalize(word,10,binary,2,fact,3,1.).backward()
            ((native@p).square().sum()/5).backward()
        backward(w,[torch.arange(7)]);backward(v,[torch.arange(3),torch.arange(3,5),torch.arange(5,7)])
        self.assertTrue(torch.allclose(w.grad,v.grad,atol=2e-6,rtol=1e-5))

    def test_zero_fact_weight_cannot_modify_selector(self):
        from scripts import test_p106b_relation_auxiliary as fixture
        h,y,s,l=fixture.fixture();head=d.fact.new_head(8,rank=4);initial={n:p.detach().clone() for n,p in head.named_parameters()}
        value,n,q,c=d.fact.auxiliary_sum(head,h,y,s,l);(value*0).backward()
        self.assertTrue(all(float(p.grad.abs().sum())==0 for p in head.parameters()));self.assertEqual(d.head_delta(head,initial),0.)

    def test_real_cli_check_only_creates_no_data_or_model(self):
        before=(d.course.CORPUS.parent.exists(),d.course.EVIDENCE.exists())
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(d.__file__)),'--mode','cost','--arm','fact1','--check-only'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout.split('] ',1)[1]);self.assertEqual(r['updates'],688)
        self.assertEqual(before,(d.course.CORPUS.parent.exists(),d.course.EVIDENCE.exists()))


if __name__=='__main__':unittest.main()
