#!/usr/bin/env python3
"""Private numeric-tail bridge with the existing256-update mechanics bytecode."""
import argparse
from datetime import datetime,timezone
import gc
import json
from pathlib import Path
import subprocess
import time
import traceback
import types
from scripts import p106b_alm_logtail as stable
from scripts import p106b_gsq_coordinates as coordinates
from scripts import diag_p106b_gsq_coordinates as study
from scripts import diag_p106b_gsq_coordinate_window as prior
from scripts import diag_p106b_gsq_objective as cost

ROOT=Path(__file__).resolve().parents[1]
TAG='p106b_gsq_logtail_v1_20261113';BASE=ROOT/'test_result/evidence'/TAG
DEADLINE=datetime(2026,11,13,8,tzinfo=timezone.utc)
POLICY=dict(prior.POLICY,numeric_kernel='FINITE_LOGIT_LOG_NLL_LOGTAIL_NO_CLIP',
            head_reduction='FP64_CHUNK64_NOT_MODEL_MATMUL',original_product_alm_changed=False)
SOURCES=tuple(dict.fromkeys((*prior.SOURCES,'scripts/p106b_alm_logtail.py','scripts/test_p106b_alm_logtail.py',
                            'scripts/diag_p106b_gsq_logtail.py','scripts/test_p106b_gsq_logtail_driver.py')))


def guard(start=None,maximum=3600):
    if (DEADLINE-datetime.now(timezone.utc)).total_seconds()<900:
        raise TimeoutError('user115 Nov13 logtail final reserve')
    if start is not None and time.perf_counter()-start>maximum:raise TimeoutError('logtail phase budget')


def make_bridge(model,observations,**kwargs):
    bridge=coordinates.scaled_bridge(model,**kwargs)
    def loss_terms(self,x,targets,chunks=(),*,temperature=100.,head_chunk=64):
        if not self._active:raise RuntimeError('explicit realization required')
        hidden=self.model(x,return_hidden=True)
        nll,logn,mask=stable.target_dual(self.model,hidden,targets,chunk=head_chunk)
        kl,count,stats=stable.chunk_kl(nll,logn,mask,chunks,temperature=temperature)
        observations['forward_calls']+=1
        for key in ('ordinary_zero_positions','old_boundary_chunks'):observations[key]+=stats[key]
        observations['min_log_nll']=min(observations['min_log_nll'],stats.get('min_log_nll',0.))
        if stats['old_boundary_chunks'] and observations['first_boundary_forward'] is None:
            observations['first_boundary_forward']=observations['forward_calls']
            print('[LOGTAIL_BOUNDARY] '+json.dumps(dict(update=(observations['forward_calls']-1)//16+1,
                micro=(observations['forward_calls']-1)%16,**stats)),flush=True)
        return dict(ce_sum=nll.sum(),ce_targets=int(mask.sum()),kl_sum=kl,kl_chunks=count,nll=nll,supervised=mask)
    bridge.loss_terms=types.MethodType(loss_terms,bridge)
    return bridge


def make_measure(observations):
    original=study.measure
    namespace=dict(original.__globals__)
    namespace['coordinates']=types.SimpleNamespace(
        scaled_bridge=lambda model,**kw:make_bridge(model,observations,**kw),
        optimizer_pair=coordinates.optimizer_pair)
    result=types.FunctionType(original.__code__,namespace,original.__name__,original.__defaults__,original.__closure__)
    result.__kwdefaults__=dict(original.__kwdefaults__ or {})
    if result.__code__ is not original.__code__:raise RuntimeError('mechanics bytecode changed')
    return result


def prepare():
    guard()
    if BASE.exists():raise FileExistsError('fresh logtail namespace required')
    from scripts import interactive_research_infer as manual
    old=json.loads((prior.BASE/'profile.json').read_text())
    references={}
    for p in (prior.BASE/'profile.json',prior.BASE/'training_rows.json',prior.BASE/'adamw/report.json',
              prior.BASE/'lion/report.json',cost.TRAIN/'report.json'):
        references[str(p.relative_to(ROOT))]=cost.sha(p)
    if cost.object_sha(manual.verify_manifest())!=old['manual_manifest_sha256']:raise ValueError('completed model changed')
    rows=json.loads((prior.BASE/'training_rows.json').read_text())['rows']
    if len(rows)!=128:raise ValueError('same complete128 required')
    sources=dict(manual.required_source_pins());sources.update({p:cost.sha(ROOT/p) for p in SOURCES})
    BASE.mkdir();(BASE/'initial_plan.txt').write_bytes((ROOT/prior.PLAN).read_bytes())
    profile=dict(schema='P106B_GSQ_LOGTAIL_WINDOW_V1',tag=TAG,authority_directive=115,deadline=DEADLINE.isoformat(),
        policy=POLICY,sources=sources,references=references,data_reference=str((prior.BASE/'training_rows.json').relative_to(ROOT)),
        manual_manifest_sha256=old['manual_manifest_sha256'],entry=old['entry'],checkpoint=old['checkpoint'],
        minimum_free_mib=10240,counts=old['counts'],plan_snapshot_sha256=cost.sha(BASE/'initial_plan.txt'),
        probability_clip=False,base_checkpoint_writes=0,quality_evaluation=False,additional300m=False)
    cost.write(BASE/'profile.json',profile)
    print('[PREPARED] '+json.dumps(dict(tag=TAG,counts=profile['counts'],model_load=False,gpu=False)),flush=True)


