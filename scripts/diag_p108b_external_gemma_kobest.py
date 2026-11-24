"""Pinned existing Gemma runtime and unchanged official KoBEST five tasks."""
import argparse
import gc
import json
import math
import os
from pathlib import Path
import time

from scripts import diag_p108b_external_kobest as task_owner
from scripts import diag_p106b_external_core6 as external
from scripts import diag_p106b_orpo_official as official
from scripts import diag_p108b_value_library as library
from scripts import interactive_research_infer as manual
from scripts import p108b_norm_sweep as limits
from scripts.p106b_shards import ShardWriter, verify as verify_shards

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'test_result/evidence/p108b_layer_transfer_v3_s1337'
PROFILE=BASE/'external_gemma_kobest_profile_v1.json'
INITIAL=BASE/'external_gemma_kobest_initial_plan_v1.md'
OUT=BASE/'external_gemma_kobest_v1'
MODEL='gemma270'
CODE=('scripts/diag_p108b_external_gemma_kobest.py',
      'scripts/diag_p108b_external_kobest.py','scripts/diag_p106b_external_core6.py',
      'scripts/diag_p106b_orpo_official.py','scripts/diag_p106b_official_core6.py',
      'scripts/prepare_p106b_kobest_official_eval.py','scripts/p106b_official_lm_adapter.py',
      'scripts/p106b_official_tasks.py','scripts/p106b_shards.py','scripts/p108b_norm_sweep.py')


def prepare():
    limits.Budget().check()
    loaded,specs,provenance=task_owner.tasks()
    assets=external.asset_identity(MODEL)
    old=json.loads((BASE/'hf_suffix_profile_v1.json').read_text())
    sources=dict(old['sources']['files'])
    sources.update({name:manual.file_sha(ROOT/name)for name in CODE})
    library.write_new(PROFILE,dict(schema='P108B_GEMMA_KOBEST_FIVE_V1',authority_directive=141,
        authority_end=limits.AUTHORITY_END.isoformat(),max_seconds=900,model=MODEL,sources=sources,
        assets=assets,task_specs=specs,framework=provenance,
        actual_counts={name:len(task.eval_docs)for name,task in loaded.items()},
        initial_plan_sha256=manual.file_sha(ROOT/library.PLAN),
        policy=dict(num_fewshot=0,apply_chat_template=False,batch_size=1,max_length=1024,
                    precision='FP32_MATH_TF32_OFF',use_cache=False,bootstrap_iters=0,seed=1337),
        previous_falcon_wrapper_modified=False,training=False,optimizer_updates=0,checkpoint_writes=0))
    with INITIAL.open('xb')as stream:stream.write((ROOT/library.PLAN).read_bytes())
    print('[GEMMA_KOBEST_PREPARED] model0;five official tasks4561;new assets/download0')


def verify():
    p=json.loads(PROFILE.read_text())
    if (p['authority_directive']!=141 or p['authority_end']!=limits.AUTHORITY_END.isoformat() or
            p['model']!=MODEL or p['initial_plan_sha256']!=manual.file_sha(INITIAL)):
        raise ValueError('explicit authority/model/initial plan differs')
    for name,expected in p['sources'].items():
        if manual.file_sha(ROOT/name)!=expected:raise ValueError('frozen source changed: '+name)
    if external.asset_identity(MODEL)!=p['assets']:raise ValueError('existing native HF assets changed')
    loaded,specs,provenance=task_owner.tasks()
    if specs!=p['task_specs']or provenance!=p['framework']:
        raise ValueError('official task/native framework differs')
    return p,loaded,provenance


