"""Same official KO/EN Belebele and LAMBADA definitions, qualified fixed Qwen."""
import argparse
from contextlib import contextmanager
from datetime import datetime,timezone
import gc
import json
import os
from pathlib import Path
import subprocess
import time
import traceback
import weakref
from scripts import diag_p106b_qwen35_fixedshape as qfixed
from scripts import diag_p106b_qwen35_legacy_fixed as legacy
from scripts import diag_p106b_actd_topk as actd
from scripts import diag_p106b_belebele as b
from scripts import diag_p106b_lambada_default as l
from scripts import p106b_qwen35_extra as e

ROOT=qfixed.ROOT;TAG='p106b_qwen35_extra_official_v2_20261113';BASE=ROOT/'test_result/evidence'/TAG
PARTIAL=ROOT/'test_result/evidence/p106b_qwen35_extra_official_v1_20261113'
HISTORICAL_SOURCE=ROOT/'handoff/audit/nov13_value_edit/INTERACTIVE_OLD_612D8C4F.py.snapshot'
FAILED_PREPARE=ROOT/'handoff/audit/nov13_value_edit/QWEN_EXTRA_PREPARE_FAILED_v1.json'
SOURCES=('scripts/p106b_qwen35_extra.py','scripts/test_p106b_qwen35_extra.py',
 'scripts/diag_p106b_qwen35_extra.py','scripts/test_p106b_qwen35_extra_driver.py',
 'scripts/diag_p106b_belebele.py','scripts/diag_p106b_lambada_default.py',
 'scripts/summarize_p106b_belebele_pairs.py')
LOAD_LAMBADA=e.private_function(l.load_task,CACHE=BASE/'runtime_cache')


def phase_budget(phase,now=None):
    if phase not in ('prepare','cost','belebele','lambada'):raise ValueError('registered phase required')
    now=datetime.now(timezone.utc) if now is None else now
    cap=min(1800 if phase in ('prepare','cost') else 10800,int((qfixed.DEADLINE-now).total_seconds())-900)
    if cap<180:raise TimeoutError('User115 extra task authority cleanup reserve')
    return cap


def documents_tasks():
    for name,value in qfixed.q.official.OFFLINE.items():os.environ[name]=value
    documents,assets,audit=b.read_assets(allow_download=False)
    tasks,contracts=b.load_tasks(documents)
    lambada,lcontract=LOAD_LAMBADA()
    return documents,tasks,lambada,dict(belebele_assets=assets,belebele_audit=audit,
        belebele_contract=contracts,lambada_assets=l.asset_proof(),lambada_contract=lcontract)


def current_identity():
    baseline=qfixed.q.read_json(b.OUTPUT/'prepare/report.json')['source_identity']['files']
    base=l.identity();proof=e.historical_source_projection(base['files'],baseline,qfixed.q.object_sha,
        expected_base_sha=b.BASE_SOURCE_SHA,allowed_drift={'scripts/interactive_research_infer.py'})
    if qfixed.q.digest(HISTORICAL_SOURCE)!='612D8C4F1302BF539D8FCAD5252FB9D781EA51ED89280B93157A4E351BFDFBCB':
        raise ValueError('historical interactive source snapshot changed')
    proof.update(e.metadata_assignments_only(HISTORICAL_SOURCE.read_text(),(ROOT/'scripts/interactive_research_infer.py').read_text(),
        allowed_names={'MANIFEST','REQUIRED_SOURCES'}))
    files=dict(base['files']);files.update({name:qfixed.q.digest(ROOT/name) for name in b.OWN_FILES})
    for name in ('scripts/diag_p106b_belebele.py','scripts/diag_p106b_lambada_default.py'):
        if files[name]!=baseline[name]:raise ValueError('official evaluator code differs from completed seven-model source')
    return dict(files=files,sha256=qfixed.q.object_sha(files),historical_fixed7_guard_preserved=proof,
        new_runtime='QUALIFIED_QWEN35_FIXED_WIDTH_NOT_LEGACY_FIXED7_MODEL_SELECTOR')


