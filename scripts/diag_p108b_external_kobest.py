#!/usr/bin/env python3
"""Existing strict Falcon runtime and unchanged official five KoBEST tasks."""
import argparse
import gc
import json
import math
import os
import time
from pathlib import Path
import torch
from torch.nn.attention import sdpa_kernel,SDPBackend
from scripts import diag_p106b_orpo_official as official
from scripts import diag_p106b_official_core6 as core
from scripts import prepare_p106b_kobest_official_eval as kobest
from scripts import diag_p108b_value_library as library
from scripts import diag_p108b_geometry as atlas
from scripts import interactive_research_infer as manual
from scripts.p106b_shards import ShardWriter,verify as verify_shards

BASE=atlas.BASE
OUT=BASE/'external_kobest_v1'
PROFILE=BASE/'external_kobest_profile_v1.json'
INITIAL=BASE/'external_kobest_initial_plan_v1.md'
CODE=('scripts/diag_p108b_external_kobest.py','scripts/test_p108b_external_kobest.py',
      'scripts/diag_p106b_orpo_official.py','scripts/diag_p106b_official_core6.py',
      'scripts/prepare_p106b_kobest_official_eval.py','scripts/p106b_official_lm_adapter.py',
      'scripts/p106b_official_tasks.py','scripts/p106b_shards.py')

def select_tasks(tasks,expected):
    selected={n:t for n,t in tasks.items()if n.startswith('kobest_')}
    actual={n:len(t.eval_docs)for n,t in selected.items()}
    if actual!=expected or len(actual)!=5 or sum(actual.values())!=4561:
        raise ValueError('the exact five official tasks and4561 test rows are required')
    return selected

def tasks():
    os.environ.update(core.OFFLINE,HF_EVALUATE_OFFLINE='1')
    loaded,specs,provenance=official.load_tasks()
    expected={'kobest_'+name:spec[0]for name,spec in kobest.SPECS.items()}
    return select_tasks(loaded,expected),core.plain(specs),core.plain(provenance)

def prepare():
    loaded,specs,provenance=tasks()
    if core.digest(core.FALCON_REFERENCE)!=core.FALCON_REFERENCE_SHA:
        raise ValueError('existing strict Falcon asset receipt differs')
    library.write_new(PROFILE,dict(schema='P108B_EXISTING_FALCON_KOBEST_V1',authority_directive=140,
        deadline=library.DEADLINE.isoformat(),sources={n:manual.file_sha(atlas.ROOT/n)for n in CODE},
        task_specs=specs,framework=provenance,actual_counts={n:len(t.eval_docs)for n,t in loaded.items()},
        model='falcon90m',model_reference_sha256=core.FALCON_REFERENCE_SHA,max_seconds=900,
        policy=dict(core.policy(),bootstrap_iters=0,tasks='OFFICIAL_KOBEST_FIVE_TEST_ONLY'),
        initial_plan_sha256=manual.file_sha(atlas.ROOT/library.PLAN)))
    with INITIAL.open('xb')as stream:stream.write((atlas.ROOT/library.PLAN).read_bytes())
    print('[FALCON_KOBEST_PREPARED] exact five tasks4561; no model loading')

def verify():
    p=json.loads(PROFILE.read_text())
    if(p['authority_directive']!=140 or p['deadline']!=library.DEADLINE.isoformat()or
       p['initial_plan_sha256']!=manual.file_sha(INITIAL)):
        raise ValueError('native authority and initial plan differ')
    for name,sha in p['sources'].items():
        if manual.file_sha(atlas.ROOT/name)!=sha:raise ValueError('official wrapper/source changed: '+name)
    loaded,specs,provenance=tasks()
    if specs!=p['task_specs']or provenance!=p['framework']:raise ValueError('fixed official task signature differs')
    return p,loaded,provenance

