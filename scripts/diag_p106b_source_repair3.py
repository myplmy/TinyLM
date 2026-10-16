#!/usr/bin/env python3
"""Sealed Gemma-MTP repair3 pilot/production, separate from old producers."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
import copy
import json
import time
from urllib.error import HTTPError
from unittest.mock import patch
from scripts import p106b_source_repair3 as fields
from scripts import diag_p106b_original_qa3_course as original
from scripts import diag_p106b_dualqa_teacher as legacy
from scripts import p106b_gemma_teacher as teacher
from scripts import diag_p106b_relation_interleaved_course as interleaved
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_memory_stream import PersistentMemory,stream_session_scope
from scripts.p106b_gemma_telemetry_resume import RetryingMemoryReader
from scripts.diag_p106b_gemma_ac import count_prompt
from scripts.p106b_http_errors import capture_http_error
training=original.training
TAG='p106b_source_repair3_v1_s1337'
OUTPUT=ROOT/'HF/sft_ready'/TAG
EVIDENCE=ROOT/'test_result/evidence'/TAG
CODE=(*legacy.CODE,*original.CODE,'scripts/p106b_source_windows.py',
    'scripts/p106b_source_repair3.py','scripts/test_p106b_source_repair3.py',
    'scripts/diag_p106b_source_repair3.py','scripts/test_p106b_source_repair3_deck.py')
GOAL=256
RESERVE=320
BATCH=16


def info():
    return dict(schema='P106B_SEALED_SOURCE_REPAIR3_V1',tag=TAG,
        code_sha256={p:training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        student_tokenizer_sha256=training.data.TOK_SHA,source_reference_token_cap=fields.SOURCE_LIMIT,
        target_per_language=GOAL,source_jobs_per_language=RESERVE,pilot_jobs=16,shared_attempts=fields.MAX_ATTEMPTS,
        teacher_model=str(teacher.MODEL.relative_to(ROOT)),teacher_draft=str(teacher.DRAFT.relative_to(ROOT)),
        server=str(teacher.SERVER),mtp=True,draft_max=2,sampler=teacher.SAMPLER,
        context=fields.CONTEXT,max_output=fields.MAX_OUTPUT,requested_thinking_budget=fields.THINKING,
        source_reference_unchanged=True,duplicate_policy='UNKNOWN_NO_CONTENT_REGENERATION',
        semantic_filter=False,teacher_reasoning_in_student=False,student_training=False,
        formal_train_ready=False,semantic_truth='PSEUDO_UNVERIFIED',deadline_utc=original.prior.producer.legacy.source.DEADLINE.isoformat())


def required(path):
    if not path.is_file() or path.is_symlink():raise GateNegative('exact regular prerequisite absent: '+str(path.relative_to(ROOT)))
    return json.loads(path.read_text(encoding='utf8'))


def reference_of(row):
    m=row['meta']
    if 'source_reference' in m:return m['source_reference']
    if 'original_first_pair' in m:return m['original_first_pair']['reference']
    for key in ('student_reference_range','user_reference_range'):
        if key in m:
            a,b=m[key];return fields.text(row['messages'][0])[a:b]
    return None


def exclusions(original_rows):
    source=interleaved.prior.producer.data.source
    ids,keys,identities=source.old_source_exclusions();ids={x.upper() for x in ids};keys=set(keys);refs=set()
    def add(row):
        ref=reference_of(row)
        if ref is None:return
        m=row['meta'];keys.update(source.method.passage_keys(ref));refs.add(fields.reference_identity(m['language'],ref))
        if m.get('parent_concept_id'):ids.add(m['parent_concept_id'].upper())
    for lane in ('three_train0','dev_natural_three','test_natural_three'):
        for row in original_rows[lane]:add(row)
    _,oldrows,_=source.read_course()
    for values in oldrows.values():
        for row in values:add(row)
    path=interleaved.prior.producer.OUTPUT/'inputs.json';r=required(path)
    identities.append(dict(report=str(path.relative_to(ROOT)),sha256=training.data.digest(path)))
    for job in training.data.stream_rows(interleaved.prior.producer.OUTPUT,r['jobs_manifest']):
        keys.update(source.method.passage_keys(job['reference']));refs.add(fields.reference_identity(job['language'],job['reference']))
    for directory,lanes in ((original.base.CORPUS,('fresh_public_test',)),(interleaved.CORPUS,('fresh_public_test','reserved_original_three_qa'))):
        p=directory/'report.json';r=required(p);identities.append(dict(report=str(p.relative_to(ROOT)),sha256=training.data.digest(p)))
        for lane in lanes:
            for row in training.data.stream_rows(directory,r['manifests'][lane]):add(row)
    for directory in interleaved.PACKETS:
        p=directory/'report.json';r=required(p);identities.append(dict(report=str(p.relative_to(ROOT)),sha256=training.data.digest(p)))
        for sample in training.data.stream_rows(directory,r['sample_manifest']):
            if 'producer_identity' in sample:
                if sample['producer_identity']['family']!='Flan-Coqa':continue
                value=sample['original']['inputs']
            else:
                if sample['group'].split(':',1)[-1]!='Flan-Coqa':continue
                value=fields.text(sample['original']['messages'][0])
            keys.update(source.method.passage_keys(value))
    return ids,keys,refs,identities


def fresh_public(tok,oldrows):
    ids,used_keys,used_refs,identities=exclusions(oldrows);source=interleaved.prior.producer.data.source
    if training.data.digest(training.data.PUBLIC/'report.json')!=training.data.PUBLIC_SHA:raise ValueError('original public source report changed')
    candidates={};rejected=Counter()
    for split in ('train','val'):
        manifest=required(training.data.PUBLIC/(split+'_shards_manifest.json'))
        for row in training.data.stream_rows(training.data.PUBLIC,manifest):
            m=row['meta']
            if m.get('selection_family')!='Flan-Coqa' or m.get('language') not in ('ko','en'):continue
            if m['parent_concept_id'].upper() in ids:continue
            try:
                parsed=fields.original_three(row);ref=parsed['reference'];language=m['language'];root=fields.reference_identity(language,ref)
                if len(tok.encode(ref).ids)>fields.SOURCE_LIMIT:raise ValueError('reference token budget')
                if root in used_refs:raise ValueError('previous exact reference')
                keys=source.method.passage_keys(ref)
                if keys&used_keys:raise ValueError('previous exact24word passage')
                job=dict(root=root,language=language,reference=ref,raw_pairs=parsed['raw_pairs'],
                    provenance={k:copy.deepcopy(m[k]) for k in fields.PROVENANCE if k in m},
                    original_student_row_sha256=fields.sha(row),original_source_root=m['parent_concept_id'])
                child=fields.render(job,job['raw_pairs'],tok,repaired=False)
                child['meta'].update(source_split='test',original_source_parser='SYNTAX_ONLY_NO_SPAN_ORACLE',original_item_ranges=parsed['original_item_ranges'])
            except ValueError as exc:rejected[str(exc)]+=1;continue
            rank=fields.sha([TAG,'FRESH',root,parsed['raw_pairs']])
            if root not in candidates or rank<candidates[root][0]:candidates[root]=(rank,child,keys)
    chosen=defaultdict(list);taken=set()
    for rank,row,keys in sorted(candidates.values(),key=lambda x:x[0]):
        if keys&taken:continue
        taken.update(keys);chosen[row['meta']['language']].append(row)
    supply={l:len(chosen[l]) for l in ('ko','en')}
    if min(supply.values())<32:raise GateNegative('fresh general3QA32 each language short: '+json.dumps(supply))
    return chosen['ko'][:32]+chosen['en'][:32],dict(supply=supply,rejections=dict(rejected),exclusion_reports=identities,
        excludes_previous_ids_references_and_exact24word=True,span_uniqueness_not_a_general_SFT_requirement=True,
        semantic_pretraining_overlap='NOT_AUDITED',raw_id_bilingual_alignment=False)


def make_jobs(tok):
    _,rows,_=original.read_course();jobs=[];by_language={};rejected=Counter()
    for language in ('ko','en'):
        values=[r for r in rows['three_train0'] if r['meta']['kind']=='public_qa' and r['meta']['language']==language]
        lane={}
        for row in values:
            try:
                job=fields.from_wrapped(row)
                if len(tok.encode(job['reference']).ids)>fields.SOURCE_LIMIT:raise ValueError('reference token budget')
                fields.render(job,job['raw_pairs'],tok,repaired=False)
            except ValueError as exc:rejected[str(exc)]+=1;continue
            lane[job['root']]=job
        ordered=sorted(lane.values(),key=lambda j:fields.sha([TAG,'TRAIN',j['root']]))
        by_language[language]=len(ordered)
        if len(ordered)<RESERVE:raise GateNegative('unique declared TRAIN source reserve short')
        jobs.append(ordered[:RESERVE])
    merged=[jobs[language][i] for i in range(RESERVE) for language in (0,1)]
    test,test_info=fresh_public(tok,rows)
    train_refs={j['root'] for j in merged};test_refs={r['meta']['semantic_root_id'] for r in test}
    if train_refs&test_refs:raise ValueError('new reference identity train/test overlap')
    return merged,test,dict(train_supply=by_language,train_rejections=dict(rejected),fresh_public=test_info)


def freeze():
    from tokenizers import Tokenizer
    if OUTPUT.exists() or EVIDENCE.exists():raise GateNegative('old repair3 namespace preserved')
    if training.data.digest(training.data.TOKENIZER)!=training.data.TOK_SHA:raise ValueError('student tokenizer changed')
    tok=Tokenizer.from_file(str(training.data.TOKENIZER));jobs,test,supply=make_jobs(tok)
    OUTPUT.mkdir(parents=True,exist_ok=False);manifests={}
    for name,values in (('teacher_jobs',jobs),('fresh_public_test',test)):
        writer=ShardWriter(OUTPUT,name)
        for row in values:writer.append(row)
        manifests[name]=writer.close(lineage=info());verify(OUTPUT,manifests[name])
    report=dict(info(),status='REPAIR3_INPUTS_FROZEN',manifests=manifests,supply=supply,
        jobs=len(jobs),fresh_test=len(test),test_model_evaluated=False,test_text_human_reviewed=False)
    training.write(OUTPUT/'inputs.json',report);training.write(EVIDENCE/'inputs.json',report)
    print('[REPAIR3_INPUTS] '+json.dumps(dict(jobs=len(jobs),fresh_test=len(test),supply=supply)),flush=True);return 0


def state():
    r=required(OUTPUT/'inputs.json')
    if r['code_sha256']!=info()['code_sha256'] or r['status']!='REPAIR3_INPUTS_FROZEN':raise ValueError('frozen repair3 CODE changed')
    jobs=list(training.data.stream_rows(OUTPUT,r['manifests']['teacher_jobs']));processed=set();counts=Counter();reports=[]
    for directory in sorted(OUTPUT.glob('batch_*')):
        p=directory/'report.json'
        if not p.is_file():raise GateNegative('unsealed old repair batch preserved; new inspected recovery required')
        b=required(p)
        if b['code_sha256']!=r['code_sha256'] or b['jobs_sha256']!=r['manifests']['teacher_jobs']['concat_sha256']:raise ValueError('batch source/CODE changed')
        for name in ('raw_manifest','candidate_manifest'):
            if b[name]:verify(directory,b[name])
        for x in b['results']:
            if x['root'] in processed:raise ValueError('root attempted again across sealed batches')
            processed.add(x['root'])
            if x['accepted']:counts[x['language']]+=1
        reports.append(dict(path=str(p.relative_to(ROOT)),sha256=training.data.digest(p)))
    return r,jobs,processed,counts,reports


def emit_answer(value):
    line=json.dumps(value,ensure_ascii=False)
    if len(line.encode())>8192:
        value={k:v for k,v in value.items() if k not in ('pairs','original_pairs')}
        value.update(stdout_fields_truncated=True,complete_fields_location='immutable raw/candidate shard keyed by raw_id')
        line=json.dumps(value,ensure_ascii=False)
    print('[REPAIR3_TEACHER_ANSWER] '+line,flush=True)


def one_job(session,job,tok,raw,candidates,counters,pilot):
    result=dict(root=job['root'],language=job['language'],accepted=False,declined=False,attempts=0);feedback=''
    for attempt in range(1,fields.MAX_ATTEMPTS+1):
        original.prior.producer.legacy.source.deadline();session.check()
        seed=int(fields.sha([TAG,job['root'],attempt])[:12],16)%(2**31-1)
        request=fields.payload(job,seed,feedback);phase='INPUT_BUDGET';budget=None;start=time.perf_counter()
        try:
            budget=count_prompt(session,request['messages'],fields.CONTEXT,fields.MAX_OUTPUT);phase='GENERATION_HTTP';start=time.perf_counter()
            reply=session.request('/v1/chat/completions',request,timeout=180);seconds=time.perf_counter()-start
        except HTTPError as exc:
            error=capture_http_error(exc,session.key)
            raw.append(dict(record_type='HTTP_ERROR',job=job,attempt=attempt,payload=request,phase=phase,error=error,input_budget=budget))
            if phase=='GENERATION_HTTP':counters['physical_requests']+=1
            raise
        native=fields.channels(reply);parsed=None;row=None;reason='';usage=reply.get('usage',{});raw_id=fields.sha([TAG,job['root'],attempt])
        try:
            if native['finish_reason']!='stop':raise ValueError('native final incomplete: '+str(native['finish_reason']))
            parsed=fields.parse_fields(native['final'])
            if parsed['status']=='THREE_QA_FIELDS_COMPLETE':row=fields.render(job,parsed['pairs'],tok,repaired=True,record_id=raw_id,note=parsed['note'])
        except ValueError as exc:reason=str(exc)
        details=usage.get('completion_tokens_details') or {}
        raw.append(dict(raw_id=raw_id,job=job,attempt=attempt,payload=request,reply=reply,channels=native,parsed_fields=parsed,
            structural_reason=reason,request_sec=seconds,input_budget=budget,actual_reasoning_tokens_from_native_usage=details.get('reasoning_tokens')))
        counters.update(physical_requests=1,request_sum_sec=seconds,completion_tokens=int(usage.get('completion_tokens') or 0))
        result['attempts']=attempt
        shown=dict(raw_id=raw_id,root=job['root'],source_id=job['provenance'].get('source_id'),language=job['language'],attempt=attempt,
            request_sec=seconds,structural_reason=reason,semantic_truth='PSEUDO_UNVERIFIED')
        if row is not None:
            shown['pairs']=parsed['pairs']
            if pilot:shown['original_pairs']=job['raw_pairs']
        else:shown['final_excerpt']=native['final'][:1024]
        emit_answer(shown)
        if parsed and parsed['status']=='PRODUCER_DECLINED':result['declined']=True;break
        if row is not None:
            changes=[dict(question_changed=x['question']!=y['question'],answer_changed=x['answer']!=y['answer']) for x,y in zip(job['raw_pairs'],parsed['pairs'])]
            candidates.append(dict(root=job['root'],language=job['language'],raw_id=raw_id,job=job,
                raw_student=fields.render(job,job['raw_pairs'],tok,repaired=False),repaired_student=row,changes=changes))
            counters.update(accepted_contexts=1,accepted_qa=3,student_x_tokens=row['meta']['actual_x_tokens'],assistant_targets=row['meta']['assistant_targets'])
            result.update(accepted=True,raw_id=raw_id);break
        feedback=reason
    return result


def produce(a,pilot):
    from tokenizers import Tokenizer
    r,jobs,processed,accepted,prior_reports=state()
    if all(accepted[l]>=GOAL for l in ('ko','en')):raise GateNegative('quota already complete, never regenerate old roots')
    if pilot and processed:raise GateNegative('pilot is single first window, original outputs preserved')
    candidates_jobs=[j for j in jobs if j['root'] not in processed and accepted[j['language']]<GOAL]
    if not candidates_jobs:raise GateNegative('unique root reserve exhausted')
    if pilot:candidates_jobs=candidates_jobs[:16]
    idle_before_gpu();tok=Tokenizer.from_file(str(training.data.TOKENIZER));began=time.perf_counter()
    index=len(prior_reports);window_index=len(list(EVIDENCE.glob('window_*.json')));batch=None;results=[];counts=Counter();batches=[]
    raw=candidates=None;active_job=None;error=None;paused=False;metrics={};assets=None
    def open_batch():
        nonlocal batch,raw,candidates,results,counts
        batch=OUTPUT/f'batch_{index:06d}';batch.mkdir(exist_ok=False);raw=ShardWriter(batch,'raw');candidates=ShardWriter(batch,'candidates');results=[];counts=Counter()
    def seal(status):
        nonlocal index,batch
        if batch is None:return
        rm=raw.close(lineage=info()) if raw._total_rows else None;cm=candidates.close(lineage=info()) if candidates._total_rows else None
        value=dict(info(),status=status,jobs_sha256=r['manifests']['teacher_jobs']['concat_sha256'],results=results,
            counts=dict(counts),raw_manifest=rm,candidate_manifest=cm,assets=assets)
        training.write(batch/'report.json',value);batches.append(dict(path=str((batch/'report.json').relative_to(ROOT)),sha256=training.data.digest(batch/'report.json')))
        index+=1;batch=None
    try:
        with wall_limit(a.max_wall_sec),patch.object(teacher,'THINKING',fields.THINKING):
            assets=teacher.assets(True)
            with PersistentMemory() as memory:
                reader=RetryingMemoryReader(memory,emit=lambda line:print(line,flush=True))
                with stream_session_scope(reader),teacher.GemmaSession(True) as session:
                    for job in candidates_jobs:
                        if accepted[job['language']]>=GOAL:continue
                        original.prior.producer.legacy.source.deadline()
                        if a.max_wall_sec-(time.perf_counter()-began)<240:paused=True;break
                        if batch is None:open_batch()
                        active_job=job;one=one_job(session,job,tok,raw,candidates,counts,pilot);results.append(one);processed.add(job['root'])
                        if one['accepted']:accepted[job['language']]+=1
                        active_job=None
                        if len(results)>=BATCH:seal('SEALED_BATCH')
                        if len(processed)%16==0:print('[REPAIR3_PROGRESS] '+json.dumps(dict(processed=len(processed),accepted=dict(accepted),elapsed_sec=time.perf_counter()-began)),flush=True)
                        if all(accepted[l]>=GOAL for l in ('ko','en')):break
                    metrics=dict(memory=session.memory(),telemetry=reader.snapshot(),persistent=memory.snapshot())
        seal('SEALED_TAIL')
    except BaseException as exc:
        import traceback
        traceback.print_exc();error=dict(type=type(exc).__name__,reason=str(exc)[:1500])
        if batch is not None and active_job is not None:results.append(dict(root=active_job['root'],language=active_job['language'],accepted=False,declined=False,status='OPERATION_ABANDONED_NO_AUTOMATIC_RETRY'))
        seal('SEALED_OPERATION_ERROR')
    complete=all(accepted[l]>=GOAL for l in ('ko','en'))
    status='OPERATION_ERROR' if error else 'REPAIR_SOURCE_QUOTA_COMPLETE' if complete else 'PILOT_COLLECTED' if pilot and not paused else 'PAUSED_WINDOW_BUDGET' if paused else 'SOURCE_RESERVES_EXHAUSTED'
    ready=error is None and all(accepted[l]>0 for l in ('ko','en'))
    report=dict(info(),status=status,pilot=pilot,accepted=dict(accepted),processed=len(processed),prior_batches=prior_reports,window_batches=batches,
        assets=assets,metrics=metrics,error=error,technical_wire_ready=ready,source_quota_complete=complete and error is None,
        whole_sec=time.perf_counter()-began,normal_pause_is_not_quality_failure=True)
    training.write(EVIDENCE/f'window_{window_index:06d}.json',report)
    print('[REPAIR3_FINAL] '+json.dumps({k:report[k] for k in ('status','accepted','processed','technical_wire_ready','source_quota_complete','whole_sec')}),flush=True)
    return (130 if error['type']=='KeyboardInterrupt' else 9) if error else 0 if ready and (pilot or complete) else 8


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('freeze','pilot','produce'),required=True)
    p.add_argument('--max-wall-sec',type=int,default=5400);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 600<=a.max_wall_sec<=7200:p.error('bounded600..7200')
    if a.check_only:print('[REPAIR3_CHECK_ONLY] '+json.dumps(info()));return 0
    try:
        original.prior.producer.legacy.source.deadline()
        if a.mode=='freeze':return freeze()
        remaining=(original.prior.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds()
        if remaining<a.max_wall_sec+2700:raise GateNegative('requested teacher window plus45minute closure margin required')
        return produce(a,pilot=a.mode=='pilot')
    except GateNegative as exc:print('[REPAIR3_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[REPAIR3_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
