"""Synthetic CPU layout/RNG/denominator checks, without a native model."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT)not in sys.path:sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from tinylm.train.context_curriculum import ContextPlan,ContextCursor,split_update
from tinylm.train.context_micro_tokens import MicroTokensCursor,regroup_update,layout_summary,parse_context_plan,_sha


class Sampler:
    def __init__(self,seed=17,*,scratch=False):
        self.bs=2;self.seq=16;self.rng=np.random.default_rng(seed);self.calls=0
        self.scratch=torch.empty((2,17),dtype=torch.long)if scratch else None
    def __call__(self):
        ix=self.rng.integers(0,1000,self.bs)
        value=torch.from_numpy(ix[:,None]+np.arange(self.seq+1))
        if self.scratch is not None:self.scratch.copy_(value);value=self.scratch
        self.calls+=1
        return value[:,:-1],value[:,1:]


def plan():return ContextPlan(((1,4),(2,8),(3,16)),micro_bs=2,base_accum=2,full_length=16)
def source():
    sampler=Sampler()
    return tuple(sampler()for _ in range(2))
def flat(update):return [(x[i],y[i])for x,y in update.batches for i in range(x.shape[0])]


class LayoutContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_initialized():raise ValueError('CPU layout CUDA initialization forbidden')
    def test_explicit_integer_stage_parser_keeps_full_horizon_and_batch_contract(self):
        parsed=parse_context_plan(' 1:4, 2:8,3:16 ',micro_bs=2,accum=2,seq=16,steps=3)
        self.assertEqual(parsed,plan())
        self.assertEqual(parsed.tokens_per_update,64)
    def test_stage_parser_rejects_malformed_lengths_and_changed_training_horizon(self):
        for text in('', '1:4,2:8', '1:4,2:3,3:16', '1.0:4,3:16', '1:4,3:16,', '1:8,2:4,3:16'):
            with self.assertRaises(ValueError):parse_context_plan(text,micro_bs=2,accum=2,seq=16,steps=3)
        with self.assertRaises(ValueError):parse_context_plan('1:16',micro_bs=2,accum=2,seq=16,steps=True)
    def test_every_same_short_row_target_and_origin_is_retained_once(self):
        p=plan();raw=source()
        for length in(4,8,16):
            old=split_update(raw,p,length);new=regroup_update(raw,p,length)
            self.assertEqual(new.origins,old.origins)
            self.assertEqual(len(new.batches),p.base_accum)
            self.assertEqual(new.accounting['active_micro_tokens'],32)
            self.assertEqual(new.accounting['ntp_targets'],64)
            counts=torch.zeros((2,2,16),dtype=torch.int64)
            for (x,y),reference,origin in zip(flat(new),flat(old),new.origins):
                self.assertTrue(torch.equal(x,reference[0]));self.assertTrue(torch.equal(y,reference[1]))
                draw,row,start,end=origin;counts[draw,row,start:end]+=1
                self.assertTrue(torch.equal(y,raw[draw][1][row,start:end]))
            self.assertTrue(torch.equal(counts,torch.ones_like(counts)))
    def test_same_M_300m_summary_distinguishes_forward_calls_from_draw_tokens(self):
        p=ContextPlan(((458,256),(916,512),(2289,1024)))
        result=layout_summary(p);rows=result['stages']
        self.assertEqual([r['active_micro_bs']for r in rows],[32,16,8])
        self.assertEqual([r['active_accum']for r in rows],[16,16,16])
        self.assertEqual([r['reference_split_accum']for r in rows],[64,32,16])
        self.assertEqual([r['active_micro_tokens']for r in rows],[8192]*3)
        self.assertEqual(sum(r['draw_tokens']for r in rows),300023808)
        self.assertEqual(sum(r['source_calls']for r in rows),2289*16)
        self.assertFalse(result['quality_claim']);self.assertFalse(result['measured_model_speed'])
    def test_standard_shapes_preserve_all393216_positions_and48_source_calls(self):
        p=ContextPlan(((1,256),(2,512),(3,1024)))
        sampler,oracle=Sampler(),Sampler()
        sampler.bs=oracle.bs=8;sampler.seq=oracle.seq=1024
        cursor=MicroTokensCursor(p,sampler,source_sha256='A'*64)
        checked=0
        for update in range(3):
            actual=cursor.prepare();raw=tuple(oracle()for _ in range(16))
            self.assertEqual(len(actual.batches),16)
            self.assertEqual(actual.accounting['active_micro_tokens'],8192)
            self.assertEqual(actual.accounting['ntp_targets'],131072)
            counts=torch.zeros((16,8,1024),dtype=torch.uint8)
            for(x,y),(draw,row,start,end)in zip(flat(actual),actual.origins):
                self.assertTrue(torch.equal(x,raw[draw][0][row,start:end]))
                self.assertTrue(torch.equal(y,raw[draw][1][row,start:end]))
                counts[draw,row,start:end]+=1;checked+=end-start
            self.assertTrue(torch.equal(counts,torch.ones_like(counts)))
            cursor.finish(optimizer_applied=False)
            self.assertEqual(sampler.rng.bit_generator.state,oracle.rng.bit_generator.state)
        self.assertEqual((checked,sampler.calls,oracle.calls,cursor.optimizer_updates),(393216,48,48,0))
    def test_full_length_keeps_the_original_noncontiguous_tensor_objects(self):
        raw=source();self.assertFalse(raw[0][0].is_contiguous())
        result=regroup_update(raw,plan(),16)
        for pair,original in zip(result.batches,raw):
            self.assertIs(pair[0],original[0]);self.assertIs(pair[1],original[1])
        self.assertEqual(result.accounting['additional_regroup_copy_bytes'],0)
    def test_short_copy_accounting_is_additional_not_total_model_memory(self):
        for length in(4,8):
            result=regroup_update(source(),plan(),length)
            self.assertEqual(result.accounting['additional_regroup_copy_bytes'],2*64*8)
            self.assertTrue(result.accounting['old_split_and_snapshot_cost_not_omitted'])
            self.assertTrue(all(x.is_contiguous()and y.is_contiguous()for x,y in result.batches))
    def test_source_calls_PCG64_and_skipped_optimizer_accounting_match(self):
        sampler,oracle=Sampler(),Sampler()
        cursor=MicroTokensCursor(plan(),sampler,source_sha256='A'*64)
        for update in range(3):
            result=cursor.prepare();raw=tuple(oracle()for _ in range(2))
            expected=regroup_update(raw,plan(),(4,8,16)[update],update=update)
            self.assertTrue(all(torch.equal(a,b)for x,y in zip(result.batches,expected.batches)for a,b in zip(x,y)))
            row=cursor.finish(optimizer_applied=update!=1)
            self.assertEqual(row['active_micro_batches'],2)
            self.assertEqual(sampler.rng.bit_generator.state,oracle.rng.bit_generator.state)
        self.assertEqual((sampler.calls,cursor.next_update,cursor.optimizer_updates),(6,3,2))
        with self.assertRaises(StopIteration):cursor.prepare()
        self.assertEqual(sampler.calls,6)
    def test_JSON_roundtrip_restores_every_next_position_without_mutating_saved_state(self):
        first=MicroTokensCursor(plan(),Sampler(),source_sha256='A'*64)
        first.prepare();first.finish(optimizer_applied=True)
        saved=json.loads(json.dumps(first.state_dict()));before=deepcopy(saved)
        second=MicroTokensCursor(plan(),Sampler(99),source_sha256='A'*64)
        second.load_state_dict(saved)
        for _ in range(2):
            a,b=first.prepare(),second.prepare()
            self.assertEqual(a.origins,b.origins)
            for x,y in zip(a.batches,b.batches):
                self.assertTrue(all(torch.equal(aa,bb)for aa,bb in zip(x,y)))
            first.finish(optimizer_applied=True);second.finish(optimizer_applied=True)
        self.assertEqual(saved,before);self.assertEqual(first.state_dict(),second.state_dict())
    def test_fixed_mode_source_wrong_layout_and_midupdate_resume_are_rejected(self):
        fixed=ContextCursor(plan(),Sampler(),source_sha256='A'*64)
        cursor=MicroTokensCursor(plan(),Sampler(),source_sha256='A'*64)
        with self.assertRaises(ValueError):cursor.load_state_dict(fixed.state_dict())
        with self.assertRaises(ValueError):fixed.load_state_dict(cursor.state_dict())
        bad=cursor.state_dict();bad['layout']='FIXED_MICRO';bad.pop('state_sha256');bad['state_sha256']=_sha(bad)
        with self.assertRaises(ValueError):cursor.load_state_dict(bad)
        wrong=MicroTokensCursor(plan(),Sampler(),source_sha256='B'*64)
        with self.assertRaises(ValueError):wrong.load_state_dict(cursor.state_dict())
        cursor.prepare()
        with self.assertRaises(RuntimeError):cursor.state_dict()
        with self.assertRaises(RuntimeError):cursor.load_state_dict(fixed.state_dict())
    def test_original_shift_mask_dtype_and_partial_input_refusals_are_preserved(self):
        for kind in('shift','mask','dtype','shape'):
            raw=list(source());x,y=[t.clone()for t in raw[0]]
            if kind=='shift':y[0,0]+=1
            elif kind=='mask':y[0,0]=-100
            elif kind=='dtype':x=x.int()
            else:x,y=x[:,:-1],y[:,:-1]
            raw[0]=(x,y)
            with self.assertRaises(ValueError):regroup_update(tuple(raw),plan(),4)
    def test_reused_source_scratch_is_snapshotted_before_next_draw(self):
        sampler,oracle=Sampler(scratch=True),Sampler()
        cursor=MicroTokensCursor(plan(),sampler,source_sha256='A'*64)
        actual=cursor.prepare();expected=regroup_update(tuple(oracle()for _ in range(2)),plan(),4)
        for a,b in zip(actual.batches,expected.batches):
            self.assertTrue(all(torch.equal(x,y)for x,y in zip(a,b)))
        cursor.finish(optimizer_applied=True)
    def test_global_CE_denominator_matches_independent_context_free_gradient(self):
        raw=tuple((x%32,y%32)for x,y in source())
        values=torch.sin(torch.arange(32*32,dtype=torch.float64).reshape(32,32)*.17)
        reference=None
        for length in(4,8,16):
            for builder in(split_update,regroup_update):
                weight=values.clone().requires_grad_();total=0.
                for x,y in builder(raw,plan(),length).batches:
                    loss=torch.nn.functional.cross_entropy(weight[x].reshape(-1,32),y.reshape(-1),reduction='sum')/64
                    loss.backward();total+=float(loss.detach())
                if reference is None:reference=(total,weight.grad.clone())
                else:
                    self.assertAlmostEqual(total,reference[0],places=12)
                    self.assertTrue(torch.allclose(weight.grad,reference[1],atol=1e-12,rtol=1e-10))


if __name__=='__main__':unittest.main()
