#!/usr/bin/env python3
"""Synthetic logits only: argmax, ID transfer and CPU policy statistics costs."""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import gc
import json
from pathlib import Path
import statistics
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import torch
from scripts import diag_p107_adaptive_masking as cpu
from scripts import diag_p106b_resource_matrix as resource
from tinylm.train.adaptive_masking import HardMaskPolicy

TAG='p107_argmax_transfer_v1_20261027'
SCHEMA='P107_SYNTHETIC_GPU_ARGMAX_TRANSFER_V1'
OWN=(*cpu.OWN,'scripts/diag_p107_adaptive_gpu_transfer.py',
     'scripts/test_p107_adaptive_gpu_transfer.py','scripts/interactive_research_infer.py',
     'tinylm/model/visibility.py')
need=resource.need


def identity():
    files={name:resource.digest(resource.safe(name)) for name in OWN}
    return dict(files=files,sha256=resource.sha(files))


def prepare_fixture(vocab):
    tokens,docs,_=cpu.fixture(vocab,0)
    selected=cpu.h.uniform_mntp_selection(tokens,docs,vocab_size=vocab,probability=.15,
                                        generator=torch.Generator(device='cpu').manual_seed(1337))
    batch=cpu.h.mntp_batch(tokens,docs,selected,vocab_size=vocab)
    expected=cpu.synthetic_predictions(batch)
    return batch,expected


def collect_ids(logits,targets,mode):
    """Full or gathered-row argmax; return only CPU IDs, no persistent GPU state."""
    need(mode in ('full','selected') and logits.ndim==3 and logits.is_floating_point()
         and targets.device.type=='cpu' and targets.dtype==torch.long
         and targets.shape==logits.shape[:-1], 'explicit logits/CPU target shape required')
    selected=targets!=cpu.h.IGNORE_INDEX
    need(bool(selected.any()),'nonempty selected rows required')
    sync=torch.cuda.synchronize if logits.device.type=='cuda' else lambda:None
    sync();started=time.perf_counter()
    gathered=logits[selected.to(logits.device)] if mode=='selected' else logits
    sync();prepared=time.perf_counter()
    ids=gathered.argmax(-1)
    sync();reduced=time.perf_counter()
    transferred=ids.to('cpu')
    output=torch.zeros_like(targets)
    output[selected]=transferred if mode=='selected' else transferred[selected]
    sync();ended=time.perf_counter()
    return output,dict(prepare_seconds=prepared-started,argmax_seconds=reduced-prepared,
        id_transfer_seconds=ended-reduced,total_id_seconds=ended-started,
        transferred_id_bytes=ids.numel()*ids.element_size(),
        extra_gather_logit_bytes=gathered.numel()*gathered.element_size() if mode=='selected' else 0)


def run_vocab(report,vocab,source,budget):
    batch,expected=prepare_fixture(vocab)
    shape=(*batch.targets.shape,vocab)
    report['allocation_attempts'].append(dict(vocab=vocab,shape=shape,dtype='bfloat16',expected_logit_bytes=2*shape[0]*shape[1]*shape[2]))
    matrix=torch.full(shape,-9.,dtype=torch.bfloat16,device='cuda')
    # The sole maximum in every row is known without evaluating another model.
    rows=torch.arange(expected.numel(),device='cuda')
    matrix.view(-1,vocab)[rows,expected.flatten().to('cuda')]=3.
    del rows
    torch.cuda.synchronize()
    try:
        for mode in ('full','selected','selected','full'):
            budget.check();gc.collect();torch.cuda.empty_cache();torch.cuda.synchronize()
            policy=HardMaskPolicy(cpu.config(vocab,'keep',source))
            block=dict(vocab=vocab,mode=mode,status='STARTED',selected_targets=batch.target_count,
                       logit_storage_bytes=matrix.untyped_storage().nbytes(),attempts=[])
            report['blocks'].append(block)
            for index in range(4):
                budget.check();policy.begin_update(index,split='train',expected_observations=1)
                attempt=dict(index=index,warmup=index==0,status='STARTED');block['attempts'].append(attempt)
                torch.cuda.reset_peak_memory_stats()
                predictions,metrics=collect_ids(matrix,batch.targets,mode)
                attempt.update(metrics)
                need(torch.equal(predictions,expected),'GPU argmax/shifted expected IDs differ')
                started=time.perf_counter();policy.observe(batch,predictions,observation_index=0)
                policy.finish_update(accepted=True)
                attempt.update(stat_commit_seconds=time.perf_counter()-started,status='ATTEMPT_COMPLETE',
                    allocated_peak_bytes=torch.cuda.max_memory_allocated(),reserved_peak_bytes=torch.cuda.max_memory_reserved())
            gold=batch.targets[batch.targets!=cpu.h.IGNORE_INDEX]
            expected_counts=torch.bincount(gold,minlength=vocab)
            need(torch.equal(policy.lifetime_total,4*expected_counts),'statistics counted wrong gold types')
            block.update(status='BLOCK_COMPLETE',gold_histogram_exact=True,median_seconds={key:statistics.median(a[key] for a in block['attempts'] if not a['warmup'])
                for key in ('prepare_seconds','argmax_seconds','id_transfer_seconds','total_id_seconds','stat_commit_seconds')})
    finally:
        del matrix
        gc.collect();torch.cuda.empty_cache();torch.cuda.synchronize()