def reuse_closed_token_artifacts(documents):
    from scripts.p106b_shards import verify
    failed=qfixed.q.read_json(FAILED_PREPARE)
    if failed['actual_process_exit_code']!=1 or failed['model_calls']!=0 or failed['gpu_calls']!=0:
        raise ValueError('failed CPU attempt lineage differs')
    pins={};manifest=qfixed.q.read_json(PARTIAL/'token_lengths_shards_manifest.json');verify(PARTIAL,manifest)
    common={b.key_for(doc) for doc in documents[b.LANGUAGES[0]]}
    for part in manifest['shards']:
        for line in (PARTIAL/part['path']).read_text().splitlines():
            row=json.loads(line)
            if not row['untruncated']:common.discard(tuple(row['key']))
    with token_only(qfixed.q.MODEL,pins) as (lm,proof):
        frozen=dict(models=[qfixed.q.MODEL],model_audits={qfixed.q.MODEL:dict(tokenizer_proof=proof)},token_manifest=manifest,
            common_keys=[list(k) for k in sorted(common)],common_rows_per_language=len(common),frozen_before_model_output=True,
            model_instances=0,forward_calls=0,gpu_calls=0,quality_claim=False,
            recovery='CLOSED_TOKEN_SUBARTIFACT_FROM_CPU_EXIT1; ORIGINAL_PREPARE_NOT_RELABELED_PASS')
    b.read_frozen(PARTIAL,frozen,documents,qfixed.q.MODEL,models=(qfixed.q.MODEL,))
    lm_manifest=qfixed.q.read_json(PARTIAL/'lambada_token_lengths_shards_manifest.json');verify(PARTIAL,lm_manifest)
    for name in ('token_lengths','lambada_token_lengths'):
        manifest_path=PARTIAL/(name+'_shards_manifest.json')
        if qfixed.q.digest(manifest_path)!=failed['closed_token_manifest_pins'][str(manifest_path.relative_to(ROOT))]:
            raise ValueError('closed CPU subartifact manifest changed')
        qfixed.q.pin_manifest(PARTIAL,name,qfixed.q.read_json(manifest_path),pins)
    return frozen,lm_manifest,pins


@contextmanager
def token_only(model,pins):
    if model!=qfixed.q.MODEL:raise ValueError('one preregistered new model required')
    p=qfixed.verify();q=qfixed.q
    raw=q.read_json(p['assets']['files']['tokenizer.json']['resolved_path'])
    metadata=q.read_json(p['assets']['files']['tokenizer_config.json']['resolved_path'])
    tokenizer,proof=q.build_tokenizer(raw,metadata)
    q.validate_tokenizer(tokenizer,raw,metadata,q.tokenizer_declarations(raw,metadata))
    from lm_eval.models.huggingface import HFLM
    from lm_eval.api.model import TemplateLM
    lm=b.token_only_hf_type(HFLM,TemplateLM)(tokenizer,248320)
    yield lm,dict(proof,model=model,native_head_vocab=248320,model_loads=0,gpu_calls=0)


def prepare():
    cap=phase_budget('prepare');start=time.perf_counter()
    if BASE.exists():raise FileExistsError('fresh extra evaluation namespace required')
    qfixed.verify();legacy.verify();identity=current_identity();BASE.mkdir(parents=True)
    qfixed.write_new(BASE/'prepare_intent.json',dict(tag=TAG,current_source_identity=identity,
        reused_cpu_subartifact_source=str(PARTIAL.relative_to(ROOT)),model_calls=0,gpu_calls=0,original_cpu_prepare_exit1_preserved=True))
    documents,tasks,lambada,contracts=documents_tasks();pins={}
    frozen,manifest,pins=reuse_closed_token_artifacts(documents)
    references={str((qfixed.BASE/'profile.json').relative_to(ROOT)):qfixed.q.digest(qfixed.BASE/'profile.json'),
        str((legacy.BASE/'profile.json').relative_to(ROOT)):qfixed.q.digest(legacy.BASE/'profile.json')}
    references.update(pins)
    for path in (HISTORICAL_SOURCE,FAILED_PREPARE,b.OUTPUT/'prepare/report.json'):
        references[str(path.relative_to(ROOT))]=qfixed.q.digest(path)
    sources={n:qfixed.q.digest(ROOT/n) for n in SOURCES}
    p=dict(schema='P106B_QWEN35_EXTRA_OFFICIAL_V1',tag=TAG,authority_directive=115,deadline=qfixed.DEADLINE.isoformat(),
        model=qfixed.q.MODEL,sources=sources,references=references,belebele_identity=identity,lambada_identity=l.identity(),
        contracts=contracts,frozen_belebele=frozen,lambada_token_manifest=manifest,
        belebele_token_directory=str(PARTIAL.relative_to(ROOT)),lambada_token_directory=str(PARTIAL.relative_to(ROOT)),
        frozen_lambada_plan_rows=5153,training=False,optimizer_updates=0,checkpoint_writes=0,downloads_installs_newenv=0,
        physical_body_width=1024,internal_batch=1,precision='FP32_EAGER_TF32_OFF',cache=False,
        primary_full_counts=dict(kor_Hang=900,eng_Latn=900,lambada_openai=5153),
        pretraining_overlap='NOT_AUDITED',fair_comparison='SAME_PINNED_TASKS_AND_DATA_NATIVE_TOKENIZATION; PRETRAINING_AND_MODEL_SIZES_NOT_MATCHED')
    frozen_lambada(p)
    qfixed.write_new(BASE/'profile.json',p)
    import torch
    if torch.cuda.is_initialized():raise RuntimeError('CPU task preparation initialized CUDA')
    result=dict(status='EXTRA_OFFICIAL_TOKEN_ONLY_PREPARED',returncode=0,seconds=time.perf_counter()-start,
        profile_sha256=qfixed.q.digest(BASE/'profile.json'),belebele_token_rows=frozen['token_manifest']['rows'],
        qwen_only_common_untruncated=frozen['common_rows_per_language'],lambada_token_rows=5153,
        cuda_initialized=False,quality_claim=False,model_loads=0)
    qfixed.write_new(BASE/'prepare_report.json',result)
    print('[QWEN_EXTRA_PREPARED] '+json.dumps(result),flush=True)


