#!/usr/bin/env python3
"""Current-authority fixed-shape Qwen3.5 canary, cost and official full evaluation."""
import argparse
from datetime import datetime,timezone
import gc
import json
import math
import os
from pathlib import Path
import subprocess
import time
import traceback
from types import FunctionType
import weakref
from scripts import diag_p106b_qwen35_text_core6 as q

ROOT=Path(__file__).resolve().parents[1]
TAG='p106b_qwen35_fixedshape_v1_20261113'
BASE=ROOT/'test_result/evidence'/TAG
DEADLINE=datetime(2026,11,13,8,tzinfo=timezone.utc)
SCHEMA='P106B_QWEN35_FIXEDSHAPE_V1'
SOURCES=('scripts/p106b_qwen35_fixedshape.py','scripts/diag_p106b_qwen35_fixedshape.py',
 'scripts/test_p106b_qwen35_fixedshape.py','scripts/test_p106b_qwen35_fixed_driver.py',
 'scripts/diag_p106b_qwen35_numeric_observer.py','scripts/diag_p107_hybrid_mntp.py')
EVALUATE=FunctionType(q.evaluate.__code__,dict(q.evaluate.__globals__,TAG=TAG),q.evaluate.__name__,q.evaluate.__defaults__)


def write_new(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(obj,stream,ensure_ascii=False,indent=2,allow_nan=False)


def phase_budget(phase,now=None):
    if phase not in ('canary','cost','full'):raise ValueError('explicit registered phase required')
    now=datetime.now(timezone.utc) if now is None else now
    seconds=min({'canary':1200,'cost':1800,'full':30000}[phase],int((DEADLINE-now).total_seconds())-900)
    if seconds<180:raise TimeoutError('phase requires180seconds and15minute authority reserve')
    return seconds


def prepare():
    if BASE.exists():raise FileExistsError('fresh fixedshape namespace required')
    phase_budget('canary')
    for name,value in q.official.OFFLINE.items():os.environ[name]=value
    os.environ['TQDM_DISABLE']='1';os.environ['HF_HUB_DISABLE_PROGRESS_BARS']='1'
    from importlib.metadata import version,PackageNotFoundError
    signature=q.identity();assets=q.asset_identity()
    from scripts.p106b_official_tasks import load_tasks
    tasks,specs,framework=load_tasks()
    deps={}
    for name in ('lm_eval','torch','transformers','safetensors','tokenizers','sqlitedict'):
        try:deps[name]=version(name)
        except PackageNotFoundError:deps[name]='NOT_INSTALLED'
    if deps['sqlitedict']!='NOT_INSTALLED':deps['sqlitedict_note']='present but response cache remains OFF'
    sources={name:q.digest(ROOT/name) for name in SOURCES}
    proof=dict(schema=SCHEMA,tag=TAG,authority_directive=115,deadline=DEADLINE.isoformat(),
        source_identity=signature,sources=sources,assets=assets,framework=framework,task_specs=specs,
        task_names=list(tasks),dependencies=deps,model=q.MODEL,revision=q.REVISION,
        width=1024,pad_id=248044,vocab=248320,precision='FP32_EAGER_TF32_OFF',
        internal_batch='SERIAL_BATCH1_ONLY; external batch2 canary is two batch1 calls',
        response_cache=False,kv_cache=False,atol=q.official.ATOL,rtol=q.official.RTOL,
        no_training=True,optimizer_updates=0,checkpoint_writes=0,download_install_newenv=0)
    write_new(BASE/'profile.json',proof)
    print('[PREPARED] '+json.dumps(dict(tag=TAG,profile_sha256=q.digest(BASE/'profile.json'),dependencies=deps)),flush=True)


def verify():
    p=q.read_json(BASE/'profile.json')
    if p['authority_directive']!=115 or p['deadline']!=DEADLINE.isoformat():raise ValueError('authority mismatch')
    if q.identity()!=p['source_identity'] or q.asset_identity()!=p['assets']:raise ValueError('pinned library/model assets changed')
    q.verify_pins(p['sources'])
    return p


def prerequisite(name,profile_sha):
    directory=BASE/name
    r=q.read_json(directory/'report.json');receipt=q.read_json(BASE/('ROOT_'+name.upper()+'_EXIT_v1.json'))
    if (r.get('status')!='QWEN35_FIXED_'+name.upper()+'_COMPLETE' or r.get('returncode')!=0
            or r.get('profile_sha256')!=profile_sha or not r.get('sources_assets_unchanged')
            or r.get('final_cuda_cleanup',{}).get('allocated_bytes')!=0
            or r.get('final_cuda_cleanup',{}).get('reserved_bytes')!=0
            or r.get('owned_model_alive_after_release')is not False
            or receipt.get('actual_process_exit_code')!=0
            or receipt.get('report_sha256')!=q.digest(directory/'report.json')
            or receipt.get('profile_sha256')!=profile_sha):
        raise ValueError('matching closed prerequisite plus root actual exit0 witness required: '+name)
    if name=='canary' and r.get('fixed_numerical_passed')is not True:raise ValueError('fixed numerical prerequisite missing')
    if name=='cost' and r.get('actual_counts')!=q.official.expected_counts('cost'):raise ValueError('whole official cost requests required')
    return r


def full_forecast(cost,available):
    counts=q.official.TASK_COUNTS;timing=cost.get('task_evaluation_seconds',{})
    if set(timing)!=set(counts) or any(type(s)not in(int,float) or not math.isfinite(s) or s<=0 for s in timing.values()):
        raise ValueError('finite six-task cost timing required')
    forecast=1.5*sum(counts[n]*timing[n]/32 for n in counts)+2*cost['pre_evaluation_seconds']+180
    if forecast>available-120:raise TimeoutError('measured conservative full ETA exceeds current authority/phase budget')
    return dict(seconds=forecast,factor=1.5,available_seconds=available,quality_claim=False)


def numerical_canary(lm,torch,check,report):
    from scripts import p106b_qwen35_fixedshape as fixed
    from scripts.p106b_official_lm_adapter import plan_tokens
    from lm_eval.api.instance import Instance
    literal=lm.tok_decode([lm.prefix_token_id],skip_special_tokens=False)
    cases=[('Question: one plus one?'+chr(10)+'Answer:',' two'),('','Hello'),
           ('질문: 사과의 색은?'+chr(10)+'답:',' 빨강'),('A B C D'+chr(10),' A B'),
           ('',literal+'Hello'),('A',' a longer continuation with several words')]
    requests=[Instance(request_type='loglikelihood',doc={},arguments=pair,idx=i,
        metadata=('fixedshape_numerical_canary',i,1)) for i,pair in enumerate(cases)]
    if not literal or lm.tok_encode(literal+'Hello',add_special_tokens=False)[0]!=248044:
        raise ValueError('literal prefix native ID did not round-trip')
    singles,pairs=q.external.canary_batches(lm,requests)
    report['batch1_serial_batch2_comparison']=q.external.compare_scores(singles,pairs)
    # Independent direct fixed-shape label oracle: do not call the adapter/padding helper.
    direct=[]
    for context,continuation in cases:
        check()
        if context:ctx,cont=lm._encode_pair(context,continuation)
        else:
            cont=lm.tok_encode(continuation,add_special_tokens=False)
            ctx,cont=([lm.prefix_token_id],cont) if cont[0]!=lm.prefix_token_id else (cont[:1],cont[1:])
        plan=plan_tokens(ctx,cont,248320,1024);length=len(plan.input_ids)
        inputs=torch.full((1,1024),248044,dtype=torch.long,device=lm.device)
        mask=torch.zeros((1,1024),dtype=torch.long,device=lm.device)
        labels=torch.full((1,1024),-100,dtype=torch.long,device=lm.device)
        inputs[0,:length]=torch.tensor(plan.input_ids,device=lm.device)
        mask[0,:length]=1;labels[0,:length]=torch.tensor(plan.labels,device=lm.device)
        with torch.no_grad(),torch.autocast(device_type='cuda',enabled=False):
            output=lm.model(input_ids=inputs,attention_mask=mask,use_cache=False,past_key_values=None,logits_to_keep=0)
            logits=output.logits
            if logits.dtype!=torch.float32 or tuple(logits.shape)!=(1,1024,248320) or output.past_key_values is not None:
                raise ValueError('independent direct fixed-shape oracle contract failed')
            loss=torch.nn.functional.cross_entropy(logits.flatten(0,1),labels.flatten(),ignore_index=-100,reduction='sum')
            keep=labels.ne(-100);greedy=bool(logits.argmax(-1)[keep].eq(labels[keep]).all())
        direct.append((-float(loss),greedy));del inputs,mask,labels,output,logits,loss,keep
    report['independent_full_label_ce']=q.external.compare_scores(singles,direct)
    aba1=lm.loglikelihood([requests[0]],disable_tqdm=True)
    lm.loglikelihood([requests[1]],disable_tqdm=True)
    report['aba']=q.external.compare_scores(aba1,lm.loglikelihood([requests[0]],disable_tqdm=True))
    normal=lm.loglikelihood(requests,disable_tqdm=True)
    reverse=lm.loglikelihood(list(reversed(requests)),disable_tqdm=True)
    report['request_order']=q.external.compare_scores(normal,list(reversed(reverse)))
    seed=lm.tok_encode('A causal prefix with words and numbers 123 456.',add_special_tokens=False)
    if not seed:raise ValueError('synthetic nonempty prefix required')
    report['fixed_prefix_checks']=[]
    for length in (6,63,64,65,255,256,257,1008):
        check();ids=(seed*((length+len(seed)-1)//len(seed)))[:length]
        original=lm._model_call(torch.tensor([ids],dtype=torch.long,device=lm.device))
        for label,tail in [('future_a',seed[:2] if length<1008 else (seed*2)[:16]),
                           ('future_b',list(reversed(seed[:3])) if length<1008 else list(reversed((seed*2)[:16])))]:
            check();observed=lm._model_call(torch.tensor([ids+tail],dtype=torch.long,device=lm.device))
            row=dict(length=length,extended_length=length+len(tail),label=label,
                     **fixed.compare_prefix(original,observed,atol=q.official.ATOL,rtol=q.official.RTOL))
            report['fixed_prefix_checks'].append(row);del observed
            if not row['close']:raise ValueError('fixed full-vocabulary future/prefix oracle negative')
        del original
    report['fixed_numerical_passed']=True


def run(phase):
    cap=phase_budget(phase);start=time.perf_counter();p=verify();profile_sha=q.digest(BASE/'profile.json')
    directory=BASE/phase
    if directory.exists():raise FileExistsError('phase already attempted; never overwrite or silently resume')
    directory.mkdir(parents=True)
    report=dict(schema=SCHEMA,tag=TAG,phase=phase,model=q.MODEL,status='RUNNING',returncode=9,
        process_id=os.getpid(),profile_sha256=profile_sha,source_identity=p['source_identity'],quality_claim=False,
        training=False,optimizer_updates=0,checkpoint_writes=0,started_at=datetime.now(timezone.utc).isoformat(),
        authority_deadline=DEADLINE.isoformat(),hard_cap_seconds=cap,contamination='PRETRAINING_OVERLAP_NOT_AUDITED')
    pins={};lm=writer=body_ref=None;torch=None;failure=None;completed_tasks=0
    def check():
        nonlocal completed_tasks
        if time.perf_counter()-start>cap-120 or (DEADLINE-datetime.now(timezone.utc)).total_seconds()<900:
            raise TimeoutError('owned phase/authority cleanup reserve')
        n=len(report.get('actual_counts',{}))
        if n>completed_tasks:
            write_new(directory/f'progress_task_{n}.json',report);completed_tasks=n
    try:
        with q.wall_limit(cap-120):
            if phase!='canary':
                c=prerequisite('canary',profile_sha);report['canary_report_sha256']=q.digest(BASE/'canary/report.json')
                if phase=='full':
                    cost=prerequisite('cost',profile_sha)
                    if cost.get('canary_report_sha256')!=report['canary_report_sha256']:raise ValueError('cost canary lineage mismatch')
                    report['forecast']=full_forecast(cost,cap-(time.perf_counter()-start))
            for name,value in q.official.OFFLINE.items():os.environ[name]=value
            os.environ['TQDM_DISABLE']='1';os.environ['HF_HUB_DISABLE_PROGRESS_BARS']='1'
            import tinylm
            from scripts.p106b_official_tasks import load_tasks
            tasks,specs,framework=load_tasks();report.update(task_specs=specs,framework_provenance=framework)
            if specs!=p['task_specs'] or framework!=p['framework']:raise ValueError('official task/framework drift')
            from scripts.interactive_research_infer import require_idle_gpu
            report['entry_gpu_point']=require_idle_gpu()
            free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],
                check=True,capture_output=True,text=True,timeout=10).stdout.strip()
            if not free.isdigit() or int(free)<12288:raise MemoryError('12288MiB free point required')
            report['entry_free_mib']=int(free)
            import torch
            from torch.nn.attention import sdpa_kernel,SDPBackend
            from scripts import p106b_qwen35_fixedshape as fixed
            from scripts import diag_p106b_qwen35_numeric_observer as observer
            from scripts.p106b_shards import ShardWriter
            torch.set_num_threads(4);torch.manual_seed(1337)
            torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
            torch.cuda.reset_peak_memory_stats();proof=report['model_proof']={}
            writer=ShardWriter(directory,'token_lengths',limit=19_999_999)
            with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                with q.model_runtime(torch,p['assets'],writer,check,proof,p['source_identity']) as lm:
                    body_ref=weakref.ref(lm.model)
                    if phase=='canary':
                        legacy,error=observer.safely(lambda:q.hybrid_canary(lm,torch,check=check))
                        report['legacy_original_shape_control']=dict(result=legacy,error=error,
                            interpretation='separate old-path control; historical negatives never relabeled')
                    stats=report['fixed_call_counts']={}
                    had_call='_model_call'in lm.__dict__;old_call=lm.__dict__.get('_model_call')
                    with fixed.fixed_calls(lm,width=1024,pad_id=248044,check=check,stats=stats):
                        if phase=='canary':numerical_canary(lm,torch,check,report)
                        else:
                            report['length_rows_before_tasks']=writer._total_rows
                            report['pre_evaluation_seconds']=time.perf_counter()-start
                            if phase=='full':report['forecast_after_startup']=full_forecast(cost,cap-(time.perf_counter()-start))
                            EVALUATE(lm,torch,directory,report,tasks,phase,check,pins)
                            if writer._total_rows-report['length_rows_before_tasks']!=report['choice_likelihoods']:
                                raise ValueError('trace must cover every official choice exactly once')
                    report['fixed_call_restored']=('_model_call'in lm.__dict__)==had_call and (not had_call or lm.__dict__['_model_call']is old_call)
                    if not report['fixed_call_restored']:raise ValueError('instance call was not restored')
            lm=None;gc.collect();report['owned_model_alive_after_release']=body_ref()is not None
            if report['owned_model_alive_after_release']:raise RuntimeError('owned Qwen body still alive')
            report.update(status='QWEN35_FIXED_'+phase.upper()+'_COMPLETE',returncode=0,quality_claim=phase=='full')
    except BaseException as exc:
        traceback.print_exc();report.update(status='ERROR',returncode=9,error=repr(exc));failure=RuntimeError(repr(exc))
    finally:
        lm=None;gc.collect()
        if torch is not None:
            report['peak_allocated_bytes']=torch.cuda.max_memory_allocated();report['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
            try:
                from scripts.diag_p107_hybrid_mntp import close_owned_cuda
                close_owned_cuda(torch,report)
            except BaseException as exc:
                report.update(status='ERROR',returncode=9,cleanup_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        if writer is not None:
            try:
                manifest=writer.close(lineage=dict(tag=TAG,model=q.MODEL,phase=phase));q.pin_manifest(directory,'token_lengths',manifest,pins)
                report['length_manifest']=manifest
            except BaseException as exc:
                report.update(status='ERROR',returncode=9,writer_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        try:
            verify();q.verify_pins(pins);report['sources_assets_unchanged']=True
        except BaseException as exc:
            report.update(status='ERROR',returncode=9,source_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        report['wall_seconds']=time.perf_counter()-start;report['finished_at']=datetime.now(timezone.utc).isoformat()
        write_new(directory/'report.json',report)
    if failure is not None:raise failure
    print('[QWEN_FIXED_PHASE_FINAL] '+json.dumps({k:report.get(k) for k in ['phase','status','returncode','wall_seconds','actual_rows','choice_likelihoods']}),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','canary','cost','full']);args=parser.parse_args()
    (prepare() if args.phase=='prepare' else run(args.phase))


if __name__=='__main__':main()
