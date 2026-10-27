#!/usr/bin/env python3
"""Full-position CPU contract and optional optimizer-free actual-model F+B cost."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
from unittest.mock import patch
import weakref

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_resource_matrix as resource
from tinylm.train.context_curriculum import ContextCursor,ContextPlan,snapshot_batches,split_update

TAG='p013_context_windows_v1_20261027'
SCHEMA='P013_FULL_WINDOW_CONTEXT_CONTRACT_AND_FB_COST_V1'
CAPS={'contract':120,'cost':900}
ORDER=(1024,256,512,512,256,1024)
OWN=('tinylm/train/context_curriculum.py','scripts/test_p013_context_curriculum.py',
     'scripts/diag_p013_context_curriculum.py','scripts/test_p013_context_driver.py')
need=resource.need


def identity():
    files=dict(resource.identity()['files'])
    files.update({name:resource.digest(resource.safe(name)) for name in OWN})
    return dict(files=files,sha256=resource.sha(files))


class WindowFixture:
    """Position fixture, NOT text/corpus. Only start selection consumes RNG."""
    def __init__(self,*,seed=1337,device='cpu'):
        import numpy as np
        self.rng=np.random.default_rng(seed)
        self.bs,self.seq,self.calls,self.device=8,1024,0,device

    def __call__(self):
        import numpy as np
        import torch
        starts=self.rng.integers(0,2**42,self.bs)
        values=((starts[:,None]+7919*np.arange(self.seq+1))%(32768-8)+8).astype(np.int64)
        t=torch.from_numpy(values).to(self.device)
        self.calls+=1
        return t[:,:-1],t[:,1:]


def tensor_pairs_sha(pairs):
    h=hashlib.sha256()
    for pair in pairs:
        for value in pair:
            h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest().upper()


def run_contract(budget):
    import torch
    plan=ContextPlan(((2,256),(4,512),(6,1024)))
    fixture_sha=resource.sha(dict(source='POSITION_ONLY_NOT_CORPUS',seed=1337,stride=7919,vocab=32768))
    source,oracle=WindowFixture(),WindowFixture()
    cursor=ContextCursor(plan,source,source_sha256=fixture_sha)
    resumed=None; saved=None; rows=[]
    for index in range(plan.steps):
        budget.check()
        update=cursor.prepare()
        expected=tuple(oracle() for _ in range(plan.base_accum))
        counts=torch.zeros(plan.base_accum,plan.micro_bs,plan.full_length,dtype=torch.int16)
        flat=[(x[i],y[i]) for x,y in update.batches for i in range(plan.micro_bs)]
        for (x,y),(draw,row,start,end) in zip(flat,update.origins):
            need(torch.equal(x,expected[draw][0][row,start:end]) and torch.equal(y,expected[draw][1][row,start:end]),
                 'original full-window target/input position changed')
            counts[draw,row,start:end]+=1
        need(len(flat)==len(update.origins) and bool((counts==1).all()),'position lost or duplicated')
        need(source.rng.bit_generator.state==oracle.rng.bit_generator.state,'extra source RNG consumed')
        if resumed is not None:
            other=resumed.prepare()
            need(tensor_pairs_sha(update.batches)==tensor_pairs_sha(other.batches)
                 and update.accounting==other.accounting,'resumed full position stream differs')
            resumed.finish(optimizer_applied=False)
        record=cursor.finish(optimizer_applied=False)
        record.update(independent_target_positions_checked=plan.tokens_per_update,
                      original_xy_sha256=tensor_pairs_sha(expected))
        rows.append(record)
        if index==1:
            saved=json.loads(json.dumps(cursor.state_dict()))
            resumed=ContextCursor(plan,WindowFixture(seed=77),source_sha256=fixture_sha)
            resumed.load_state_dict(saved)
    need(cursor.state_dict()==resumed.state_dict() and source.calls==oracle.calls==96,'final source accounting differs')
    return dict(status='FULL_POSITION_CONTRACT_ONLY_NOT_TRAINING',updates=6,
        original_target_positions_checked=6*131072,source_calls=96,optimizer_updates=0,
        model_forwards=0,model_loads=0,checkpoint_writes=0,rows=rows,
        resumed_next_update=saved['next_update'],final_source_state_sha256=cursor.state_dict()['state_sha256'],
        full_training_resume_claim=False,quality_claim=False)


def closed_contract(report,*,source,profile_sha256):
    need(report.get('exit_code')==0 and report.get('mode')=='contract'
         and report.get('source')==source and report.get('profile_sha256')==profile_sha256
         and report.get('result',{}).get('original_target_positions_checked')==786432
         and report['result'].get('source_calls')==96 and report['result'].get('model_forwards')==0,
         'closed exact full-position CPU contract required before actual model')


def validate(profile,args):
    need(profile.get('schema')==SCHEMA and profile.get('tag')==TAG
         and profile.get('root_approved') is True and profile.get('authority_directive')==96
         and profile.get('source_sha256')==identity()['sha256']
         and profile.get('deadline')=='2026-10-27T08:00:00+00:00'
         and profile.get('optimizer_updates')==0 and profile.get('checkpoint_writes')==0
         and profile.get('additional_300m') is False and args.max_wall_sec==CAPS[args.mode]
         and (resource.DEADLINE-datetime.now(timezone.utc)).total_seconds()>args.max_wall_sec+180,
         'exact bounded no-training source/authority required')
    contract=profile['cpu_contract']
    need(contract['actual_exit']==0 and resource.digest(resource.safe(contract['path']))==contract['sha256'],
         'closed meaningful CPU fixtures required')
    native=resource.read_ref(profile['native_profile'])
    need(native['source_sha256']==resource.identity()['sha256'] and profile.get('model_id')=='native595-q',
         'same native resource source and explicit completed Q model required')
    spec=next(x for x in native['models'] if x['id']=='native595-q')
    need(spec['cfg']['max_seq_len']==1024 and spec['cfg']['grad_checkpoint'] is True
         and spec['cfg']['train_repeat']==spec['cfg']['infer_repeat']==1 and not spec['cfg']['mtp_aux'],
         'original checkpoint-ON R1/noMTP model required')
    return native,spec


def forward_backward(model,pairs,length,plan):
    import torch
    import torch.nn.functional as F
    torch.cuda.synchronize();started=time.perf_counter()
    model.zero_grad(set_to_none=True)
    moved=iter(tuple((x.to('cuda'),y.to('cuda')) for x,y in pairs))
    source=snapshot_batches(lambda:next(moved),plan.base_accum)
    prepared=split_update(source,plan,length)
    total=torch.zeros((),device='cuda')
    for x,y in prepared.batches:
        with torch.autocast('cuda',dtype=torch.bfloat16):
            logits=model(x)
            loss=F.cross_entropy(logits.reshape(-1,32768),y.reshape(-1),reduction='sum')/plan.tokens_per_update
        loss.backward();total+=loss.detach()
        del logits,loss
    torch.cuda.synchronize();seconds=time.perf_counter()-started
    validation_started=time.perf_counter()
    gradients=[(name,p.grad) for name,p in model.named_parameters() if p.requires_grad]
    need(gradients and all(g is not None and bool(torch.isfinite(g).all()) for _,g in gradients),'missing/nonfinite model gradient')
    row=dict(seconds=seconds,validation_seconds=time.perf_counter()-validation_started,
        ntp_loss=float(total),actual_input_tokens=plan.tokens_per_update,ntp_targets=plan.tokens_per_update,
        source_xy_sha256=tensor_pairs_sha(pairs),active_micro_batches=len(prepared.batches),
        train_length=length,gradient_tensors=len(gradients),optimizer_updates=0)
    model.zero_grad(set_to_none=True)
    return row


def cleanup_cost_model(model,report):
    errors=[]
    for stage,action in (('zero_grad',lambda:model.zero_grad(set_to_none=True)),('clear_quant',model.clear_quant)):
        try:action()
        except BaseException as exc:errors.append(dict(stage=stage,type=type(exc).__name__,message=str(exc)[:1000]))
    report['cost_model_cleanup_errors']=errors
    return errors


def failure_outcome(error,report):
    # A later shutdown timeout cannot turn an earlier real compute error into HOLD.
    primary_exists='primary_cost_error' in report
    first_timeout=(not primary_exists or report.get('primary_cost_error_is_timeout') is True)
    if isinstance(error,TimeoutError) and first_timeout:return 'BUDGET_HOLD_NOT_FULL_SUITE',8
    return 'ERROR_NOT_COMPLETE',9


def record_cost_block(block,length,report,run_update,reset_peak,read_peak,read_entry=None):
    row=dict(block=block,length=length,warmup=None,measured=[],status='STARTED',
        peak_scope='RESET_ALLOCATED_PEAK;MODEL_PREPARATION_H2D_SPLIT_FB_GRAD_CHECK;RESERVED_CACHE_MAY_INCLUDE_CP_LOAD_OR_PREVIOUS_BLOCK')
    report['blocks'].append(row)
    primary=None
    try:
        if read_entry is not None:row['entry_memory']=read_entry()
        reset_peak()
        row['warmup']=run_update(0)
        for index in (1,2):row['measured'].append(run_update(index))
        row['status']='BLOCK_COMPLETE'
        return row
    except BaseException as exc:
        primary=dict(type=type(exc).__name__,message=str(exc)[:2000])
        row.update(status='PARTIAL_BLOCK_ERROR',primary_error=primary)
        raise
    finally:
        try:row.update(read_peak())
        except BaseException as exc:
            row['peak_error']=dict(type=type(exc).__name__,message=str(exc)[:1000])
            if primary is None:raise


def run_cost(native,spec,budget,report,runtime):
    import torch
    from scripts.interactive_research_infer import require_idle_gpu
    from scripts.diag_p102a_logit_margin import memory_point
    report['idle_before']=require_idle_gpu();report['memory_before']=memory_point()
    need(report['memory_before']['free_mib']>=12288,'12GiB free admission for actual F+B diagnostic required')
    generation_started=time.perf_counter();fixture=WindowFixture()
    master=tuple(snapshot_batches(fixture,16) for _ in range(3))
    report['source_generation_seconds']=time.perf_counter()-generation_started
    report['source_fixture']='POSITION_ONLY_NOT_CORPUS_OR_TRAIN_DATA'
    plan=ContextPlan(((2289,1024),));report['blocks']=[];report['source_proof']={}
    loaded=model=settings=tokenizer=route=parameters=None
    try:
        with resource.frozen_model(spec,native['tokenizer'],'cuda',budget,report['source_proof']) as loaded:
            model,settings,tokenizer,route=loaded
            runtime['model_ref']=weakref.ref(model)
            primary=None
            try:
                model.clear_quant();model.train()
                need(settings.grad_checkpoint and not settings.mtp_aux,'unexpected model training path')
                parameters=tuple(model.parameters())
                need(parameters and all(p.requires_grad for p in parameters),'cost requires every original model parameter trainable')
                report['actual_trainable_parameters']=sum(p.numel() for p in parameters)
                parameters=None
                with patch.object(torch,'save',side_effect=ValueError('checkpoint/tensor serialization forbidden in cost')):
                    for block,length in enumerate(ORDER):
                        budget.check()
                        row=record_cost_block(block,length,report,
                            lambda index:forward_backward(model,master[index],length,plan),
                            torch.cuda.reset_peak_memory_stats,
                            lambda:dict(peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                                        peak_reserved_bytes=torch.cuda.max_memory_reserved()),
                            lambda:dict(allocated_bytes=torch.cuda.memory_allocated(),reserved_bytes=torch.cuda.memory_reserved()))
                        print(json.dumps(dict(block=block,length=length,measured_seconds=[r['seconds'] for r in row['measured']])),flush=True)
            except BaseException as exc:
                primary=dict(type=type(exc).__name__,message=str(exc)[:2000]);report['primary_cost_error']=primary
                report['primary_cost_error_is_timeout']=isinstance(exc,TimeoutError)
                raise
            finally:
                errors=cleanup_cost_model(model,report)
                if errors and primary is None:raise RuntimeError('cost model cleanup failed: '+str(errors))
    finally:
        loaded=model=settings=tokenizer=route=parameters=None
    for index in (0,1):
        signatures={row['measured'][index]['source_xy_sha256'] for row in report['blocks']}
        need(len(signatures)==1,'same measured fixture/update position differs across block lengths')
    report['summary']={str(length):dict(measured_updates=4,
        median_seconds=statistics.median(r['seconds'] for b in report['blocks'] if b['length']==length for r in b['measured']),
        input_tokens_per_update=131072) for length in (256,512,1024)}
    report['not_measured']=['OPTIMIZER_TIME','COMPILE','VALIDATION','CHECKPOINT_SAVE','FULL_TRAINING_WALL','QUALITY','UNIQUE_CORPUS_EPOCH']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=CAPS,required=True)
    parser.add_argument('--profile',required=True);parser.add_argument('--profile-sha256',required=True)
    parser.add_argument('--max-wall-sec',type=int,required=True)
    action=parser.add_mutually_exclusive_group();action.add_argument('--execute',action='store_true');action.add_argument('--check-only',action='store_true')
    args=parser.parse_args();profile=resource.read_ref(dict(path=args.profile,sha256=args.profile_sha256))
    native,spec=validate(profile,args)
    if args.check_only:
        print(json.dumps(dict(status='P013_METADATA_ONLY',models=0,gpu_calls=0)));return 0
    need(args.execute,'explicit contract/cost execution required')
    import torch
    torch.set_num_threads(1 if args.mode=='contract' else 2);torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    output=resource.safe('test_result/evidence/'+TAG+'/'+args.mode+'/report.json');need(not output.exists(),'new phase namespace required')
    budget=resource.Budget(args.max_wall_sec);source=identity();rc=9;runtime={}
    report=dict(schema=SCHEMA,tag=TAG,mode=args.mode,source=source,profile_sha256=args.profile_sha256,
        started_at=datetime.now(timezone.utc).isoformat(),optimizer_updates=0,checkpoint_writes=0,quality_claim=False,
        status='STARTED',native_checkpoint=spec['checkpoint'])
    try:
        with resource.wall(args.max_wall_sec):
            if args.mode=='contract':report['result']=run_contract(budget)
            else:
                cp=resource.safe('test_result/evidence/'+TAG+'/contract/report.json')
                closed_contract(json.loads(cp.read_text()),source=source,profile_sha256=args.profile_sha256)
                run_cost(native,spec,budget,report,runtime)
            need(identity()==source,'source changed during diagnostic')
            report['status'],rc='TECHNICAL_COMPLETE_NOT_QUALITY',0
    except BaseException as exc:
        report['status'],rc=failure_outcome(exc,report)
        report['execution_error']=dict(type=type(exc).__name__,message=str(exc)[:2000])
    finally:
        gc.collect()
        if 'model_ref' in runtime:
            report['model_released']=runtime['model_ref']() is None
            if not report['model_released']:rc=9
        if args.mode=='cost' and torch.cuda.is_initialized():
            try:
                report['final_cuda_cleanup']=resource.close_cuda(torch)
                from scripts.diag_p014e_packed_deploy import assert_cuda_clean
                assert_cuda_clean(report['final_cuda_cleanup'])
            except BaseException as exc:
                report['final_cleanup_error']=dict(type=type(exc).__name__,message=str(exc)[:1000]);rc=9
        try:
            report['source_unchanged']=identity()==source
            need(report['source_unchanged'],'final diagnostic source changed')
            if args.mode=='cost':
                from scripts.interactive_research_infer import require_idle_gpu
                report['idle_after']=require_idle_gpu()
                proof=report.get('source_proof',{})
                if proof.get('initial_core_verified'):
                    need(proof.get('final_core_verified') and proof.get('gradients_absent')
                         and proof.get('checkpoint_bytes_unchanged') and not report.get('cost_model_cleanup_errors'),
                         'final actual-model verification incomplete')
        except BaseException as exc:
            report['final_verification_error']=dict(type=type(exc).__name__,message=str(exc)[:1000]);rc=9
        if rc==9 and report['status'] in ('TECHNICAL_COMPLETE_NOT_QUALITY','BUDGET_HOLD_NOT_FULL_SUITE'):
            report['status']='ERROR_FINAL_CLEANUP_NOT_COMPLETE'
        report.update(exit_code=rc,seconds=time.monotonic()-budget.started,ended_at=datetime.now(timezone.utc).isoformat())
        resource.write_new(output,report)
        print(json.dumps(dict(mode=args.mode,status=report['status'],actual_exit=rc,seconds=report['seconds'])))
    return rc


if __name__=='__main__':raise SystemExit(main())