def verify():
    qfixed.verify();legacy.verify();p=qfixed.q.read_json(BASE/'profile.json')
    if p['deadline']!=qfixed.DEADLINE.isoformat() or p['authority_directive']!=115:raise ValueError('extra current authority changed')
    qfixed.q.verify_pins(p['sources']);qfixed.q.verify_pins(p['references'])
    if p['belebele_identity']!=current_identity() or p['lambada_identity']!=l.identity():raise ValueError('official task evaluator source changed')
    return p


def frozen_lambada(p):
    from scripts.p106b_shards import verify
    directory=ROOT/p['lambada_token_directory']
    verify(directory,p['lambada_token_manifest']);plans={};seen=[]
    for part in p['lambada_token_manifest']['shards']:
        for line in (directory/part['path']).read_text().splitlines():
            row=json.loads(line);seen.append(row['doc_id'])
            key=row['arguments_sha256']
            if key in plans and plans[key]!=row['plan']:raise ValueError('duplicate argument token plan conflict')
            plans[key]=row['plan']
    if seen!=list(range(5153)):raise ValueError('all5153 pre-output token plans required')
    return plans


def cost_prerequisite():
    r=qfixed.q.read_json(BASE/'cost/report.json');w=qfixed.q.read_json(BASE/'ROOT_COST_EXIT_v1.json')
    if (r.get('status')!='QWEN_EXTRA_COST_COMPLETE' or r.get('returncode')!=0
            or not r.get('sources_assets_unchanged') or r.get('owned_model_alive_after_release')is not False
            or r.get('profile_sha256')!=qfixed.q.digest(BASE/'profile.json')
            or r.get('final_cuda_cleanup',{}).get('allocated_bytes')!=0 or r.get('final_cuda_cleanup',{}).get('reserved_bytes')!=0
            or w.get('actual_process_exit_code')!=0 or w.get('report_sha256')!=qfixed.q.digest(BASE/'cost/report.json')):
        raise ValueError('same-profile complete cost plus actual root exit0 required')
    return r


