#!/usr/bin/env python3
"""Separate prefill-shape intervention; preserve prior native resource ERROR9."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from pathlib import Path
import json,struct,sys,time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_gguf_resources as generation
from scripts import diag_p106b_resource_matrix as resource

TAG='p106b_gpt2_prefill_control_v1_20261027'
SCHEMA='P106B_NATIVE_PREFILL_CONTROL_V1'
TILES=(1,32,512)
OWN=('scripts/diag_p106b_gguf_prefill_control.py','scripts/test_p106b_gguf_prefill_control.py')
need=resource.need

def identity():
    files=dict(generation.identity()['files'])
    files.update({name:resource.digest(resource.safe(name)) for name in OWN})
    return dict(files=files,sha256=resource.sha(files))

def admit_singleton(diagnostic):
    need(diagnostic['schema']==SCHEMA and diagnostic['mode']=='diagnose'
         and diagnostic['status']=='CONTROLLED_PREFILL_COMPLETE_NOT_ADOPTED' and diagnostic['exit_code']==0,
         'closed controlled prefill report required')
    rows={x['prefill_chunk']:x for x in diagnostic['controls']}
    need(set(rows)==set(TILES) and len(diagnostic['controls'])==3,'all three distinct controls required')
    need(all(len(x['numeric'])==16 for x in rows.values()),'partial alternative controls cannot be hidden')
    row=rows[1];need(not row['failed_workloads'] and len(row['numeric'])==16,'complete singleton sixteen positions required')
    need({(x['workload'],x['step']) for x in row['numeric']}=={(k,i) for k in ('ko128','en128','ko512','en512') for i in range(4)},
         'singleton coverage differs')
    need(all(x['allclose'] and x['argmax_equal'] for x in row['numeric']),'singleton original numeric gate failed')
    need(diagnostic['proof']['worker_returncode']==0 and diagnostic['proof']['worker_cleanup_complete'] is True
         and not diagnostic['proof']['cleanup_diagnostics'] and not diagnostic['proof']['telemetry_errors'],
         'closed clean controlled worker required')
    return dict(prefill_chunk=1,prior_bulk_error_preserved=True,scope='SINGLETON_ENGINE_FUNCTION_ONLY_NOT_BULK_ADOPTION')

def set_chunk(worker,tile):
    need(tile in TILES,'unregistered prefill intervention')
    reader=generation.native.Reader(worker.rpc(10,struct.pack('<I',tile)))
    need(reader.u32()==tile,'native prefill echo differs');reader.end()

def diagnose(worker,texts,budget,report):
    prompts=[]
    for source in texts['workloads']:
        text=source['text'];ids=worker.tokenize(text)
        while len(ids)<source['prompt_tokens']:
            text+=source['text'];ids=worker.tokenize(text)
        prompts.append(dict(id=source['id'],ids=ids[:source['prompt_tokens']]))
    report['prompts']=prompts
    for tile in TILES:
        budget.check();set_chunk(worker,tile)
        row=dict(prefill_chunk=tile,numeric=[],failed_workloads=[]);report['controls'].append(row)
        for prompt in prompts:
            try:generation.numeric_canary(worker,prompt['ids'],row['numeric'],prompt['id'])
            except ValueError as exc:
                if str(exc)!='native cache/fullprefix numeric canary differs':raise
                row['failed_workloads'].append(prompt['id'])
        need(len(row['numeric'])==16,'complete sixteen probes per prefill required')
        row['allclose']=all(x['allclose'] for x in row['numeric'])
        row['max_abs']=max(x['max_abs'] for x in row['numeric'])
        print(json.dumps(dict(prefill_chunk=tile,allclose=row['allclose'],max_abs=row['max_abs'])),flush=True)
    report['status']='CONTROLLED_PREFILL_COMPLETE_NOT_ADOPTED';return 0

def validate(profile,args):
    cap=900 if args.mode=='diagnose' else 1800
    need(profile.get('schema')==SCHEMA and profile.get('tag')==TAG and profile.get('root_approved') is True
         and profile.get('authority_directive')==96 and profile.get('mode')==args.mode
         and profile.get('source_sha256')==identity()['sha256'] and args.max_wall_sec==profile['max_worker_seconds']==cap,
         'exact source/mode/authority/cap required')
    need(profile.get('deadline')=='2026-10-27T08:00:00+00:00'
         and (resource.DEADLINE-datetime.now(timezone.utc)).total_seconds()>cap+180,'whole native control cannot fit')
    build=resource.read_ref(profile['build']);binary=resource.safe(build['worker'])
    need(resource.digest(binary)==build['worker_sha256']
         and build['cpp_sha256']==resource.digest(resource.safe(generation.OWN[1]))
         and build['wire_cpp_sha256']==resource.digest(resource.safe('scripts/p106b_native_llama_worker.cpp')),
         'controlled worker/source differs')
    assets=generation.native.asset_identity('gpt2_q4km')
    old=resource.read_ref(profile['closed_report']);terminal=resource.read_ref(profile['terminal'])
    need(old['assets']==assets and terminal['status']=='NATIVE_WINDOW_FULL_COMPLETE' and terminal['returncode']==0
         and terminal['report_sha256']==profile['closed_report']['sha256'],'completed official identity differs')
    prior=resource.read_ref(profile['prior_errors'][args.device])
    need(prior['exit_code']==9 and prior['status']=='ERROR_NOT_COMPLETE'
         and prior['error']['message']=='native cache/fullprefix numeric canary differs'
         and prior['assets']==assets and prior['device']==args.device,'same-device original numerical error must remain visible')
    admission=None
    if args.mode=='resources':
        diagnostic=resource.read_ref(profile['diagnostics'][args.device])
        need(diagnostic['source']==identity() and diagnostic['device']==args.device
             and diagnostic['assets']==assets and diagnostic['build']==profile['build'],
             'same-device/source/assets/build diagnosis required')
        admission=admit_singleton(diagnostic)
    return build,assets,resource.read_ref(profile['texts']),admission

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('diagnose','resources'),required=True)
    parser.add_argument('--device',choices=('cpu','cuda'),required=True)
    parser.add_argument('--profile',required=True);parser.add_argument('--profile-sha256',required=True)
    parser.add_argument('--max-wall-sec',type=int,required=True)
    action=parser.add_mutually_exclusive_group();action.add_argument('--execute',action='store_true');action.add_argument('--check-only',action='store_true')
    args=parser.parse_args();profile=resource.read_ref(dict(path=args.profile,sha256=args.profile_sha256))
    build,assets,texts,admission=validate(profile,args)
    if args.check_only:print(json.dumps(dict(status='PREFILL_CONTROL_METADATA_ONLY',model_loads=0,gpu_calls=0)));return 0
    need(args.execute,'explicit independent controlled execution required')
    from scripts.p106b_shards import ShardWriter
    from scripts.interactive_research_infer import require_idle_gpu
    source=identity();budget=resource.Budget(args.max_wall_sec)
    branch=TAG+'/'+args.mode+'/'+args.device
    output=resource.safe('test_result/evidence/'+branch+'/report.json');raw=resource.safe('runs/eval/'+branch+'/wire')
    need(not output.exists() and not raw.exists(),'new controlled output namespace required')
    report=dict(schema=SCHEMA,tag=TAG,mode=args.mode,device=args.device,source=source,assets=assets,build=profile['build'],
        profile_sha256=args.profile_sha256,prior_error=profile['prior_errors'][args.device],admission=admission,
        status='STARTED',quality_claim=False,training_updates=0,checkpoint_writes=0,
        exact_native_tensor_storage='NOT_MEASURED_NO_PUBLIC_BUFFER_HANDLE',exact_native_KV_storage='NOT_MEASURED',
        controls=[],workloads=[],answers=[],proof={},started_at=datetime.now(timezone.utc).isoformat())
    writer=ShardWriter(raw,'wire',limit=19_999_999);rc=9
    try:
        with resource.wall(args.max_wall_sec):
            report['idle_before']=require_idle_gpu()
            with generation.Worker(assets,build,min(time.time()+args.max_wall_sec,resource.DEADLINE.timestamp()),writer,report['proof'],args.device) as worker:
                if args.mode=='diagnose':rc=diagnose(worker,texts,budget,report)
                else:
                    set_chunk(worker,1);report['prefill_chunk']=1
                    rc=generation.run_suite(worker,texts,budget,report)
            need(report['proof'].get('worker_returncode')==0 and report['proof'].get('worker_cleanup_complete') is True
                 and not report['proof'].get('cleanup_diagnostics') and not report['proof'].get('telemetry_errors'),
                 'controlled native worker cleanup differs')
            report['idle_after']=require_idle_gpu()
            need(identity()==source and generation.native.asset_identity('gpt2_q4km')==assets,'controlled source/assets changed')
    except BaseException as exc:
        report['status']='ERROR_NOT_COMPLETE';report['error']=dict(type=type(exc).__name__,message=str(exc)[:2000]);rc=9
    finally:
        report['wire_manifest']=writer.close(lineage=dict(schema=SCHEMA,mode=args.mode,complete=rc==0))
        report.update(exit_code=rc,seconds=time.monotonic()-budget.started,ended_at=datetime.now(timezone.utc).isoformat())
        resource.write_new(output,report);print(json.dumps(dict(status=report['status'],exit_code=rc,seconds=report['seconds'])))
    return rc

if __name__=='__main__':raise SystemExit(main())
