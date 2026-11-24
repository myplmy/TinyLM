#!/usr/bin/env python3
"""Bounded existing-Gemma correction production from TRAIN-only failures.

This makes reviewed-source candidates, not automatic TRAIN admission or new
student learning. All failed replies, thinking channels and attempts persist.
"""
from __future__ import annotations
import argparse
import json
import time
import traceback
from tokenizers import Tokenizer

from scripts import p108b_correction as contract
from scripts import diag_p108b_value_library as library
from scripts import diag_p108b_geometry as atlas
from scripts import interactive_research_infer as manual
from scripts import p106b_gemma_labels as teacher
from scripts.p106b_mixed_scale import TOKENIZER,TOK_SHA
from scripts.p106b_shards import ShardWriter,verify as verify_shards
from scripts.diag_p106d_views import request_with_evidence
from scripts.p106b_mtp_teacher import response_metrics
from scripts.diag_p106b_gemma_telemetry_resume import telemetry_scope
from scripts.p106b_gemma_telemetry_resume import RetryingMemoryReader
from scripts import diag_p106_vram_sample as memory_source

BASE=atlas.BASE
OUT=BASE/'correction_v1'
SOURCES=('scripts/diag_p108b_correction.py','scripts/p108b_correction.py',
    'scripts/test_p108b_correction.py','scripts/test_p108b_correction_driver.py',
    'scripts/p106b_gemma_labels.py','scripts/p106b_gemma_teacher.py',
    'scripts/p106b_teacher_format.py','scripts/diag_p106d_views.py',
    'scripts/p106b_mtp_teacher.py','scripts/diag_p106b_mtp_teacher.py',
    'scripts/diag_p106b_qwen_coload.py','scripts/p106b_qwen_teacher.py',
    'scripts/p106b_gemma_telemetry_resume.py','scripts/diag_p106b_gemma_telemetry_resume.py',
    'scripts/diag_p106_vram_sample.py','scripts/diag_p106b_online_rate5.py',
    'scripts/p106b_shards.py','scripts/diag_p101a_clean_bilingual.py',
    'tinylm/train/mtp_sft.py','tinylm/chat/canonical.py','tinylm/chat/serialize.py')


def prepare():
    rows=contract.cases();assets=teacher.assets(True)
    if manual.file_sha(TOKENIZER)!=TOK_SHA:raise ValueError('fixed student tokenizer changed')
    library.write_new(BASE/'correction_cases_v1.json',dict(rows=rows,role='TRAIN_ONLY_CANDIDATES',
        source_scope='actual24 FIT failures and4 explicit code-verified controls',root_source_review=True))
    profile=dict(schema='P108B_CORRECTION_TEACHER_V1',authority_directive=140,
        deadline=library.DEADLINE.isoformat(),max_wall_seconds=2700,max_attempts_per_case=3,
        sources={n:manual.file_sha(atlas.ROOT/n)for n in SOURCES},teacher_assets=assets,
        source_cases_sha256=manual.file_sha(BASE/'correction_cases_v1.json'),
        tokenizer_path=str(TOKENIZER.relative_to(atlas.ROOT)),tokenizer_sha256=TOK_SHA,
        model_source_core_sha256=rows[0]['source_origin']['core_sha256'],
        mtp=True,student_teacher_coload=False,task='known-literal single and correction views',
        raw_reply_and_thinking_preserved=True,wrong_first_assistant_supervised=False,
        semantic_teacher_review='ROOT_REVIEW_REQUIRED_AFTER_GENERATION',corpus75m_admitted=False,
        intended_cases=28,independent_concept_groups=10,intended_views=56,
        source_role='FIT_TRAIN_ONLY; no DEV,FINAL or official test errors',
        initial_plan_sha256=manual.file_sha(atlas.ROOT/library.PLAN))
    library.write_new(BASE/'correction_profile_v1.json',profile)
    with(BASE/'correction_initial_plan_v1.md').open('xb')as stream:stream.write((atlas.ROOT/library.PLAN).read_bytes())
    print('[CORRECTION_PREPARED]28 TRAIN cases,56 paired candidates; no student or GPU',flush=True)


def verify():
    library.Budget().check();p=json.loads((BASE/'correction_profile_v1.json').read_text(encoding='utf-8'))
    for name,sha in p['sources'].items():
        if manual.file_sha(atlas.ROOT/name)!=sha:raise ValueError('correction source changed: '+name)
    if manual.file_sha(BASE/'correction_cases_v1.json')!=p['source_cases_sha256']:raise ValueError('correction source cases changed')
    if manual.file_sha(TOKENIZER)!=p['tokenizer_sha256']:raise ValueError('correction tokenizer changed')
    if manual.file_sha(BASE/'correction_initial_plan_v1.md')!=p['initial_plan_sha256']:raise ValueError('initial correction plan changed')
    assets=teacher.assets(False)
    for key in('model','draft','model_bytes','draft_bytes','runtime_sha256','sampler','context','max_output','thinking_budget'):
        if assets[key]!=p['teacher_assets'][key]:raise ValueError('teacher asset/profile differs: '+key)
    rows=json.loads((BASE/'correction_cases_v1.json').read_text(encoding='utf-8'))['rows']
    if len(rows)!=28 or rows!=contract.cases():raise ValueError('exact root-reviewed source28 required')
    return p,rows