def verify():
    from scripts import interactive_research_infer as manual
    p=json.loads((BASE/'profile.json').read_text())
    if p['authority_directive']!=115 or p['deadline']!=DEADLINE.isoformat() or p['policy']!=POLICY:
        raise ValueError('frozen logtail authority/policy changed')
    for name,sha in dict(p['sources'],**p['references']).items():
        if cost.sha(ROOT/name)!=sha:raise ValueError('logtail source/reference changed: '+name)
    if cost.sha(BASE/'initial_plan.txt')!=p['plan_snapshot_sha256']:raise ValueError('frozen plan changed')
    if cost.object_sha(manual.verify_manifest())!=p['manual_manifest_sha256']:raise ValueError('closed model changed')
    rows=json.loads((ROOT/p['data_reference']).read_text())['rows']
    if len(rows)!=128:raise ValueError('complete128 required')
    return p,rows


def run(arm):
    if arm not in ('adamw','lion'):raise ValueError('explicit arm required')
    guard();p,rows=verify();out=BASE/arm
    if out.exists():raise FileExistsError('actual logtail arm exists')
    out.mkdir();started=time.perf_counter();torch=model=manifest=entry=spec=None
    observations=dict(forward_calls=0,ordinary_zero_positions=0,old_boundary_chunks=0,min_log_nll=0.,first_boundary_forward=None)
    result=dict(schema=p['schema'],tag=TAG,arm=arm,status='RUNNING',policy=POLICY,authority_directive=115,
        profile_sha256=cost.sha(BASE/'profile.json'),quality_evaluation=False,original_checkpoint_writes=0,
        teacher_calls=0,returncode=9,private_mechanics_bytecode=True)
    try:
        from scripts import interactive_research_infer as manual
        result['admission']=manual.require_idle_gpu()
        query=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],
                             capture_output=True,text=True,check=True,timeout=10)
        if not query.stdout.strip().isdigit() or int(query.stdout.strip())<p['minimum_free_mib']:
            raise MemoryError('logtail GSQ needs10240MiB free')
        result['admission']['free_mib']=int(query.stdout.strip())
        torch,model,manifest,entry,spec=cost.load_cpu()
        if entry!=p['entry'] or cost.object_sha(manifest)!=p['manual_manifest_sha256']:raise ValueError('strict CPU model changed')
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        model=model.cuda();torch.cuda.reset_peak_memory_stats()
        result.update(make_measure(observations)(torch,model,rows,arm,started,3600,guard_fn=guard,directory=out))
        result.update(status='LOGTAIL_COORDINATE_MECHANICS_COMPLETE',returncode=0)
    except BaseException as exc:
        result.update(status='LOGTAIL_COORDINATE_ERROR',error_type=type(exc).__name__,error=str(exc),
                      traceback=traceback.format_exc(),returncode=9)
    if torch is not None and torch.cuda.is_initialized():
        result['peak_allocated_bytes']=torch.cuda.max_memory_allocated();result['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
    result['numeric_tail_observations']=observations
    if (out/'events.jsonl').is_file():
        result['completed_updates_from_journal']=sum(1 for l in (out/'events.jsonl').read_text().splitlines() if l.strip())
    model=manifest=entry=spec=None;gc.collect()
    if torch is not None and torch.cuda.is_initialized():
        try:
            from scripts.diag_p107_hybrid_mntp import close_owned_cuda
            close_owned_cuda(torch,result)
        except BaseException as exc:result.update(status='CUDA_CLEANUP_UNVERIFIED',cleanup_error=str(exc),returncode=9)
    result['original_checkpoint_unchanged']=cost.sha(ROOT/p['checkpoint'])==p['entry']['checkpoint']['sha256']
    if not result['original_checkpoint_unchanged']:result.update(status='ORIGINAL_CHECKPOINT_CHANGED',returncode=9)
    try:verify();result['sources_and_inputs_unchanged']=True
    except BaseException as exc:result.update(status='FINAL_SOURCE_ERROR',error=str(exc),returncode=9)
    result['whole_wall_seconds']=time.perf_counter()-started;cost.write(out/'report.json',result)
    print('[LOGTAIL_FINAL] '+json.dumps(dict(arm=arm,status=result['status'],updates=result.get('completed_updates_from_journal'),
        seconds=result['whole_wall_seconds'],returncode=result['returncode'])),flush=True)
    return result['returncode']


def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','run']);p.add_argument('--arm',choices=['adamw','lion'])
    args=p.parse_args()
    if args.phase=='prepare':prepare();return 0
    if not args.arm:p.error('explicit arm required')
    return run(args.arm)


if __name__=='__main__':raise SystemExit(main())
