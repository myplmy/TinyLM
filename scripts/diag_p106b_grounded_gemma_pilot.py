#!/usr/bin/env python3
"""User-only grounded B pilot:16 source groups, KO/EN8 each, no student.

QA4/JSON2/teacher-authored3turn2 per language. Original-source family/provenance
is retained. Maximum3 structural attempts per turn, never a semantic blacklist.
The pilot cannot claim75M supply, new facts, gold labels or training readiness.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_gemma_teacher as teacher
from scripts.diag_p106b_source_inventory import OUTPUT as INVENTORY
from scripts.diag_p106b_gemma_teacher_gate import OUTPUT as TEACHER
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit,disposition
from scripts.p106b_teacher_wrapper import wrap_turns
from scripts.p106b_mixed_scale import TOKENIZER,TOK_SHA,digest,safe_repo_path

OUTPUT=ROOT/'HF/sft_ready/p106b_gemma_grounded_pilot_v1'
PROFILES=('qa','qa','qa','qa','json','json','multiturn','multiturn')


def select_jobs(samples):
    from tinylm.data.sft import conversation_split_key
    result=[];used=set()
    for language in ('ko','en'):
        candidates={}
        for sample in samples:
            row=sample['original'];meta=row['meta']
            if meta.get('language')!=language or not sample['current_builder_eligible']:continue
            key=conversation_split_key(row).hex().upper()
            if key in used:continue
            if key not in candidates or sample['sampling_rank']<candidates[key]['sampling_rank']:
                candidates[key]=sample
        ranked=sorted(candidates.values(),key=lambda s:s['sampling_rank'])
        if len(ranked)<8:raise FileNotFoundError('need8 distinct current-policy source groups per language; no repeated filler')
        for index,profile in enumerate(PROFILES):
            sample=ranked[index];row=sample['original'];key=conversation_split_key(row).hex().upper();used.add(key)
            result.append(dict(language=language,task=profile,original=row,
                source_group_id=key,
                source_family=row['meta']['source_family'],sampling_rank=sample['sampling_rank']))
    return result


def check():
    safe_repo_path(OUTPUT)
    if OUTPUT.exists() or OUTPUT.is_symlink():raise FileExistsError('prior/partial pilot preserved; new stage needed')
    inventory=json.loads(safe_repo_path(INVENTORY/'report.json').read_text(encoding='utf-8'))
    if inventory.get('status')!='INVENTORY_COMPLETE':raise FileNotFoundError('successful source inventory required')
    manifest=inventory['sample_manifest'];verify(INVENTORY,manifest)
    samples=[json.loads(line) for shard in manifest['shards']
             for line in (INVENTORY/shard['path']).read_text(encoding='utf-8').splitlines()]
    jobs=select_jobs(samples)
    role=json.loads(safe_repo_path(TEACHER/'role/report.json').read_text(encoding='utf-8'))
    expected={c['id'] for c in teacher.cases()}
    observed={r['case_id'] for r in role.get('answers',[]) if not r['mtp'] and r['format_status']=='TAGGED_COMPLETE'}
    if role.get('actual_requests')!=16 or not expected<=observed:
        raise FileNotFoundError('Gemma base off-mode role wiring not confirmed; MTP benefit is not a prerequisite')
    if digest(TOKENIZER)!=TOK_SHA:raise ValueError('student chat32 identity differs')
    return jobs,dict(schema='P106B_GROUNDED_GEMMA_PREFLIGHT_V1',source_sample_sha256=manifest['concat_sha256'],
        teacher_identity=role['input']['asset_identity'],language_groups={'ko':8,'en':8},
        maximum_attempts_per_turn=3,planned_groups=16,planned_turns=24,mtp=False,
        teacher_authored_dialogue='not source natural dialogue',semantic_truth='PSEUDO_UNVERIFIED',
        formal_train_ready=False,student_training='NOT_RUN',source_family_cap='real original family, not teacher/filename labels')


def execute(jobs,info):
    from tokenizers import Tokenizer
    fresh=teacher.assets(True)
    if any(fresh[key]!=info['teacher_identity'][key] for key in ('model_sha256','draft_sha256')):
        raise ValueError('Gemma asset identity changed')
    tok=Tokenizer.from_file(str(TOKENIZER));OUTPUT.mkdir(exist_ok=False)
    raw=ShardWriter(OUTPUT,'raw');canonical=ShardWriter(OUTPUT,'candidates');started=time.perf_counter()
    report=dict(schema='P106B_GROUNDED_GEMMA_PILOT_V1',input=info,attempts=0,accepted_groups=0,
        accepted_student_x_tokens=0,accepted_targets=0,groups=[],student_training='NOT_RUN',
        formal_train_ready=False,semantic_truth='PSEUDO_UNVERIFIED',new75M_ready=False)
    try:
        idle_before_gpu()
        with wall_limit(3600),teacher.GemmaSession(False) as session:
            for index,job in enumerate(jobs):
                turns=[];reasoning_refs=[];meta=job['original']['meta'];required=3 if job['task']=='multiturn' else 1
                for turn_index in range(required):
                    accepted=None
                    for attempt in range(1,4):
                        session.check();payload=teacher.grounded_payload(job['original'],job['language'],job['task'],
                            20261007+index*100+turn_index*10+attempt,history=turns)
                        applied=session.request('/apply-template',{'messages':payload['messages']})
                        tokens=session.request('/tokenize',{'content':applied['prompt'],'add_special':False,'parse_special':True})['tokens']
                        if len(tokens)+teacher.MAX_OUTPUT+128>teacher.CONTEXT:
                            raise ValueError('actual source token budget exceeded; source preserved, no silent truncation')
                        t=time.perf_counter();report['attempts']+=1
                        reply=session.request('/v1/chat/completions',payload,timeout=300)
                        parsed=teacher.parsed_response(reply,job['language'])
                        record=dict(group=index,turn=turn_index+1,attempt=attempt,job=job,reply=reply,parsed=parsed,
                                    request_sec=time.perf_counter()-t,input_tokens=len(tokens),semantic_truth='PSEUDO_UNVERIFIED')
                        raw.append(record);raw_row=raw._total_rows
                        print('[GROUNDED_ANSWER] '+json.dumps(dict(group=index,task=job['task'],turn=turn_index+1,
                            attempt=attempt,final=parsed.get('teacher_final_content'),status=parsed['format_status']),ensure_ascii=False),flush=True)
                        if parsed['format_status']!='TAGGED_COMPLETE':continue
                        content=parsed['parsed_content']
                        if job['task']=='json':
                            try:obj=json.loads(content['assistant_text'])
                            except (TypeError,ValueError):continue
                            if not isinstance(obj,dict) or set(obj)!={'answer'}:continue
                        accepted=content
                        reasoning=parsed.get('teacher_reasoning_content','')
                        reasoning_refs.append(dict(raw_row_1based=raw_row,
                            sha256=hashlib.sha256(reasoning.encode()).hexdigest().upper(),in_student=False))
                        break
                    if accepted is None:break
                    turns.append(dict(user_text=accepted['user_text'],assistant_text=accepted['assistant_text']))
                if len(turns)!=required:
                    report['groups'].append(dict(group=index,accepted=False,reason='structural turn completion insufficient'));continue
                candidate=wrap_turns(turns,source_id=meta['source_id'],source_sha256=meta['source_sha256'],
                    teacher_model_sha256=info['teacher_identity']['model_sha256'],language=job['language'],
                    source_license=meta['source_license'],generation_id='grounded_'+str(index),
                    source_repo=meta['source_repo'],source_revision=meta['source_revision'],
                    source_object_id=meta['source_id'],source_transform='teacher_answer',
                    parent_concept_id=job['source_group_id'],source_rights_status=meta.get('rights_status','CARD_ONLY'))
                candidate['meta'].update(source_family=job['source_family'],producer='Gemma4-12B',
                    task_profile=job['task'],role_origin='teacher_authored',teacher_reasoning_refs=reasoning_refs)
                from tinylm.data.sft import encode_conversation,sft_targets
                ids,labels,_=encode_conversation(candidate,tok);x,y=sft_targets(ids,labels);targets=sum(v>=0 for v in y)
                if not 0<len(x)<=1024 or not targets:
                    report['groups'].append(dict(group=index,accepted=False,reason='student context/mask contract'));continue
                canonical.append(candidate);report['accepted_groups']+=1
                report['accepted_student_x_tokens']+=len(x);report['accepted_targets']+=targets
                report['groups'].append(dict(group=index,accepted=True,x_tokens=len(x),source_family=job['source_family']))
            report['memory']=session.memory()
            report.update(status='GROUNDED_PILOT_COMPLETE' if report['accepted_groups']==16 else 'GATE_NEGATIVE',
                          returncode=0 if report['accepted_groups']==16 else 8)
    except BaseException as exc:
        status,rc=disposition(exc);report.update(status=status,returncode=rc,error_type=type(exc).__name__,error=str(exc)[:1600])
    finally:
        for name,writer in (('raw',raw),('candidate',canonical)):
            if writer._total_rows:
                m=writer.close(lineage=info);verify(OUTPUT,m);report[name+'_manifest']=m
        report['whole_wall_sec']=time.perf_counter()-started
        report['accepted_student_x_per_sec']=report['accepted_student_x_tokens']/report['whole_wall_sec']
        with (OUTPUT/'report.json').open('x',encoding='utf-8') as stream:
            json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
        print('[GROUNDED_FINAL] '+json.dumps({k:report.get(k) for k in ('status','returncode','attempts','accepted_groups',
            'accepted_student_x_tokens','accepted_targets','accepted_student_x_per_sec','new75M_ready','error_type','error')},ensure_ascii=False),flush=True)
    return report['returncode']


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    try:
        jobs,info=check()
        if a.check_only:print('[CHECK_ONLY] '+json.dumps(info));return 0
        return execute(jobs,info)
    except (FileNotFoundError,FileExistsError) as exc:print('[HOLD] '+str(exc),file=sys.stderr);return 8
    except Exception as exc:print('[ERROR] '+type(exc).__name__+': '+str(exc),file=sys.stderr);return 9


if __name__=='__main__':raise SystemExit(main())