def run_model(p,loaded,provenance,target):
    from lm_eval.evaluator import simple_evaluate
    from lm_eval.tasks import TaskManager
    from scripts.p106b_gate_runtime import wall_limit
    result=dict(policy=p['policy'],framework=provenance,framework_commit=official.adapter.COMMIT,
        actual_counts={},official_results={},independent_audits={},sample_manifests={},training=False,
        optimizer_updates=0,checkpoint_writes=0,metrics_scope='EXTERNAL_BASELINE_NOT_TINYLM_IMPROVEMENT')
    manager=TaskManager();lengths=ShardWriter(target,'token_lengths')
    try:
        with wall_limit(p['max_seconds']),sdpa_kernel(SDPBackend.MATH),torch.no_grad():
            with core.model_runtime('falcon90m',torch)as(lm,proof):
                result['model_proof']=proof;result['native_likelihood_canary']=core.numerical_canary(lm,torch)
                torch.cuda.reset_peak_memory_stats()
                with core.length_observer(lm,lengths)as measured:
                    for name,task in loaded.items():
                        tick=time.monotonic()
                        raw=simple_evaluate(model=lm,tasks=[task],num_fewshot=0,task_manager=manager,
                            batch_size=8,device='cuda',use_cache=None,cache_requests=False,limit=None,
                            bootstrap_iters=0,log_samples=True,apply_chat_template=False,fewshot_as_multiturn=False,
                            random_seed=1337,numpy_random_seed=1337,torch_random_seed=1337,fewshot_random_seed=1337)
                        rows=raw.pop('samples')[name];audit=official.audit_task(task,rows,len(task.eval_docs))
                        for metric,key in [('acc','correct'),('acc_norm','correct_norm')]:
                            point=raw['results'][name].get(metric+',none')
                            if point is not None and not math.isclose(point,audit[key]/len(rows),abs_tol=1e-12):
                                raise ValueError('official accuracy differs from independent raw audit')
                        f1=task.aggregation()['f1']([r['f1']for r in rows])
                        if not math.isclose(f1,raw['results'][name]['f1,none'],abs_tol=1e-12):raise ValueError('official macroF1 differs')
                        writer=ShardWriter(target,name+'_samples')
                        for row in rows:writer.append(core.plain(row))
                        manifest=writer.close(lineage=dict(model='falcon90m',task=name,framework_commit=official.adapter.COMMIT))
                        verify_shards(target,manifest);result['sample_manifests'][name]=manifest
                        result['official_results'][name]=core.plain(raw);result['independent_audits'][name]=audit
                        result['actual_counts'][name]=len(rows)
                        print('[FALCON_KOBEST_TASK] '+json.dumps(dict(task=name,n=len(rows),seconds=time.monotonic()-tick)),flush=True)
                result['token_lengths_summary']=measured
                result.update(peak_allocated_mib=torch.cuda.max_memory_allocated()/1024**2,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/1024**2,peak_scope='POST_LOAD_CANARY_TO_OFFICIAL_TASK_END')
        result['status']='OFFICIAL_KOBEST_FALCON_FIVE_COMPLETE'
    except TimeoutError as error:result.update(status='BUDGET_HOLD',reason=str(error))
    finally:
        if lengths._total_rows:
            result['lengths_manifest']=lengths.close(lineage=dict(model='falcon90m'))
            verify_shards(target,result['lengths_manifest'])
        library.write_new(target/'task_closures.json',result)
    return result

def actual():
    p,loaded,provenance=verify();library.resources();library.Budget(p['max_seconds']).check()
    if OUT.exists():raise FileExistsError('preserve prior external evaluation attempt')
    OUT.mkdir();torch.set_num_threads(4);torch.manual_seed(1337)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    started=time.monotonic();failure=None;report=dict(status='STARTED',source_profile_sha256=manual.file_sha(PROFILE))
    try:report.update(run_model(p,loaded,provenance,OUT))
    except BaseException as error:failure=error;report.update(status='FALCON_KOBEST_ERROR',error=str(error))
    finally:
        gc.collect();cleanup_error=library.cleanup(report)
        if failure is None:failure=cleanup_error
        report['wall_seconds']=time.monotonic()-started;library.write_new(OUT/'report.json',report)
        print('[FALCON_KOBEST_END] '+json.dumps({k:report.get(k)for k in('status','wall_seconds','actual_counts','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved external official evaluation failure')from failure
    if report['status']=='BUDGET_HOLD':raise SystemExit(8)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','actual']);a=parser.parse_args()
    if a.phase=='prepare':prepare()
    elif a.phase=='check':verify();print('FALCON_KOBEST_CPU_PREFLIGHT_MODEL0')
    else:actual()

if __name__=='__main__':main()
