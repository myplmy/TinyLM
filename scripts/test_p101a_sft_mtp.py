#!/usr/bin/env python3
"""Synthetic CPU only: assistant MTP, unchanged main state and greedy verification."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import torch
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer
from tinylm.train import mtp_sft as core
from tinylm.infer.generate import sample


def tiny(aux=False):
    torch.manual_seed(17)
    cfg=TMTConfig(vocab_size=31,dim=16,ffn_dim=32,n_prelude=1,n_middle=2,n_coda=1,
        n_q_heads=4,n_kv_heads=2,emb_rank=8,max_seq_len=32,tie_mlp=False,
        micro_group=4,mlp_group=2,cla_group=1,
        mtp_aux=aux,mtp_horizons=(2,3,4))
    model=TiedMLPTransformer(cfg)
    return model,cfg


class Tokens:
    def encode(self,text):return type('Encoded',(),{'ids':[1,2]})()
    def decode(self,ids):return ','.join(map(str,ids))
    def token_to_id(self,name):return 30


class Contracts(unittest.TestCase):
    def test_mask_does_not_cross_role_or_turn(self):
        y=torch.tensor([[-100,4,5,6,7,-100,8,9]])
        s=torch.tensor([[0,1,1,1,2,0,3,3]])
        target,valid=core.horizon_targets(y,s,2)
        self.assertEqual(target.tolist(),[[-100,5,6,-100,-100,-100,9]])
        self.assertEqual(int(valid.sum()),3)

    def test_padding_empty_horizon(self):
        y=torch.tensor([[1,-100]]);s=torch.tensor([[1,0]])
        self.assertEqual(core.horizon_targets(y,s,4)[0].numel(),0)

    def test_list_denominator_matches_tensor(self):
        row=core.Record([0]*8,[-100,4,5,6,7,-100,8,9],[0,1,1,1,2,0,3,3])
        _,y,s=core.pad_records([row],0)
        counts=core.count_record(row)
        self.assertEqual(counts,{h:int(core.horizon_targets(y,s,h)[1].sum()) for h in (1,2,3,4)})

    def test_main_state_and_rng_unchanged(self):
        baseline,_=tiny(False);model,cfg=tiny(True)
        for key,value in baseline.state_dict().items():
            self.assertTrue(torch.equal(value,model.state_dict()[key]),key)
        before=torch.get_rng_state().clone();model.attach_mtp_heads((2,3))
        self.assertTrue(torch.equal(before,torch.get_rng_state()))
        self.assertNotIn('mtp_up4',model.state_dict())

    def test_head_memory_drop_and_strict_export(self):
        model,cfg=tiny(True);model.eval()
        self.assertEqual(model.mtp_head_bytes(),3*16*8*4)
        original=model(torch.tensor([[1,2,3]]))
        keep=model.mtp_deployment_payload(keep_aux=True,horizons=(2,3))
        kept=TiedMLPTransformer(TMTConfig(**keep['cfg']));kept.load_state_dict(keep['model'],strict=True);kept.eval()
        drop=model.mtp_deployment_payload();model.detach_mtp_heads()
        self.assertEqual(model.mtp_head_bytes(),0)
        self.assertTrue(torch.equal(original,model(torch.tensor([[1,2,3]]))))
        self.assertFalse(drop['cfg']['mtp_aux'])

    def test_gradient_and_chunk_alignment(self):
        model,_=tiny(True)
        x=torch.tensor([[1,2,3,4,5,6]]);y=torch.tensor([[-100,3,4,5,6,7]])
        s=torch.tensor([[0,1,1,1,1,1]])
        hidden=model(x,return_hidden=True)
        sums,counts=core.components(model,hidden,y,s,chunk=3,checkpoint_heads=False)
        loss=core.normalized_loss(sums,counts,{2:.1,3:.1,4:.1});loss.backward()
        self.assertTrue(torch.isfinite(loss))
        self.assertEqual(counts,{1:5,2:4,3:3,4:2})
        for h in (2,3,4):self.assertGreater(float(getattr(model,f'mtp_up{h}').grad.abs().sum()),0)

    def test_checkpoint_head_gradient_same(self):
        x=torch.tensor([[1,2,3,4,5,6]]);y=torch.tensor([[-100,3,4,5,6,7]])
        s=torch.tensor([[0,1,1,1,1,1]])
        gradients=[]
        for checkpoint in (False,True):
            model,_=tiny(True);hidden=model(x,return_hidden=True)
            sums,counts=core.components(model,hidden,y,s,chunk=3,checkpoint_heads=checkpoint)
            core.normalized_loss(sums,counts,{2:.1,3:.1,4:.1}).backward()
            gradients.append({n:p.grad.clone() for n,p in model.named_parameters() if p.grad is not None})
        for key in gradients[0]:self.assertTrue(torch.allclose(gradients[0][key],gradients[1][key],atol=1e-6,rtol=1e-5),key)

    def test_greedy_verified_matches_native(self):
        model,cfg=tiny(True);model.eval();tok=Tokens()
        for cache in (False,True):
            expected=sample(model,cfg,tok,'x',max_new=8,temperature=0.,use_cache=cache,stop_at_eos=False)
            for k in (2,3,4):
                measured=sample(model,cfg,tok,'x',max_new=8,temperature=0.,use_cache=cache,
                    stop_at_eos=False,mtp_tokens=k)
                self.assertEqual(measured,expected,(cache,k))

    def test_sampling_not_silently_lossy(self):
        model,cfg=tiny(True);model.eval()
        with self.assertRaisesRegex(ValueError,'greedy'):
            sample(model,cfg,Tokens(),'x',temperature=.8,mtp_tokens=2)

    def test_memory_formula(self):
        self.assertEqual([core.projection_memory(768,256,k)['tensor_mib'] for k in (2,3,4)],[.75,1.5,2.25])
        self.assertEqual(core.projection_memory(768,256,4,2)['tensor_mib'],1.125)

    def test_fp16_hotplug_and_main_preservation(self):
        model,cfg=tiny(True);model.eval();x=torch.tensor([[1,2,3]])
        before=model(x).clone();saved={'mtp_up2':model.mtp_up2.detach().half()}
        model.detach_mtp_heads();model.attach_mtp_heads((2,),saved)
        self.assertEqual(model.mtp_head_bytes(),16*8*2)
        self.assertTrue(torch.equal(before,model(x)))

    def test_pad_is_not_data_mass(self):
        rec=core.Record([1,2,3],[2,3,4],[1,1,1])
        x,y,s=core.pad_records([rec],0,fixed_width=8,batch_size=4)
        self.assertEqual(tuple(x.shape),(4,8))
        self.assertEqual(int(y.ne(-100).sum()),3)
        self.assertEqual(int(core.horizon_targets(y,s,2)[1].sum()),2)

    def test_bad_draft_rebuilds_cache(self):
        model,cfg=tiny(True);model.eval();tok=Tokens()
        expected=sample(model,cfg,tok,'x',max_new=9,temperature=0.,stop_at_eos=False)
        bad=(int(expected.split(',')[-1])+1)%31
        def wrong(hidden,h):
            value=torch.full((*hidden.shape[:-1],31),-100.)
            value[...,bad]=100.;return value
        with patch.object(model,'mtp_aux_logits',side_effect=wrong):
            actual,meta=sample(model,cfg,tok,'x',max_new=9,temperature=0.,stop_at_eos=False,
                mtp_tokens=4,return_metadata=True)
        self.assertEqual(actual,expected)
        self.assertGreater(meta['mtp']['cache_rebuilds'],0)

    def test_opt_in_verified_modes_preserve_native_and_rejection_prefix(self):
        model,cfg=tiny(True);model.eval();tok=Tokens()
        expected=sample(model,cfg,tok,'x',max_new=9,temperature=0.,stop_at_eos=False)
        def wrong(hidden,h):
            value=torch.full((*hidden.shape[:-1],31),-100.)
            value[...,0]=100.;return value
        for cache in (False,True):
            for mode in ('parallel_rebuild','parallel_truncate','serial_truncate'):
                with patch.object(model,'mtp_aux_logits',side_effect=wrong):
                    actual,meta=sample(model,cfg,tok,'x',max_new=9,temperature=0.,
                        use_cache=cache,stop_at_eos=False,mtp_tokens=4,
                        mtp_verify_mode=mode,return_metadata=True)
                self.assertEqual(actual,expected,(cache,mode))
                self.assertEqual(meta['mtp']['verification_mode'],mode)
                if mode!='parallel_rebuild':self.assertEqual(meta['mtp']['cache_rebuilds'],0)
                if cache and mode=='parallel_truncate':
                    self.assertGreater(meta['mtp']['cache_truncations'],0)

    def test_opt_in_modes_stop_and_cla_repeat_cache(self):
        for cla,repeat in ((1,1.),(2,2.)):
            model,cfg=tiny(True);cfg.cla_group=cla;cfg.train_repeat=repeat
            torch.manual_seed(17);model=TiedMLPTransformer(cfg);model.eval();tok=Tokens()
            native=sample(model,cfg,tok,'x',max_new=7,temperature=0.,stop_at_eos=False)
            stop=[int(t) for t in native.split(',')[3:5]]
            expected=sample(model,cfg,tok,'x',max_new=7,temperature=0.,stop_at_eos=False,
                return_metadata=True,stop_token_sequences=[stop])
            for mode in ('parallel_truncate','serial_truncate'):
                actual=sample(model,cfg,tok,'x',max_new=7,temperature=0.,stop_at_eos=False,
                    return_metadata=True,stop_token_sequences=[stop],mtp_tokens=4,mtp_verify_mode=mode)
                self.assertEqual(actual[0],expected[0],(cla,repeat,mode))
                self.assertEqual(actual[1]['generated_tokens'],expected[1]['generated_tokens'])

    def test_verify_mode_validation(self):
        model,cfg=tiny(True);model.eval()
        with self.assertRaisesRegex(ValueError,'verification mode'):
            sample(model,cfg,Tokens(),'x',temperature=0.,mtp_tokens=2,mtp_verify_mode='guess')

    def test_stop_sequence_and_max_new(self):
        model,cfg=tiny(True);model.eval();tok=Tokens()
        full=sample(model,cfg,tok,'x',max_new=8,temperature=0.,stop_at_eos=False)
        stop=[int(x) for x in full.split(',')[3:5]]
        expected=sample(model,cfg,tok,'x',max_new=8,temperature=0.,stop_at_eos=False,
            return_metadata=True,stop_token_sequences=[stop])
        actual=sample(model,cfg,tok,'x',max_new=8,temperature=0.,stop_at_eos=False,
            return_metadata=True,stop_token_sequences=[stop],mtp_tokens=4)
        self.assertEqual(actual[0],expected[0]);self.assertEqual(actual[1]['finish_reason'],'STOP_SEQUENCE')
        self.assertEqual(actual[1]['generated_tokens'],expected[1]['generated_tokens'])

    def test_turn_owner_encoding(self):
        from tinylm.data.prepare import SyntheticTokenizer
        row={'messages':[{'role':'user','content':'첫 질문'},{'role':'assistant','content':'첫 답'},
            {'role':'user','content':'다음 질문'},{'role':'assistant','content':'다음 답'}]}
        record=core.encode_record(row,SyntheticTokenizer())
        self.assertEqual(set(s for s in record.segments if s),{1,2})
        _,y,s=core.pad_records([record],0)
        target,valid=core.horizon_targets(y,s,4)
        self.assertFalse(bool((target[valid]==-100).any()))

    def test_optimizer_owns_every_new_head(self):
        from scripts.diag_p101a_sft_mtp import optimizers
        model,_=tiny(True)
        adam,muon=optimizers(model)
        all_ids=[id(p) for opt in (adam,muon) for g in opt.param_groups for p in g['params']]
        self.assertEqual(len(all_ids),len(set(all_ids)))
        for h in (2,3,4):self.assertIn(id(getattr(model,f'mtp_up{h}')),all_ids)

    def test_accumulated_gradient_matches_combined_update(self):
        records=[core.Record([1,2,3,4],[2,3,4,5],[1,1,1,1]),
                 core.Record([2,3,4],[-100,4,5],[0,2,2])]
        denominators={h:sum(core.count_record(r)[h] for r in records) for h in (1,2,3,4)}
        weights={2:.1,3:.1,4:.1};gradients=[]
        for groups in ([records],[[r] for r in records]):
            model,_=tiny(True)
            for group in groups:
                x,y,s=core.pad_records(group,0,fixed_width=4)
                hidden=model(x,return_hidden=True)
                sums,_=core.components(model,hidden,y,s,checkpoint_heads=False)
                core.normalized_loss(sums,denominators,weights).backward()
            gradients.append({n:p.grad.clone() for n,p in model.named_parameters() if p.grad is not None})
        for key in gradients[0]:self.assertTrue(torch.allclose(gradients[0][key],gradients[1][key],atol=2e-6,rtol=1e-5),key)

    def test_eos_is_never_skipped_by_draft(self):
        model,cfg=tiny(True);model.eval();tok=Tokens()
        first=sample(model,cfg,tok,'x',max_new=1,temperature=0.,stop_at_eos=False)
        eos=int(first.split(',')[-1])
        expected=sample(model,cfg,tok,'x',max_new=8,temperature=0.,eos_id=eos,return_metadata=True)
        for k in (2,3,4):
            actual=sample(model,cfg,tok,'x',max_new=8,temperature=0.,eos_id=eos,
                return_metadata=True,mtp_tokens=k)
            self.assertEqual(actual[0],expected[0]);self.assertEqual(actual[1]['finish_reason'],'EOS')
            self.assertEqual(actual[1]['generated_tokens'],1)

    def test_multi_query_cache_matches_single_query_cla(self):
        for cla in (1,2):
            _,cfg=tiny(True);cfg.cla_group=cla
            torch.manual_seed(17);model=TiedMLPTransformer(cfg);model.eval()
            prefix=torch.tensor([[1,2,3]]);suffix=torch.tensor([[4,5,6]])
            with torch.no_grad():
                _,past=model(prefix,use_cache=True)
                batched,_=model(suffix,past_kv=past,use_cache=True)
                _,past=model(prefix,use_cache=True)
                values=[]
                for i in range(3):
                    logits,past=model(suffix[:,i:i+1],past_kv=past,use_cache=True)
                    values.append(logits)
            self.assertTrue(torch.allclose(batched,torch.cat(values,1),atol=1e-6,rtol=1e-5),cla)

    def test_checkpoint_head_load_policies(self):
        import tempfile
        from tinylm.infer.generate import load_model
        model,_=tiny(True)
        with tempfile.TemporaryDirectory(prefix='p101a_mtp_fixture_') as directory:
            path=Path(directory)/'synthetic.pt'
            torch.save(model.mtp_deployment_payload(keep_aux=True),path)
            dropped,_,_=load_model(ckpt_path=path,device='cpu',mtp_heads='off')
            self.assertEqual(dropped.mtp_head_bytes(),0)
            selected,cfg,_=load_model(ckpt_path=path,device='cpu',mtp_heads=3)
            self.assertEqual(cfg.mtp_horizons,(2,3))
            self.assertNotIn('mtp_up4',selected.state_dict())
            for key,value in dropped.state_dict().items():self.assertTrue(torch.equal(value,selected.state_dict()[key]))


if __name__=='__main__':
    torch.set_num_threads(1)
    result=unittest.main(exit=False).result
    if not result.wasSuccessful():raise SystemExit(1)
    print('[CPU_SFT_MTP_PASS] assistant-turn/horizon gradients; head drop/main unchanged; greedy verification; model/GPU quality NOT_RUN')