def run(phase):
    cap=phase_budget(phase);p=verify();start=time.perf_counter()
    qfixed.prerequisite('full',qfixed.q.digest(qfixed.BASE/'profile.json'));actd.legacy_prerequisite()
    cost=None
    if phase!='cost':cost=cost_prerequisite();forecast=e.admission(cost,phase,cap)
    directory=BASE/phase
    if directory.exists():raise FileExistsError('extra phase already attempted')
    directory.mkdir();report=dict(schema=p['schema'],tag=TAG,model=qfixed.q.MODEL,phase=phase,status='RUNNING',returncode=9,
        profile_sha256=qfixed.q.digest(BASE/'profile.json'),training=False,optimizer_updates=0,checkpoint_writes=0,
        quality_claim=False,started_at=datetime.now(timezone.utc).isoformat(),actual_counts={},task_seconds={})
    if cost is not None:report['forecast']=forecast
    lm=writer=ref=torch=None;failure=None;pins={}
    def check():
        if time.perf_counter()-start>cap-120 or (qfixed.DEADLINE-datetime.now(timezone.utc)).total_seconds()<900:
            raise TimeoutError('extra official phase/authority cleanup reserve')
    try:
        with qfixed.q.wall_limit(cap-120):
            documents,tasks,lambada,contracts=documents_tasks()
            if contracts!=p['contracts']:raise ValueError('official datasets/tasks changed after token freeze')
            plans,common=b.read_frozen(ROOT/p['belebele_token_directory'],p['frozen_belebele'],documents,qfixed.q.MODEL,models=(qfixed.q.MODEL,))
            lplans=frozen_lambada(p)
            from scripts.interactive_research_infer import require_idle_gpu
            report['entry_gpu_point']=require_idle_gpu()
            free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],check=True,capture_output=True,text=True,timeout=10).stdout.strip()
            if not free.isdigit() or int(free)<12288:raise MemoryError('extra Qwen needs12288MiB free point')
            import torch
            from torch.nn.attention import sdpa_kernel,SDPBackend
            from scripts.p106b_shards import ShardWriter
            from scripts import p106b_qwen35_fixedshape as fixed
            torch.set_num_threads(4);torch.manual_seed(1337)
            torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
            torch.cuda.reset_peak_memory_stats();qp=qfixed.verify();proof=report['model_proof']={}
            writer=ShardWriter(directory,'token_lengths',limit=19_999_999);stats=report['fixed_calls']={}
            had_call=old_call=None
            with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                with qfixed.q.model_runtime(torch,qp['assets'],writer,check,proof,qp['source_identity']) as lm:
                    ref=weakref.ref(lm.model);had_call='_model_call'in lm.__dict__;old_call=lm.__dict__.get('_model_call')
                    with fixed.fixed_calls(lm,width=1024,pad_id=248044,check=check,stats=stats):
                        report['pre_evaluation_seconds']=time.perf_counter()-start
                        if cost is not None:report['forecast_after_startup']=e.admission(cost,phase,cap-(time.perf_counter()-start))
                        if phase=='cost':report['lambada_boundary_canary']=l.boundary_canary(lambada,lm)
                        if phase in ('cost','belebele'):
                            sub=directory/'belebele';sub.mkdir();task_report=dict(model=qfixed.q.MODEL)
                            b.evaluate(tasks,documents,lm,qfixed.q.MODEL,'cost' if phase=='cost' else 'full',sub,task_report,check,plans,common)
                            qfixed.write_new(sub/'report.json',task_report);report['belebele']=task_report
                            for language,manifest in task_report['sample_manifests'].items():
                                qfixed.q.pin_manifest(sub,language+'_samples',manifest,pins)
                            report['actual_counts'].update(task_report['actual_counts']);report['task_seconds'].update(task_report['evaluation_seconds'])
                        if phase in ('cost','lambada'):
                            sub=directory/'lambada';sub.mkdir();task_report=dict(model=qfixed.q.MODEL)
                            callback=e.matching_plan_callback(l.token_plan,lplans,qfixed.q.object_sha)
                            evaluate=e.private_function(l.evaluate,token_plan=callback)
                            evaluate(lambada,lm,'cost' if phase=='cost' else 'full',sub,task_report,check)
                            qfixed.write_new(sub/'report.json',task_report);report['lambada']=task_report
                            qfixed.q.pin_manifest(sub,'samples',task_report['sample_manifest'],pins)
                            report['actual_counts'][l.TASK]=task_report['actual_rows'];report['task_seconds'][l.TASK]=task_report['evaluation_seconds']
                    report['fixed_call_restored']=('_model_call'in lm.__dict__)==had_call and (not had_call or lm.__dict__['_model_call']is old_call)
                    if not report['fixed_call_restored']:raise ValueError('owned instance scorer not restored')
            lm=None;gc.collect();report['owned_model_alive_after_release']=ref()is not None
            if report['owned_model_alive_after_release']:raise RuntimeError('owned Qwen still alive')
            report.update(status='QWEN_EXTRA_'+phase.upper()+'_COMPLETE',returncode=0,quality_claim=phase!='cost')
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
                report['length_manifest']=writer.close(lineage=dict(tag=TAG,phase=phase))
                qfixed.q.pin_manifest(directory,'token_lengths',report['length_manifest'],pins)
            except BaseException as exc:
                report.update(status='ERROR',returncode=9,writer_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        try:verify();qfixed.q.verify_pins(pins);report['sources_assets_unchanged']=True
        except BaseException as exc:
            report.update(status='ERROR',returncode=9,source_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        report.update(seconds=time.perf_counter()-start,finished_at=datetime.now(timezone.utc).isoformat())
        qfixed.write_new(directory/'report.json',report)
    if failure is not None:raise failure
    print('[QWEN_EXTRA_FINAL] '+json.dumps({k:report[k] for k in ['phase','status','returncode','seconds','actual_counts']}),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','cost','belebele','lambada']);a=parser.parse_args()
    (prepare() if a.phase=='prepare' else run(a.phase))


if __name__=='__main__':main()