def actual():
    import torch
    from torch.nn.attention import sdpa_kernel,SDPBackend
    from lm_eval.evaluator import simple_evaluate
    from lm_eval.tasks import TaskManager
    from scripts.p106b_gate_runtime import wall_limit
    p,loaded,provenance=verify()
    budget=limits.Budget(p['max_seconds']);budget.check();library.resources()
    if OUT.exists():raise FileExistsError('preserve prior complete/partial official attempt')
    OUT.mkdir();torch.set_num_threads(4);torch.manual_seed(1337)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    report=dict(schema=p['schema'],model=MODEL,status='STARTED',source_profile_sha256=manual.file_sha(PROFILE),
        policy=p['policy'],framework=provenance,actual_counts={},official_results={},independent_audits={},
        sample_manifests={},training=False,optimizer_updates=0,checkpoint_writes=0,
        metrics_scope='EXTERNAL_KOBEST_BASELINE_NOT_TINYLM_QUALITY_IMPROVEMENT')
    began=time.monotonic();failure=None;lengths=ShardWriter(OUT,'token_lengths')
    try:
        with wall_limit(p['max_seconds']),sdpa_kernel(SDPBackend.MATH),torch.no_grad():
            proof={}
            with external.model_runtime(MODEL,torch,p['assets'],proof=proof)as(lm,_proof):
                report['model_proof']=proof
                report['native_full_softmax_canary']=external.numerical_canary(lm,torch)
                if lm.batch_size!=1 or lm.max_length!=1024:raise ValueError('native HF batch/length differs')
                torch.cuda.reset_peak_memory_stats();manager=TaskManager()
                with task_owner.core.length_observer(lm,lengths)as measured:
                    for name,task in loaded.items():
                        budget.check();tick=time.monotonic()
                        raw=simple_evaluate(model=lm,tasks=[task],num_fewshot=0,task_manager=manager,
                            batch_size=1,device='cuda',use_cache=None,cache_requests=False,limit=None,
                            bootstrap_iters=0,log_samples=True,apply_chat_template=False,fewshot_as_multiturn=False,
                            random_seed=1337,numpy_random_seed=1337,torch_random_seed=1337,fewshot_random_seed=1337)
                        rows=raw.pop('samples')[name];audit=official.audit_task(task,rows,len(task.eval_docs))
                        for metric,key in (('acc','correct'),('acc_norm','correct_norm')):
                            score=raw['results'][name].get(metric+',none')
                            if score is not None and not math.isclose(score,audit[key]/len(rows),abs_tol=1e-12):
                                raise ValueError('independent official accuracy differs')
                        f1=task.aggregation()['f1']([row['f1']for row in rows])
                        if not math.isclose(f1,raw['results'][name]['f1,none'],abs_tol=1e-12):
                            raise ValueError('official macroF1 differs from raw rows')
                        writer=ShardWriter(OUT,name+'_samples')
                        for row in rows:writer.append(task_owner.core.plain(row))
                        manifest=writer.close(lineage=dict(model=MODEL,task=name,framework_commit=official.adapter.COMMIT))
                        verify_shards(OUT,manifest);report['sample_manifests'][name]=manifest
                        report['actual_counts'][name]=len(rows);report['independent_audits'][name]=audit
                        report['official_results'][name]=task_owner.core.plain(raw)
                        print('[GEMMA_KOBEST_TASK] '+json.dumps(dict(task=name,n=len(rows),seconds=time.monotonic()-tick)),flush=True)
                report['token_lengths_summary']=measured
                report.update(peak_allocated_mib=torch.cuda.max_memory_allocated()/1024**2,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/1024**2,
                    peak_scope='POST_LOAD_CANARY_TO_OFFICIAL_TASK_END')
            if report['actual_counts']!=p['actual_counts']:raise ValueError('five task denominators differ')
            report['status']='OFFICIAL_KOBEST_GEMMA_FIVE_COMPLETE'
    except BaseException as error:
        failure=error;report.update(status='GEMMA_KOBEST_ERROR',error_type=type(error).__name__,error=str(error))
    finally:
        if lengths._total_rows:
            report['lengths_manifest']=lengths.close(lineage=dict(model=MODEL))
            verify_shards(OUT,report['lengths_manifest'])
        gc.collect();cleanup_error=library.cleanup(report)
        if failure is None:failure=cleanup_error
        report.update(wall_seconds=time.monotonic()-began,
            source_files_unchanged=all(manual.file_sha(ROOT/n)==s for n,s in p['sources'].items()))
        library.write_new(OUT/'report.json',report)
        print('[GEMMA_KOBEST_END] '+json.dumps({k:report.get(k)for k in('status','wall_seconds','actual_counts','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved external Gemma official failure')from failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('prepare','check','actual'));args=parser.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='check':verify();print('GEMMA_KOBEST_PREFLIGHT_MODEL0')
    else:actual()


if __name__=='__main__':main()
