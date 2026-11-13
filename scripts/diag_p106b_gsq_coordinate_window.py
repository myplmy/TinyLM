#!/usr/bin/env python3
"""New Nov13 execution authority for the closed coordinate mechanics design."""
import argparse
from datetime import datetime,timezone
import gc
import json
from pathlib import Path
import subprocess
import time
from scripts import diag_p106b_gsq_coordinates as study
from scripts import diag_p106b_gsq_objective as cost

ROOT=Path(__file__).resolve().parents[1]
TAG='p106b_gsq_coordinates_v2_20261113';BASE=ROOT/'test_result/evidence'/TAG
DEADLINE=datetime(2026,11,13,8,tzinfo=timezone.utc)
POLICY=dict(study.POLICY)
SOURCES=tuple(dict.fromkeys((*study.SOURCE,'scripts/diag_p106b_gsq_coordinate_window.py',
                           'scripts/test_p106b_gsq_coordinate_window.py')))
PLAN='test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md'


def guard(start=None,maximum=3600):
    if (DEADLINE-datetime.now(timezone.utc)).total_seconds()<900:
        raise TimeoutError('user115 Nov13 final cleanup reserve')
    if start is not None and time.perf_counter()-start>maximum:
        raise TimeoutError('new coordinate phase budget')


def prepare():
    guard()
    if BASE.exists():raise FileExistsError('new coordinate window namespace required')
    from scripts.p101a_sft_mtp_data import stream_rows
    from scripts import interactive_research_infer as manual
    prepared=json.loads((cost.TRAIN/'report.json').read_text())
    rows=cost.selected_rows(prepared,list(stream_rows(cost.TRAIN,prepared['manifest'])))
    torch,model,manifest,entry,spec=cost.load_cpu();geometry=cost.inventory(model);model=None;gc.collect()
    cost.write(BASE/'training_rows.json',dict(rows=rows))
    (BASE/'initial_plan.txt').write_bytes((ROOT/PLAN).read_bytes())
    sources=dict(manual.required_source_pins());sources.update({n:cost.sha(ROOT/n) for n in SOURCES})
    profile=dict(schema='P106B_GSQ_COORDINATE_WINDOW_V1',tag=TAG,authority_directive=115,
        deadline=DEADLINE.isoformat(),sources=sources,policy=POLICY,
        training_data_sha256=cost.sha(BASE/'training_rows.json'),
        original_training_report_sha256=cost.sha(cost.TRAIN/'report.json'),
        plan_snapshot_sha256=cost.sha(BASE/'initial_plan.txt'),entry=entry,checkpoint=str(spec.checkpoint),
        manual_manifest_sha256=cost.object_sha(manifest),inventory=geometry,
        counts=dict(rows=128,actual_x_tokens=sum(len(r['record']['x']) for r in rows),
                    ce_targets=sum(r['ce_targets'] for r in rows),kd_chunks=sum(r['kd_chunks'] for r in rows)),
        exposure='EXACT_TRAIN128_REPEATED256_NOT_NORMAL_EPOCH_OR_QUALITY',minimum_free_mib=10240,
        base_checkpoint_writes=0,teacher_calls=0,quality_evaluation=False,additional300m=False)
    cost.write(BASE/'profile.json',profile)
    print('[PREPARED] '+json.dumps(dict(tag=TAG,counts=profile['counts'],cpu_model_load=True,gpu=False)),flush=True)


def verify():
    from scripts import interactive_research_infer as manual
    p=json.loads((BASE/'profile.json').read_text())
    if p['authority_directive']!=115 or p['deadline']!=DEADLINE.isoformat() or p['policy']!=POLICY:
        raise ValueError('frozen new coordinate authority/policy differs')
    for name,sha in p['sources'].items():
        if cost.sha(ROOT/name)!=sha:raise ValueError('frozen coordinate source differs: '+name)
    if cost.sha(BASE/'training_rows.json')!=p['training_data_sha256'] or cost.sha(BASE/'initial_plan.txt')!=p['plan_snapshot_sha256']:
        raise ValueError('frozen copied input or plan changed')
    if cost.sha(cost.TRAIN/'report.json')!=p['original_training_report_sha256']:
        raise ValueError('original TRAIN report changed')
    if cost.object_sha(manual.verify_manifest())!=p['manual_manifest_sha256']:raise ValueError('closed model manifest changed')
    rows=json.loads((BASE/'training_rows.json').read_text())['rows']
    if len(rows)!=128:raise ValueError('complete fixed128 required')
    return p,rows


def run(arm):
    if arm not in ('adamw','lion'):raise ValueError('explicit optimizer arm required')
    guard();profile,rows=verify();out=BASE/arm
    if out.exists():raise FileExistsError('coordinate output already exists')
    out.mkdir();started=time.perf_counter()
    result=dict(schema=profile['schema'],tag=TAG,arm=arm,status='RUNNING',authority_directive=115,
        profile_sha256=cost.sha(BASE/'profile.json'),policy=POLICY,quality_evaluation=False,
        original_checkpoint_writes=0,teacher_calls=0,returncode=9)
    torch=model=manifest=entry=spec=None
    try:
        from scripts import interactive_research_infer as manual
        result['admission']=manual.require_idle_gpu()
        point=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],
                             capture_output=True,text=True,check=True,timeout=10)
        if not point.stdout.strip().isdigit() or int(point.stdout.strip())<profile['minimum_free_mib']:
            raise MemoryError('GSQ full-model coordinate arm requires10240MiB free')
        result['admission']['free_mib']=int(point.stdout.strip())
        torch,model,manifest,entry,spec=cost.load_cpu()
        if entry!=profile['entry'] or cost.object_sha(manifest)!=profile['manual_manifest_sha256']:
            raise ValueError('actual strict CPU load differs from profile')
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        model=model.cuda();torch.cuda.reset_peak_memory_stats()
        result.update(study.measure(torch,model,rows,arm,started,3600,guard_fn=guard,directory=out))
        result.update(status='COORDINATE_MECHANICS_COMPLETE',returncode=0,
            peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
    except BaseException as exc:
        result.update(status='COORDINATE_MECHANICS_ERROR',error_type=type(exc).__name__,error=str(exc),returncode=9)
    model=manifest=entry=spec=None;gc.collect()
    if torch is not None and torch.cuda.is_initialized():
        try:
            from scripts.diag_p107_hybrid_mntp import close_owned_cuda
            close_owned_cuda(torch,result)
        except BaseException as exc:result.update(status='CUDA_CLEANUP_UNVERIFIED',cleanup_error=str(exc),returncode=9)
    result['original_checkpoint_unchanged']=cost.sha(ROOT/profile['checkpoint'])==profile['entry']['checkpoint']['sha256']
    if not result['original_checkpoint_unchanged']:result.update(status='ORIGINAL_CHECKPOINT_CHANGED',returncode=9)
    try:verify();result['sources_and_inputs_unchanged']=True
    except BaseException as exc:result.update(status='FINAL_SOURCE_ERROR',error=str(exc),returncode=9)
    result['whole_wall_seconds']=time.perf_counter()-started;cost.write(out/'report.json',result)
    print('[COORDINATE_FINAL] '+json.dumps(dict(arm=arm,status=result['status'],updates=result.get('updates'),
        seconds=result['whole_wall_seconds'],returncode=result['returncode'])),flush=True)
    return result['returncode']


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','run'])
    parser.add_argument('--arm',choices=['adamw','lion']);args=parser.parse_args()
    if args.phase=='prepare':prepare();return 0
    if not args.arm:parser.error('run requires explicit --arm')
    return run(args.arm)


if __name__=='__main__':raise SystemExit(main())
