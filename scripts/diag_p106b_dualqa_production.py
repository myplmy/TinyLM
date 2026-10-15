#!/usr/bin/env python3
"""Sealed source-job windows for paired curriculum; all old artifacts read-only."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from contextlib import ExitStack,contextmanager
from datetime import datetime,timezone
import json
import time
from unittest.mock import patch
from scripts import p106b_dualqa_sources as data
from scripts import diag_p106b_dualqa_optional_note as adapter
from scripts import diag_p106b_dualqa_teacher as legacy
from scripts import p106b_dualqa_optional_note as parser
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
from scripts.p106b_memory_stream import PersistentMemory,stream_session_scope
from scripts.p106b_gemma_telemetry_resume import RetryingMemoryReader
TAG='p106b_dualqa_corpus_v1_s1337'
OUTPUT=ROOT/'HF/sft_ready'/TAG
EVIDENCE=ROOT/'test_result/evidence'/TAG
PARENT=ROOT/'runs/ckpt/m100s10_ko-en_grounded_span_dense_chat32_p106b_grounded_span_exec_v3_s1337_span0.pt'
PARENT_SHA='180104A965CAA84379802D9862A74B59895537EB8B8905DA6E0AA84293E91337'
CODE=(*adapter.CODE,'scripts/p106b_dualqa_sources.py','scripts/test_p106b_dualqa_sources.py',
      'scripts/diag_p106b_dualqa_production.py','scripts/test_p106b_dualqa_production.py')
BATCH_SIZE=32
ORIGINAL_PAYLOAD=legacy.method.payload


def info():
    return dict(schema='P106B_DUAL_QA_SEALED_PRODUCTION_V1',tag=TAG,
        code_sha256={p:legacy.source.public.digest(ROOT/p) for p in sorted(set(CODE))},
        parent=str(PARENT.relative_to(ROOT)),parent_sha256=PARENT_SHA,tokenizer_sha256=legacy.source.public.TOK_SHA,
        targets=data.TARGETS,reserves=data.RESERVES,pairs_per_context=2,batch_contexts=BATCH_SIZE,
        teacher_mtp=True,draft_max=2,teacher_context=legacy.method.CONTEXT,
        teacher_output_cap=legacy.method.MAX_OUTPUT,teacher_requested_thinking_cap=legacy.method.THINKING,
        sampler=legacy.teacher.SAMPLER,shared_attempts=3,semantic_filter=False,
        original_sources_changed=False,student_training=False,formal_train_ready=False,
        test_text_hidden_during_production=True,source_max_tokens=data.SOURCE_TOKEN_LIMIT,
        source_second_user_scope='CODE_SOURCE_SCOPE_V1',deadline_utc=legacy.source.DEADLINE.isoformat())


def freeze():
    from tokenizers import Tokenizer
    legacy.source.deadline()
    if OUTPUT.exists() or EVIDENCE.exists():raise GateNegative('old production namespace preserved')
    if legacy.source.public.digest(PARENT)!=PARENT_SHA:raise ValueError('selected initializer changed')
    if legacy.source.public.digest(legacy.source.public.TOKENIZER)!=legacy.source.public.TOK_SHA:raise ValueError('student tokenizer changed')
    tok=Tokenizer.from_file(str(legacy.source.public.TOKENIZER));jobs,supply=data.deck(tok,TAG)
    OUTPUT.mkdir(parents=True,exist_ok=False);w=ShardWriter(OUTPUT,'jobs')
    for job in jobs:w.append(job)
    manifest=w.close(lineage=info());verify(OUTPUT,manifest)
    r=dict(info(),status='SOURCE_JOBS_FROZEN',jobs_manifest=manifest,supply=supply,jobs=len(jobs),
        target_total=sum(data.TARGETS.values())*2,source_jobs_sha256=manifest['concat_sha256'],
        scope='paired teaching curriculum, not75M or new independent world benchmark')
    legacy.source.training.write(OUTPUT/'inputs.json',r);legacy.source.training.write(EVIDENCE/'inputs.json',r)
    print('[DUALQA_PRODUCTION_SOURCES] '+json.dumps(dict(jobs=len(jobs),supply=supply,target_total=r['target_total'])),flush=True)
    return 0


def state():
    r=legacy.source.required(OUTPUT/'inputs.json')
    if r['code_sha256']!=info()['code_sha256']:raise ValueError('frozen producer code changed')
    jobs=list(legacy.source.public.stream_rows(OUTPUT,r['jobs_manifest']));processed=set();counts=Counter();refs=[]
    for directory in sorted(OUTPUT.glob('batch_*')):
        rp=directory/'report.json'
        if not rp.is_file():raise GateNegative('unsealed prior batch preserved; inspect before new version')
        b=legacy.source.required(rp)
        if b['code_sha256']!=r['code_sha256'] or b['source_jobs_sha256']!=r['source_jobs_sha256']:
            raise ValueError('batch source/code differs')
        if b['raw_manifest']:verify(directory,b['raw_manifest'])
        if b['candidate_manifest']:verify(directory,b['candidate_manifest'])
        for item in b['results']:
            if item['root'] in processed:raise ValueError('source repeated across sealed windows')
            processed.add(item['root'])
            if item['accepted']:counts[item['split']+':'+item['language']]+=1
        refs.append(dict(path=str(rp.relative_to(ROOT)),sha256=legacy.source.public.digest(rp)))
    return r,jobs,processed,counts,refs


def quotas_met(counts):return all(counts[s+':'+l]>=n for s,n in data.TARGETS.items() for l in ('ko','en'))


def next_jobs(jobs,processed,counts):
    return [j for j in jobs if j['root'] not in processed and counts[j['split']+':'+j['language']]<data.TARGETS[j['split']]]


def emit_factory(jobs):
    hidden={j['root'] for j in jobs if j['split']=='test'}
    def emit(line,*args,**kwargs):
        prefix='[DUALQA_TEACHER_ANSWER] '
        if isinstance(line,str) and line.startswith(prefix):
            value=json.loads(line[len(prefix):])
            if value.get('root') in hidden:
                value['fields']='FROZEN_TEST_CONTENT_HIDDEN_UNTIL_EVALUATION'
                line=prefix+json.dumps(value,ensure_ascii=False)
        if isinstance(line,str) and line.startswith('[DUALQA_BACKEND_ERROR] '):
            value=json.loads(line[len('[DUALQA_BACKEND_ERROR] '):])
            if value.get('root') in hidden:
                for key in ('message','body_excerpt'):value.get('error',{}).pop(key,None)
                line='[DUALQA_BACKEND_ERROR] '+json.dumps(value)
        print(line,*args,**kwargs)
    return emit


@contextmanager
def producer_scope(jobs):
    with ExitStack() as stack:
        stack.enter_context(patch.object(legacy,'TAG',TAG))
        stack.enter_context(patch.object(legacy,'print',emit_factory(jobs),create=True))
        stack.enter_context(patch.object(legacy.method,'messages',parser.messages))
        stack.enter_context(patch.object(legacy.method,'parse_fields',parser.parse_fields))
        stack.enter_context(patch.object(legacy.method,'wrap',data.render))
        stack.enter_context(patch.object(legacy.teacher,'THINKING',legacy.method.THINKING))
        yield


def run(args):
    from tokenizers import Tokenizer
    r,jobs,processed,accepted,refs=state()
    if quotas_met(accepted):raise GateNegative('all quotas already complete; no repeated generation')
    if not next_jobs(jobs,processed,accepted):raise GateNegative('source reserves exhausted; no repeated prompt refill')
    idle_before_gpu();tok=Tokenizer.from_file(str(legacy.source.public.TOKENIZER));start=time.perf_counter()
    index=len(refs);window_index=len(list(EVIDENCE.glob('window_*.json')));batch=None;raw=canonical=None;results=[];counters=Counter()
    window_records=[];error=None;pause=False;assets=None;metrics={};active_job=None
    def open_batch():
        nonlocal batch,raw,canonical,results,counters
        batch=OUTPUT/f'batch_{index:06d}';batch.mkdir(exist_ok=False)
        raw=ShardWriter(batch,'raw');canonical=ShardWriter(batch,'candidates');results=[];counters=Counter()
    def seal(status):
        nonlocal index,batch
        if batch is None:return
        rm=raw.close(lineage=info()) if raw._total_rows else None
        cm=canonical.close(lineage=info()) if canonical._total_rows else None
        b=dict(info(),source_jobs_sha256=r['source_jobs_sha256'],status=status,results=results,
            counts=dict(counters),raw_manifest=rm,candidate_manifest=cm,assets=assets,
            candidate_count=canonical._total_rows,raw_record_count=raw._total_rows,
            attempt_policy='processed/declined/exhausted/operation-abandoned roots never restarted in another window')
        legacy.source.training.write(batch/'report.json',b)
        window_records.append(dict(path=str((batch/'report.json').relative_to(ROOT)),sha256=legacy.source.public.digest(batch/'report.json')))
        index+=1;batch=None
    try:
        with wall_limit(args.max_wall_sec),producer_scope(jobs):
            assets=legacy.teacher.assets(True)
            with PersistentMemory() as memory:
                reader=RetryingMemoryReader(memory,emit=lambda line:print(line,flush=True))
                with stream_session_scope(reader),legacy.teacher.GemmaSession(True) as session:
                    for job in jobs:
                        if job['root'] in processed or accepted[job['split']+':'+job['language']]>=data.TARGETS[job['split']]:continue
                        legacy.source.deadline()
                        if args.max_wall_sec-(time.perf_counter()-start)<600:pause=True;break
                        if batch is None:open_batch()
                        active_job=job
                        one=legacy.one_job(session,job,2,0,tok,raw,canonical,counters)
                        one.update(split=job['split']);results.append(one);processed.add(job['root'])
                        if one['accepted']:accepted[job['split']+':'+job['language']]+=1
                        active_job=None
                        if len(results)>=BATCH_SIZE:seal('SEALED_BATCH')
                        if len(processed)%32==0:print('[DUALQA_PRODUCTION_PROGRESS] '+json.dumps(dict(accepted=dict(accepted),processed=len(processed),elapsed_sec=time.perf_counter()-start)),flush=True)
                        if quotas_met(accepted):break
                    metrics=dict(memory=session.memory(),telemetry=reader.snapshot(),persistent=memory.snapshot())
        seal('SEALED_WINDOW_TAIL')
    except BaseException as exc:
        import traceback
        traceback.print_exc();error=dict(type=type(exc).__name__,reason=str(exc)[:1500])
        if batch is not None and active_job is not None:
            # Do not reset a partial root's structural budget after interruption.
            results.append(dict(root=active_job['root'],language=active_job['language'],split=active_job['split'],accepted=False,
                declined=False,status='OPERATION_ABANDONED_NO_AUTOMATIC_RETRY',physical_attempts_may_be_partial=True))
        seal('SEALED_OPERATION_ERROR')
    ready=quotas_met(accepted);status='TEACHER_SOURCE_QUOTAS_COMPLETE' if ready and error is None else 'OPERATION_ERROR' if error else 'PAUSED_WINDOW_BUDGET' if pause else 'SOURCE_RESERVES_EXHAUSTED'
    result=dict(info(),status=status,source_jobs_sha256=r['source_jobs_sha256'],accepted=dict(accepted),
        target_total=sum(data.TARGETS.values())*2,completed_contexts=sum(accepted.values()),
        window_batches=window_records,prior_batches=refs,error=error,metrics=metrics,
        whole_sec=time.perf_counter()-start,source_quota_complete=ready and error is None,
        source_data_quota_met=ready,operational_error_does_not_erase_sealed_data=error is not None,
        world_truth='NOT_RUN',student_training=False,normal_pause_is_not_model_quality_failure=True)
    legacy.source.training.write(EVIDENCE/f'window_{window_index:06d}.json',result)
    print('[DUALQA_PRODUCTION_FINAL] '+json.dumps(dict(status=status,accepted=dict(accepted),completed_contexts=sum(accepted.values()),whole_sec=result['whole_sec'])),flush=True)
    return (130 if error['type']=='KeyboardInterrupt' else 9) if error else 0 if ready else 8


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('freeze','generate','status'),required=True)
    p.add_argument('--max-wall-sec',type=int,default=14400)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 600<=a.max_wall_sec<=21600:p.error('bounded600..21600')
    try:
        if a.check_only:print('[DUALQA_PRODUCTION_CHECK_ONLY] '+json.dumps(info()));return 0
        if not a.execute:p.error('explicit execution required')
        if a.mode=='status':
            r,jobs,processed,counts,refs=state();print('[DUALQA_SOURCE_STATUS] '+json.dumps(dict(accepted=dict(counts),processed=len(processed),quota_complete=quotas_met(counts),batches=len(refs))));return 0
        legacy.source.deadline()
        if a.mode=='freeze':return freeze()
        a.max_wall_sec=min(a.max_wall_sec,int((legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds())-2700)
        if a.max_wall_sec<600:raise GateNegative('closing margin before authorized deadline')
        return run(a)
    except GateNegative as exc:print('[DUALQA_PRODUCTION_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[DUALQA_PRODUCTION_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
