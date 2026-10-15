#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
from collections import Counter
import random
import unittest
import torch
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer
from scripts import p070b_cla_routes as r
OBSERVATIONS={}
ATOL=1e-5
RTOL=1e-4


def config(repeats=2,checkpoint=False):
    return TMTConfig(vocab_size=67,dim=32,ffn_dim=64,n_q_heads=4,n_kv_heads=2,emb_rank=8,
        n_prelude=1,n_middle=8,n_coda=1,mlp_group=2,cla_group=2,micro_group=0,
        train_repeat=float(repeats),max_seq_len=32,grad_checkpoint=checkpoint,quantize_embedding=False)


def make(mode='uniform',repeats=2,checkpoint=False):
    torch.manual_seed(1337);model=r.FixedRouteTransformer(config(repeats,checkpoint),mode,repeats)
    model.set_anneal(1.);return model


class RouteContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(1)

    def test_uniform_matches_existing_schedule(self):
        model=make()
        self.assertEqual(model.visit_schedule(),model._repeat_schedule(2.))
        self.assertEqual(r.schedule(model.cfg,model.owner,repeats=1),list(range(10)))
        self.assertEqual(model.visit_schedule()[:2],[0,1]);self.assertEqual(model.visit_schedule()[-2:],[8,9])

    def test_atomic_modes_keep_multiset_and_boundary_fragments(self):
        model=make();base=model.visit_schedule()
        for mode in r.MODES:
            chosen=r.schedule(model.cfg,model.owner,mode,2)
            self.assertEqual(Counter(chosen),Counter(base));self.assertEqual(chosen[0],0);self.assertEqual(chosen[-1],9)
            self.assertEqual(chosen[1],1);self.assertEqual(chosen[8],8)
            self.assertEqual(r.trace(model.cfg,model.owner,chosen)['kv_entries'],9)

    def test_unsafe_layer_reverse_rejected(self):
        model=make();wrong=[0]+list(range(1,9))[::-1]*2+[9]
        with self.assertRaisesRegex(ValueError,'pinned|atomic|before KV owner|previous-cycle'):r.trace(model.cfg,model.owner,wrong)

    def test_interleaved_group_and_unpinned_fragments_rejected(self):
        model=make();wrong=model.visit_schedule();wrong[3],wrong[4]=wrong[4],wrong[3]
        with self.assertRaisesRegex(ValueError,'atomic'):r.trace(model.cfg,model.owner,wrong)
        wrong=model.visit_schedule();wrong[1],wrong[2]=wrong[2],wrong[1]
        with self.assertRaisesRegex(ValueError,'pinned'):r.trace(model.cfg,model.owner,wrong)

    def test_repeat_cfg_cannot_silently_claim_a_different_function(self):
        cfg=config(2)
        with self.assertRaisesRegex(ValueError,'matching train_repeat'):r.FixedRouteTransformer(cfg,repeats=3)
        model=make();before=(model.visit_schedule(),model.route_sha256,copy.deepcopy(model.route_trace))
        with self.assertRaisesRegex(ValueError,'differs from cfg'):model.set_route(r.schedule(model.cfg,model.owner,'uniform',1))
        self.assertEqual(before,(model.visit_schedule(),model.route_sha256,model.route_trace))

    def test_fixed_shuffle_preserves_global_rng_and_is_reproducible(self):
        model=make();before=random.getstate()
        orders=[r.schedule(model.cfg,model.owner,'shuffle',2,seed) for seed in range(10)]
        self.assertEqual(random.getstate(),before);self.assertGreater(len({tuple(x) for x in orders}),1)
        self.assertEqual(orders[3],r.schedule(model.cfg,model.owner,'shuffle',2,3))

    def test_random_maximum_draw_not_an_unimplemented_router_claim(self):
        before=random.getstate();values=[r.repeat_draw(3,1337,k) for k in range(40)]
        self.assertEqual(set(values),{1,2,3});self.assertEqual(before,random.getstate())
        self.assertEqual(values,[r.repeat_draw(3,1337,k) for k in range(40)])
        with self.assertRaises(ValueError):r.repeat_draw(0,1337,0)

    def test_uniform_logits_and_gradients_match_product_on_toy(self):
        model=make(checkpoint=True);base=TiedMLPTransformer(copy.deepcopy(model.cfg));base.load_state_dict(model.state_dict());base.set_anneal(1.)
        x=torch.tensor([[1,7,11,4,16,8]])
        a=model(x);b=base(x)
        self.assertTrue(torch.equal(a,b));a.square().mean().backward();b.square().mean().backward()
        grads=0
        for (na,pa),(nb,pb) in zip(model.named_parameters(),base.named_parameters()):
            self.assertEqual(na,nb)
            if pa.grad is None or pb.grad is None:self.assertIs(pa.grad,None);self.assertIs(pb.grad,None);continue
            self.assertTrue(torch.equal(pa.grad,pb.grad),na);self.assertTrue(bool(torch.isfinite(pa.grad).all()));grads+=1
        self.assertGreater(grads,0);OBSERVATIONS['uniform_gradient_parameter_tensors']=grads

    def test_all_fixed_routes_prefill_decode_cache_parity(self):
        records=[]
        for repeats,mode in ((1,'uniform'),(2,'uniform'),(3,'uniform'),(2,'reverse'),(2,'shuffle')):
            model=make(mode,repeats);model.eval();model.freeze_quant();ids=torch.tensor([[3,2,9,6,5,7,13,10]])
            with torch.no_grad():
                full=model(ids);first,past=model(ids[:,:3],use_cache=True);parts=[first]
                for t in range(3,8):
                    out,past=model(ids[:,t:t+1],past_kv=past,use_cache=True);parts.append(out)
                decoded=torch.cat(parts,dim=1)
            self.assertTrue(torch.allclose(full,decoded,atol=ATOL,rtol=RTOL),(repeats,mode,float((full-decoded).abs().max())))
            self.assertEqual(len(past),model.route_trace['kv_entries'])
            self.assertTrue(all(v[0].shape[2]==8 for v in past.values()))
            records.append(dict(repeats=repeats,mode=mode,visits=len(model.visit_schedule()),kv_entries=len(past),
                max_abs=float((full-decoded).abs().max()),route_sha256=model.route_sha256))
            model.clear_quant()
        OBSERVATIONS['cache_cases']=records

    def test_changed_future_tokens_do_not_change_prefix(self):
        model=make('reverse');model.eval();x=torch.tensor([[1,2,3,4,5,6,7,8]]);changed=x.clone();changed[:,4:]+=20
        with torch.no_grad():a=model(x);b=model(changed)
        self.assertTrue(torch.allclose(a[:,:4],b[:,:4],atol=ATOL,rtol=RTOL))
        OBSERVATIONS['future_prefix_max_abs']=float((a[:,:4]-b[:,:4]).abs().max())

    def test_cache_rejects_route_change(self):
        model=make();model.eval()
        with torch.no_grad():out,past=model(torch.tensor([[1,2,3]]),use_cache=True)
        model.set_route(r.schedule(model.cfg,model.owner,'reverse',2))
        with self.assertRaisesRegex(ValueError,'route changed'):model(torch.tensor([[4]]),past_kv=past,use_cache=True)
        with self.assertRaisesRegex(ValueError,'unbound cache'):model(torch.tensor([[4]]),past_kv=dict(past),use_cache=True)

    def test_no_extra_weights_or_silent_optional_features(self):
        model=make();base=TiedMLPTransformer(copy.deepcopy(model.cfg))
        self.assertEqual(set(base.state_dict()),set(model.state_dict()))
        cfg=config();cfg.mtp_aux=True
        with self.assertRaisesRegex(ValueError,'MTP excluded'):r.FixedRouteTransformer(cfg)


if __name__=='__main__':unittest.main()
