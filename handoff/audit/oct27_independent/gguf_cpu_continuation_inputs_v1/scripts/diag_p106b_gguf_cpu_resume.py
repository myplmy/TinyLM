#!/usr/bin/env python3
"""Explicit CPU-only5400s follow-up; original1800s HOLD and source stay intact."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json,math
from pathlib import Path
import sys,time
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_gguf_prefill_control as control
from scripts import diag_p106b_gguf_resources as generation
from scripts import diag_p106b_resource_matrix as resource

TAG='p106b_gpt2_singleton_cpu_budget5400_v1_20261027'
SCHEMA='P106B_EXPLICIT_SINGLETON_CPU_BUDGET_V1'
OWN=('scripts/diag_p106b_gguf_cpu_resume.py','scripts/test_p106b_gguf_cpu_resume.py')
need=resource.need

def identity():
    files=dict(control.identity()['files'])
    files.update({name:resource.digest(resource.safe(name)) for name in OWN})
    return dict(files=files,sha256=resource.sha(files))

def budget_admission(hold):
    need(hold['mode']=='resources' and hold['device']=='cpu' and hold['exit_code']==8
         and hold['status']=='BUDGET_HOLD_NOT_FULL_SUITE' and hold['workloads']==[] and hold['answers']==[],
         'original untouched CPU forecast HOLD required')
    need(len(hold['numeric_canary'])==16 and all(x['allclose'] and x['argmax_equal'] for x in hold['numeric_canary']),
         'CPU singleton numerical canary must already be complete')
    proof=hold['proof'];need(proof['worker_returncode']==0 and proof['worker_cleanup_complete'] is True
         and not proof['cleanup_diagnostics'] and not proof['telemetry_errors'],'original CPU worker must be closed cleanly')
    seconds=hold['cost_admission']['conservative_seconds']
    need(type(seconds) in (int,float) and math.isfinite(seconds) and seconds>0 and seconds+600<5400,
         'measured whole CPU forecast plus600s cannot fit new explicit cap')
    return dict(prior_execution_cap_seconds=1800,new_execution_cap_seconds=5400,
                measured_conservative_seconds=seconds,reserved_closure_seconds=600,
                predicted_total_seconds=seconds+600,prior_hold_preserved=True)

def validate(profile,args):
    need(profile.get('schema')==SCHEMA and profile.get('tag')==TAG and profile.get('root_approved') is True
         and profile.get('authority_directive')==96 and profile.get('source_sha256')==identity()['sha256']
         and args.max_wall_sec==profile['max_wall_sec']==5400,'separate source-bound5400s CPU authority required')
    need(profile.get('deadline')=='2026-10-27T08:00:00+00:00'
         and (resource.DEADLINE-datetime.now(timezone.utc)).total_seconds()>5580,'whole CPU continuation/closure cannot fit')
    original=resource.read_ref(profile['prior_profile'])
    # This validates the ORIGINAL1800s metadata contract only. Actual execution
    # below uses the separate5400s wall, Budget and native worker deadline.
    build,assets,texts,route=control.validate(original,SimpleNamespace(mode='resources',device='cpu',max_wall_sec=1800))
    hold=resource.read_ref(profile['prior_hold'])
    need(hold['source']==control.identity() and hold['assets']==assets
         and hold['build']==original['build'] and hold['profile_sha256']==profile['prior_profile']['sha256'],
         'exact original CPU source/assets/profile/build required')
    return build,assets,texts,route,budget_admission(hold)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True);parser.add_argument('--profile-sha256',required=True)
    parser.add_argument('--max-wall-sec',type=int,required=True)
    action=parser.add_mutually_exclusive_group();action.add_argument('--execute',action='store_true');action.add_argument('--check-only',action='store_true')
    args=parser.parse_args();profile=resource.read_ref(dict(path=args.profile,sha256=args.profile_sha256))
    build,assets,texts,route,admission=validate(profile,args)
    if args.check_only:print(json.dumps(dict(status='EXPLICIT_CPU_BUDGET_METADATA_ONLY',admission=admission,model_loads=0,gpu_calls=0)));return 0
    need(args.execute,'explicit CPU continuation required')
    from scripts.p106b_shards import ShardWriter
    from scripts.interactive_research_infer import require_idle_gpu
    source=identity();budget=resource.Budget(args.max_wall_sec)
    output=resource.safe('test_result/evidence/'+TAG+'/report.json');raw=resource.safe('runs/eval/'+TAG+'/wire')
    need(not output.exists() and not raw.exists(),'separate CPU continuation output required')
    report=dict(schema=SCHEMA,tag=TAG,device='cpu',source=source,assets=assets,build=profile['build'],
        profile_sha256=args.profile_sha256,prior_profile=profile['prior_profile'],prior_hold=profile['prior_hold'],
        admission=admission,route_admission=route,prefill_chunk=1,status='STARTED',quality_claim=False,
        training_updates=0,checkpoint_writes=0,exact_native_tensor_storage='NOT_MEASURED_NO_PUBLIC_BUFFER_HANDLE',
        exact_native_KV_storage='NOT_MEASURED',workloads=[],answers=[],proof={},started_at=datetime.now(timezone.utc).isoformat())
    writer=ShardWriter(raw,'wire',limit=19_999_999);rc=9
    try:
        with resource.wall(args.max_wall_sec):
            report['idle_before']=require_idle_gpu()
            with generation.Worker(assets,build,min(time.time()+5400,resource.DEADLINE.timestamp()),writer,report['proof'],'cpu') as worker:
                control.set_chunk(worker,1);rc=generation.run_suite(worker,texts,budget,report)
            need(report['proof'].get('worker_returncode')==0 and report['proof'].get('worker_cleanup_complete') is True
                 and not report['proof'].get('cleanup_diagnostics') and not report['proof'].get('telemetry_errors'),
                 'continued CPU worker cleanup differs')
            report['idle_after']=require_idle_gpu()
            need(identity()==source and generation.native.asset_identity('gpt2_q4km')==assets,'CPU continuation inputs changed')
    except BaseException as exc:
        report['status']='ERROR_NOT_COMPLETE';report['error']=dict(type=type(exc).__name__,message=str(exc)[:2000]);rc=9
    finally:
        report['wire_manifest']=writer.close(lineage=dict(schema=SCHEMA,complete=rc==0))
        report.update(exit_code=rc,seconds=time.monotonic()-budget.started,ended_at=datetime.now(timezone.utc).isoformat())
        resource.write_new(output,report);print(json.dumps(dict(status=report['status'],exit_code=rc,seconds=report['seconds'])))
    return rc

if __name__=='__main__':raise SystemExit(main())