def validate(profile,args):
    need(profile.get('schema')==SCHEMA and profile.get('tag')==TAG and profile.get('root_approved') is True
        and profile.get('source_sha256')==identity()['sha256'] and args.max_wall_sec==300
        and profile.get('authority_directive')==96 and profile.get('deadline')==resource.DEADLINE.isoformat()
        and profile.get('models')==profile.get('optimizer_updates')==profile.get('checkpoint_writes')==0,
        'exact synthetic-only GPU profile required')
    need(datetime.now(timezone.utc).timestamp()+420<resource.DEADLINE.timestamp(),'worker and cleanup must fit authority')
    ref=profile['cpu_contract']
    need(ref['actual_exit']==0 and resource.digest(resource.safe(ref['path']))==ref['sha256'],'closed CPU receipt required')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True);parser.add_argument('--profile-sha256',required=True)
    parser.add_argument('--max-wall-sec',type=int,required=True)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-only',action='store_true');mode.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    profile=resource.read_ref(dict(path=args.profile,sha256=args.profile_sha256));validate(profile,args)
    if args.check_only:
        print(json.dumps(dict(status='ARGMAX_METADATA_ONLY',models=0,gpu_calls=0)));return 0
    output=resource.safe('test_result/evidence/'+TAG+'/gpu/report.json');need(not output.exists(),'new namespace required')
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    source=identity();budget=resource.Budget(300);rc=9
    report=dict(schema=SCHEMA,source=source,profile_sha256=args.profile_sha256,started_at=datetime.now(timezone.utc).isoformat(),
        status='STARTED',blocks=[],allocation_attempts=[],models=0,optimizer_updates=0,checkpoint_writes=0,
        source_corpus_reads=0,quality_claim=False,measures='SYNTHETIC_EXISTING_LOGITS_ARGMAX_ID_TRANSFER_CPU_COMMIT;NOT_MODEL_TRAINING',
        torch_version=torch.__version__,cuda_version=torch.version.cuda)
    try:
        with resource.wall(300),patch.object(torch,'load',side_effect=ValueError('model load forbidden')), \
             patch.object(torch,'save',side_effect=ValueError('checkpoint save forbidden')),torch.inference_mode():
            from scripts.interactive_research_infer import require_idle_gpu
            report['idle_before']=require_idle_gpu()
            free,total=torch.cuda.mem_get_info();report['entry_free_bytes']=free;report['entry_total_bytes']=total
            need(free>=8*1024**3,'8GiB free admission required')
            for vocab in (32768,262144):run_vocab(report,vocab,source,budget)
        report['status'],rc='GPU_TECHNICAL_COMPLETE_NOT_QUALITY',0
    except BaseException as exc:
        rc=8 if isinstance(exc,TimeoutError) else 9
        report.update(status='GPU_BUDGET_HOLD' if rc==8 else 'GPU_ERROR',error=dict(type=type(exc).__name__,message=str(exc)[:2000]))
    finally:
        errors=[]
        try:
            report['final_cuda_cleanup']={}
            if torch.cuda.is_initialized():
                resource.close_cuda(torch,report['final_cuda_cleanup'])
                need(report['final_cuda_cleanup'].get('allocated_bytes')==0 and report['final_cuda_cleanup'].get('reserved_bytes')==0,'owned CUDA not empty')
        except BaseException as exc:errors.append(dict(stage='cuda_cleanup',type=type(exc).__name__,message=str(exc)[:1000]))
        try:
            report['source_unchanged']=identity()==source;need(report['source_unchanged'],'source changed')
        except BaseException as exc:errors.append(dict(stage='source',type=type(exc).__name__,message=str(exc)[:1000]))
        if errors:rc=9;report['status']='GPU_FINAL_VERIFICATION_ERROR'
        report.update(final_verification_errors=errors,exit_code=rc,seconds=time.monotonic()-budget.started,ended_at=datetime.now(timezone.utc).isoformat())
        resource.write_new(output,report)
        print(json.dumps(dict(status=report['status'],actual_exit=rc,seconds=report['seconds'],blocks=len(report['blocks']))))
    return rc


if __name__=='__main__':raise SystemExit(main())
