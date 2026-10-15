#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
import torch
from scripts import p070b_cla_routes as routes
from scripts import test_p070b_cla_routes as prior
SEED=0
OBSERVATIONS={}


def model(checkpoint=False):
    torch.manual_seed(1337)
    cfg=prior.config(2,checkpoint)
    result=routes.FixedRouteTransformer(cfg,'shuffle',2,route_seed=SEED)
    result.set_anneal(1.);return result


class Nonidentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(1)

    def test_declared_seed_differs_from_uniform_and_reverse(self):
        m=model();actual=m.visit_schedule();uniform=routes.schedule(m.cfg,m.owner,'uniform',2);reverse=routes.schedule(m.cfg,m.owner,'reverse',2)
        self.assertNotEqual(actual,uniform);self.assertNotEqual(actual,reverse)
        OBSERVATIONS.update(route_seed=SEED,actual_route=actual,uniform_route=uniform,reverse_route=reverse,
            nonidentity=True,route_sha256=m.route_sha256,visits=len(actual),kv_entries=m.route_trace['kv_entries'])

    def test_nonidentity_cache_full_decode_parity(self):
        m=model();m.eval();m.freeze_quant();x=torch.tensor([[3,2,9,6,5,7,13,10]])
        with torch.no_grad():
            full=m(x);first,past=m(x[:,:3],use_cache=True);parts=[first]
            for i in range(3,8):
                current,past=m(x[:,i:i+1],past_kv=past,use_cache=True);parts.append(current)
            decoded=torch.cat(parts,dim=1)
        self.assertTrue(torch.allclose(full,decoded,atol=prior.ATOL,rtol=prior.RTOL))
        self.assertEqual(len(past),9);self.assertTrue(all(k.shape[2]==8 for k,v in past.values()))
        OBSERVATIONS['cache_max_abs']=float((full-decoded).abs().max());m.clear_quant()

    def test_checkpoint_gradient_agrees_for_actual_shuffled_path(self):
        a=model(False);b=model(True);b.load_state_dict(a.state_dict());x=torch.tensor([[2,9,4,5,1,6]])
        la=a(x);lb=b(x);self.assertTrue(torch.equal(la,lb));la.square().mean().backward();lb.square().mean().backward()
        maximum=0.;count=0
        for pa,pb in zip(a.parameters(),b.parameters()):
            if pa.grad is None or pb.grad is None:self.assertIs(pa.grad,None);self.assertIs(pb.grad,None);continue
            self.assertTrue(bool(torch.isfinite(pa.grad).all()));self.assertTrue(torch.allclose(pa.grad,pb.grad,atol=prior.ATOL,rtol=prior.RTOL))
            maximum=max(maximum,float((pa.grad-pb.grad).abs().max()));count+=1
        OBSERVATIONS.update(gradient_parameter_tensors=count,checkpoint_gradient_max_abs=maximum)

    def test_actual_shuffled_future_causality(self):
        m=model();m.eval();a=torch.tensor([[1,2,3,4,5,6,7,8]]);b=a.clone();b[:,4:]+=20
        with torch.no_grad():left=m(a);right=m(b)
        delta=float((left[:,:4]-right[:,:4]).abs().max())
        self.assertTrue(torch.allclose(left[:,:4],right[:,:4],atol=prior.ATOL,rtol=prior.RTOL));OBSERVATIONS['future_prefix_max_abs']=delta

    def test_frozen_train_eval_path_and_wrong_cache_rejection(self):
        m=model();path=m.visit_schedule();m.eval();self.assertEqual(path,m.visit_schedule())
        with torch.no_grad():out,past=m(torch.tensor([[1,2]]),use_cache=True)
        m.set_route(routes.schedule(m.cfg,m.owner,'uniform',2))
        with self.assertRaisesRegex(ValueError,'route changed'):m(torch.tensor([[3]]),past_kv=past,use_cache=True)


if __name__=='__main__':unittest.main()
