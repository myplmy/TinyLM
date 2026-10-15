#!/usr/bin/env python3
"""Same-source1QA/2QA Gemma-MTP pilot, write-once, no student training."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from datetime import datetime,timezone
import json
import time
from urllib.error import HTTPError
from unittest.mock import patch
from scripts import p106b_dualqa_teacher as method
from scripts import p106b_gemma_teacher as teacher
from scripts import diag_p106b_grounded_span as source
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
from scripts.p106b_memory_stream import PersistentMemory,stream_session_scope
from scripts.p106b_gemma_telemetry_resume import RetryingMemoryReader
from scripts.diag_p106b_gemma_ac import count_prompt
from scripts.p106b_http_errors import capture_http_error
TAG='p106b_dualqa_teacher_pilot_v1_s1337'
OUTPUT=ROOT/'HF/sft_ready'/TAG
EVIDENCE=ROOT/'test_result/evidence'/TAG
CODE=(*source.CODE,'scripts/p106b_dualqa_teacher.py','scripts/diag_p106b_dualqa_teacher.py',
      'scripts/test_p106b_dualqa_teacher.py','scripts/p106b_gemma_teacher.py','scripts/p106b_memory_stream.py',
      'scripts/p106b_gemma_telemetry_resume.py','scripts/diag_p106b_gemma_telemetry_resume.py',
      'scripts/diag_p106b_gemma_ac.py','scripts/diag_p106b_qwen_coload.py','scripts/p106b_qwen_teacher.py',
      'scripts/p106b_gate_runtime.py','scripts/diag_p106b_mtp_teacher.py','scripts/p106b_mtp_teacher.py',
      'scripts/diag_p106b_online_rate5.py','scripts/diag_p106_bonsai_assets.py',
      'scripts/diag_p106_vram_sample.py','scripts/p106b_http_errors.py')


def jobs(tok):
    r,rows,_=source.read_course();result=[]
    for language in ('ko','en'):
        values=[x for x in rows['train'] if x['meta']['kind']=='natural_first_qa' and x['meta']['language']==language]
        values.sort(key=lambda x:method.sha([TAG,x['meta']['semantic_root_id']]))
        for row in values:
            ref=row['meta']['original_first_pair']['reference']
            if len(tok.encode(ref).ids)>768:continue
            m=row['meta'];result.append(dict(root=m['semantic_root_id'],language=language,reference=ref,
                provenance={k:m[k] for k in ('source_repo','source_revision','source_id','source_family','source_license','source_sha256') if k in m}))
            if sum(x['language']==language for x in result)==4:break
    if len(result)!=8:raise ValueError('eight bounded train-only source contexts required')
    result.sort(key=lambda x:(x['root'],x['language']))
    return result,r


def info():
    return dict(schema='P106B_DUAL_QA_TEACHER_PILOT_V1',tag=TAG,
        code_sha256={p:source.public.digest(ROOT/p) for p in sorted(set(CODE))},
        source_corpus_sha256=source.public.digest(source.CORPUS/'report.json'),tokenizer_sha256=source.public.TOK_SHA,
        teacher_sampler=teacher.SAMPLER,teacher_mtp=True,teacher_draft_max=2,teacher_context=method.CONTEXT,
        teacher_output_cap=method.MAX_OUTPUT,teacher_requested_thinking_cap=method.THINKING,
        original_global_thinking_constant_unchanged=True,pair_counts=[1,2],orders=[[1,2],[2,1]],
        source_contexts=8,planned_original_requests=32,shared_total_attempts=method.MAX_ATTEMPTS,
        student_training=False,checkpoint_saved=False,formal_train_ready=False,semantic_truth='NOT_RUN',
        pilot_candidates_not_for_training=True,source_is_shared_verbatim=True,source_not_hidden_original_QA=True,
        native_actual_thinking_tokens='only report if server usage supplies them; never student-tokenizer inference',
        deadline_utc=source.DEADLINE.isoformat())


def one_job(session,job,n,order,tok,raw,canonical,counters):
    feedback='';result=dict(root=job['root'],language=job['language'],accepted=False,declined=False,attempts=0)
    for attempt in range(1,method.MAX_ATTEMPTS+1):
        source.deadline();session.check();seed=int(method.sha([TAG,job['root'],attempt])[:12],16)%(2**31-1)
        request=method.payload(job,n,seed,feedback);ref=job['reference']
        if request['messages'][1]['content'].count(ref)!=1:raise ValueError('one exact teacher reference copy required')
        phase='INPUT_BUDGET';budget=None;tick=time.perf_counter()
        try:
            budget=count_prompt(session,request['messages'],method.CONTEXT,method.MAX_OUTPUT)
            phase='GENERATION_HTTP';tick=time.perf_counter()
            reply=session.request('/v1/chat/completions',request,timeout=180);seconds=time.perf_counter()-tick
        except HTTPError as exc:
            seconds=time.perf_counter()-tick;backend=capture_http_error(exc,session.key)
            raw.append(dict(order=order,requested_pairs=n,job=job,attempt=attempt,payload=request,
                record_type='HTTP_ERROR',phase=phase,backend_error=backend,seconds=seconds,input_budget=budget))
            if phase=='GENERATION_HTTP':counters.update(physical_requests=1,request_sum_sec=seconds)
            print('[DUALQA_BACKEND_ERROR] '+json.dumps(dict(phase=phase,root=job['root'],error=backend)),flush=True)
            raise
        native=method.channels(reply);fields=None;student=None;reason='';usage=reply.get('usage',{})
        try:
            if native['finish_reason']!='stop':raise ValueError('native finish '+str(native['finish_reason'])+'; complete FINAL labels required')
            fields=method.parse_fields(native['final'],n)
            if fields['status']=='QA_FIELDS_COMPLETE':
                student=method.wrap(job,fields,tok,record_id=method.sha([TAG,order,n,job['root'],attempt]))
                if n==2:method.wrap(job,fields,tok,repeat_first=True,record_id=method.sha([TAG,order,n,job['root'],attempt]))
        except ValueError as exc:reason=str(exc)
        raw_id=method.sha([TAG,order,n,job['root'],attempt]);details=usage.get('completion_tokens_details') or {}
        raw.append(dict(raw_record_id=raw_id,order=order,requested_pairs=n,job=job,attempt=attempt,
            payload=request,reply=reply,channels=native,parsed_fields=fields,structural_reason=reason,
            request_sec=seconds,input_budget=budget,actual_reasoning_tokens_from_native_usage=details.get('reasoning_tokens')))
        counters.update(physical_requests=1,request_sum_sec=seconds,completion_tokens=int(usage.get('completion_tokens') or 0))
        result['attempts']=attempt
        print('[DUALQA_TEACHER_ANSWER] '+json.dumps(dict(order=order,requested_pairs=n,root=job['root'],language=job['language'],
            attempt=attempt,fields=fields,structural_reason=reason,request_sec=seconds,
            completion_tokens=usage.get('completion_tokens'),semantic_truth='PSEUDO_UNVERIFIED'),ensure_ascii=False),flush=True)
        if fields is not None and fields['status']=='PRODUCER_DECLINED':result['declined']=True;break
        if student is not None:
            canonical.append(dict(order=order,requested_pairs=n,root=job['root'],raw_record_id=raw_id,student=student))
            counters.update(accepted_contexts=1,accepted_qa=n,student_x_tokens=student['meta']['actual_x_tokens'],assistant_targets=student['meta']['assistant_targets'])
            result.update(accepted=True,raw_record_id=raw_id);break
        feedback=reason
    return result


def execute(args):
    from tokenizers import Tokenizer
    if OUTPUT.exists() or EVIDENCE.exists():raise GateNegative('old pilot output preserved')
    if source.public.digest(source.public.TOKENIZER)!=source.public.TOK_SHA:raise ValueError('student tokenizer changed')
    tok=Tokenizer.from_file(str(source.public.TOKENIZER));items,old=jobs(tok);run_info=info()
    idle_before_gpu();OUTPUT.mkdir(parents=True,exist_ok=False);EVIDENCE.mkdir(parents=True,exist_ok=False)
    writer=ShardWriter(OUTPUT,'sources')
    for item in items:writer.append(item)
    source_manifest=writer.close(lineage=run_info);raw=ShardWriter(OUTPUT,'raw');canonical=ShardWriter(OUTPUT,'candidates')
    arms=[];total_raw=total_candidates=0;began=time.perf_counter();error=None;assets=None;metrics={};partial_arm=None
    try:
        with wall_limit(args.max_wall_sec),patch.object(teacher,'THINKING',method.THINKING):
            assets=teacher.assets(True)
            with PersistentMemory() as memory:
                reader=RetryingMemoryReader(memory,emit=lambda line:print(line,flush=True))
                with stream_session_scope(reader),teacher.GemmaSession(True) as session:
                    for order,sequence in enumerate(((1,2),(2,1))):
                        for n in sequence:
                            tick=time.perf_counter();counter=Counter();results=[]
                            for item in items:results.append(one_job(session,item,n,order,tok,raw,canonical,counter))
                            counter['declined_contexts']=sum(x['declined'] for x in results)
                            counter['structural_exhausted_contexts']=sum(not x['declined'] and not x['accepted'] for x in results)
                            total_raw+=counter['physical_requests'];total_candidates+=counter['accepted_contexts']
                            elapsed=time.perf_counter()-tick
                            accepted_languages=Counter(x['language'] for x in results if x['accepted'])
                            arm=dict(order=order,requested_pairs=n,counts=dict(counter),results=results,whole_sec=elapsed,
                                qa_per_request_sec=counter['accepted_qa']/counter['request_sum_sec'],
                                assistant_targets_per_request_sec=counter['assistant_targets']/counter['request_sum_sec'],
                                student_x_per_request_sec=counter['student_x_tokens']/counter['request_sum_sec'],
                                completion_tok_per_request_sec=counter['completion_tokens']/counter['request_sum_sec'],
                                qa_per_wall_sec=counter['accepted_qa']/elapsed,accepted_languages=dict(accepted_languages))
                            arms.append(arm);print('[DUALQA_TEACHER_ARM] '+json.dumps({k:v for k,v in arm.items() if k!='results'}),flush=True)
                    metrics=dict(memory=session.memory(),telemetry=reader.snapshot(),persistent=memory.snapshot())
    except BaseException as exc:
        import traceback
        traceback.print_exc();error=dict(type=type(exc).__name__,reason=str(exc)[:1500])
        if 'counter' in locals():partial_arm=dict(order=order,requested_pairs=n,counts=dict(counter),completed_contexts=results)
    # A failed partially processed arm may contain valid raw rows. Count the
    # writer's own buffered totals rather than only completed-arm counters.
    raw_count=raw._total_rows;candidate_count=canonical._total_rows
    rm=raw.close(lineage=run_info) if raw_count else None;cm=canonical.close(lineage=run_info) if candidate_count else None
    ready=error is None and len(arms)==4 and all(a['accepted_languages'].get(l,0)>0 for a in arms for l in ('ko','en'))
    result=dict(run_info,status='DUALQA_TEACHER_PILOT_COLLECTED' if error is None else 'DUALQA_EXECUTION_ERROR',
        arms=arms,error=error,partial_arm=partial_arm,assets=assets,metrics=metrics,source_manifest=source_manifest,raw_manifest=rm,candidate_manifest=cm,
        raw_directory=str(OUTPUT.relative_to(ROOT)),raw_records=raw_count,candidate_conversations=candidate_count,
        technical_wire_ready=ready,whole_sec=time.perf_counter()-began,
        content_quality='NOT_REVIEWED; no automatic semantic or bad-phrase gate',
        generation_scope='same8 sources repeated for paired measurement only; not unique training data')
    source.training.write(OUTPUT/'report.json',result);source.training.write(EVIDENCE/'report.json',result)
    print('[DUALQA_TEACHER_FINAL] '+json.dumps(dict(status=result['status'],raw_records=raw_count,
        candidate_conversations=candidate_count,technical_wire_ready=ready,whole_sec=result['whole_sec'])),flush=True)
    return (130 if error['type']=='KeyboardInterrupt' else 9) if error else 0 if ready else 8


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--max-wall-sec',type=int,default=3600)
    group=p.add_mutually_exclusive_group(required=True);group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=3600:p.error('bounded60..3600')
    if a.check_only:print('[DUALQA_CHECK_ONLY] '+json.dumps(info()));return 0
    if not a.execute:p.error('explicit execution required')
    try:
        source.deadline();a.max_wall_sec=min(a.max_wall_sec,int((source.DEADLINE-datetime.now(timezone.utc)).total_seconds())-600)
        if a.max_wall_sec<60:raise GateNegative('authorized deadline margin')
        return execute(a)
    except GateNegative as exc:print('[DUALQA_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[DUALQA_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