def generate_case(session,case,append,budget,index):
    last_reason=None
    for attempt in range(1,4):
        budget.check();session.check();payload=contract.payload(case,1337+index*11+attempt)
        if last_reason:
            body=json.loads(payload['messages'][1]['content'])
            body['structural_retry']=dict(reason=last_reason,request='Keep source and verified answer unchanged; fix only the declared output contract.')
            payload['messages'][1]['content']=json.dumps(body,ensure_ascii=False,sort_keys=True)
        ident=case['id']+f':attempt{attempt}';started=time.monotonic()
        reply=request_with_evidence(session,payload,append,ident,timeout=120)
        parsed=teacher.parsed_response(reply,case['language']);reason=parsed.get('parse_error')or''
        views=None
        if parsed['format_status']==teacher.COMPLETE:
            try:views=contract.views(case,parsed['parsed_content'])
            except ValueError as exc:reason=str(exc)
        else:reason=reason or 'incomplete final/finish contract'
        record=dict(case_id=case['id'],generation_id=ident,attempt=attempt,request=payload,
            raw_reply=reply,parsed=parsed,metrics=response_metrics(reply,max(time.monotonic()-started,1e-9)),
            structural_reason=reason,accepted_structure=views is not None,root_semantic_review='PENDING')
        append(record)
        if views is not None:return dict(case_id=case['id'],attempts=attempt,status='CANDIDATE_STRUCTURE_COMPLETE',views=views)
        last_reason=reason
    return dict(case_id=case['id'],attempts=3,status='REJECTED_STRUCTURE_AFTER3',reason=last_reason,views=())


def encode_audit(case,rows,tok):
    records=[contract.masked_record(row,tok)for row in rows]
    if len(records)!=2 or records[0].targets!=records[1].targets:raise ValueError('paired corrected answer supervision differs')
    for index,record in enumerate(records,1):
        owners={owner for owner,target in zip(record.segments,record.y)if target!=-100}
        if owners!={index}:raise ValueError('wrong first assistant turn receives loss')
    return dict(case_id=case['id'],single_x_tokens=len(records[0].x),correction_x_tokens=len(records[1].x),
        corrected_targets_each=records[0].targets,wrong_first_turn_supervised_targets=0,
        context_limit=1024,truncated=False)


def actual():
    p,cases=verify();library.resources()
    if OUT.exists()or OUT.is_symlink():raise FileExistsError('preserve earlier correction attempt')
    OUT.mkdir(parents=True);started=time.monotonic();budget=library.Budget(p['max_wall_seconds'])
    raw=ShardWriter(OUT,'raw',limit=3_000_000);candidates=ShardWriter(OUT,'candidates',limit=3_000_000)
    tok=Tokenizer.from_file(str(TOKENIZER));reader=RetryingMemoryReader(memory_source.read_memory,emit=lambda line:print(line,flush=True))
    report=dict(schema=p['schema'],status='STARTED',cases=[],token_audits=[],raw_rows=0,candidate_rows=0,
        source_profile_sha256=manual.file_sha(BASE/'correction_profile_v1.json'),student_training_updates=0,
        corpus75m_admitted=False,root_teacher_review='PENDING',error=None)
    failure=None;session=None
    def append(row):raw.append(row);report['raw_rows']+=1
    try:
        actual_assets=teacher.assets(True)
        if actual_assets!=p['teacher_assets']:raise ValueError('full teacher bytes changed')
        with telemetry_scope(reader),teacher.GemmaSession(True)as session:
            report['startup_seconds']=session.startup_sec
            for index,case in enumerate(cases):
                outcome=generate_case(session,case,append,budget,index);views=outcome.pop('views')
                if views:
                    try:audit=encode_audit(case,views,tok)
                    except ValueError as error:
                        outcome.update(status='REJECTED_TOKEN_OR_OWNER_CONTRACT',reason=str(error));views=()
                    else:
                        report['token_audits'].append(audit)
                        for row in views:candidates.append(row);report['candidate_rows']+=1
                report['cases'].append(outcome)
                report['memory']=session.memory()
                print('[CORRECTION_CASE] '+json.dumps(outcome),flush=True)
            report['server_tail']=list(session.tail);report['server_signals']=dict(session.signals)
        report['owned_server_ended']=session.process is not None and session.process.poll()is not None
        if not report['owned_server_ended']:raise RuntimeError('owned teacher process did not end')
        report['status']='CORRECTION_GENERATION_COMPLETE_REVIEW_PENDING'
    except BaseException as error:
        failure=error;report.update(status='CORRECTION_TECHNICAL_ERROR',error=str(error),traceback=traceback.format_exc())
    finally:
        if session is not None and session.process is not None:report['owned_server_ended']=session.process.poll()is not None
        report['telemetry']=reader.snapshot()
        lineage=dict(profile_sha256=report['source_profile_sha256'],role='TRAIN_CANDIDATE_NOT_AUTOMATIC_ADMISSION')
        if report['raw_rows']:
            report['raw_manifest']=raw.close(lineage=lineage);verify_shards(OUT,report['raw_manifest'])
        if report['candidate_rows']:
            report['candidate_manifest']=candidates.close(lineage=lineage);verify_shards(OUT,report['candidate_manifest'])
        report['wall_seconds']=time.monotonic()-started
        report['accepted_cases']=sum(c['status']=='CANDIDATE_STRUCTURE_COMPLETE'for c in report['cases'])
        library.write_new(OUT/'report.json',report)
        print('[CORRECTION_END] '+json.dumps({k:report.get(k)for k in('status','accepted_cases','candidate_rows','wall_seconds','owned_server_ended','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved correction technical error')from failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','actual']);a=parser.parse_args()
    if a.phase=='prepare':prepare()
    elif a.phase=='check':verify();print('[CORRECTION_CHECK] sources/roles/assets only; no model/GPU')
    else:actual()


if __name__=='__main__':main()
