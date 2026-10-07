#!/usr/bin/env python3
"""User-only contract16 -> conditional family64. No student/model training.

Same original16 fixes trusted instructions and learner constraints first.
The64 sample is family-stratified, not certified topic coverage or75M supply.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_gemma_task_contract as tasks
from scripts import p106b_gemma_labels as teacher
from scripts import diag_p106b_grounded_gemma_label_pilot as previous
from scripts import p106b_capability_corpus as capability
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit, disposition
from scripts.p106b_teacher_wrapper import wrap_turns
from scripts.p106b_mixed_scale import TOKENIZER, TOK_SHA, digest, safe_repo_path
from tinylm.data.sft import conversation_split_key

OLD_SHA = '9C19760A4E7EF71D806BBD2E3C397BD9203D4169E360EAFA6DDBC9A49F1BCC56'
ROLE_SHA = 'DF1D34F16EC0D5022E5395CC62A14DBDF8BB895E5FF76966F2A666DD3FF3CC97'
OUTPUTS = {mode: ROOT / ('HF/sft_ready/p106b_gemma_task_' + mode + '_v1')
           for mode in ('contract16', 'family64')}


def read_report(path, sha):
    path = safe_repo_path(path)
    if digest(path) != sha:
        raise ValueError('pinned report changed: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def records(directory, manifest):
    verify(directory, manifest)
    return [json.loads(line) for spec in manifest['shards']
            for line in (directory / spec['path']).read_text(encoding='utf-8').splitlines()]


def same_jobs(raw):
    selected = {}
    for rec in raw:
        index, job = rec['group'], rec['job']
        if index in selected and selected[index] != job:
            raise ValueError('one original group has conflicting jobs')
        selected[index] = job
    if set(selected) != set(range(16)):
        raise ValueError('same16 source jobs incomplete')
    jobs = [selected[i] for i in range(16)]
    if (Counter(j['language'] for j in jobs) != {'ko': 8, 'en': 8}
            or len({j['source_group_id'] for j in jobs}) != 16):
        raise ValueError('same16 balance/identity differs')
    return jobs


def diverse_jobs(samples):
    jobs, used = [], set()
    profiles = ('qa', 'json', 'qa', 'multiturn') * 8
    for language in ('ko', 'en'):
        families = defaultdict(list)
        for sample in samples:
            row, meta = sample['original'], sample['original']['meta']
            if meta['language'] != language:
                continue
            key = conversation_split_key(row).hex().upper()
            family = capability.engine.family_bucket(meta['source_family'])
            families[family].append((sample['sampling_rank'], key, sample))
        queues = {f: sorted(rows, key=lambda r: (r[0], r[1])) for f, rows in families.items()}
        counts = Counter()
        chosen = []
        while len(chosen) < 32:
            progressed = False
            for family in sorted(queues):
                if counts[family] >= 8:
                    continue
                queue = queues[family]
                while queue and queue[0][1] in used:
                    queue.pop(0)
                if not queue:
                    continue
                _, key, sample = queue.pop(0)
                row = sample['original']
                used.add(key); counts[family] += 1; progressed = True
                chosen.append(dict(language=language, task=profiles[len(chosen)], original=row,
                    source_group_id=key, source_family=row['meta']['source_family'],
                    sampling_rank=sample['sampling_rank'], original_builder_eligible=sample['current_builder_eligible']))
                if len(chosen) == 32:
                    break
            if not progressed:
                raise FileNotFoundError('need32 unique source groups per language with real-family cap8; no repeated filler')
        jobs.extend(chosen)
    return jobs


def require_contract16(report):
    if (report.get('schema') != 'P106B_GEMMA_TASK_PILOT_V1'
            or report.get('status') != 'TASK_PILOT_COMPLETE'
            or report.get('accepted_groups') != 16
            or report.get('candidate_manifest', {}).get('rows') != 16
            or report.get('input', {}).get('mode') != 'contract16'
            or report.get('input', {}).get('planned_groups') != 16
            or report.get('input', {}).get('wire_contract') != tasks.CONTRACT
            or report.get('input', {}).get('old_report_sha256') != OLD_SHA
            or report.get('input', {}).get('role_report_sha256') != ROLE_SHA):
        raise FileNotFoundError('successful pinned contract16 required before family64')


def check(mode):
    output = safe_repo_path(OUTPUTS[mode])
    if output.exists() or output.is_symlink():
        raise FileExistsError('old/partial output preserved; use a new stage')
    old = read_report(previous.OUTPUT / 'report.json', OLD_SHA)
    role = read_report(previous.role_gate.OUTPUT / 'role/report.json', ROLE_SHA)
    previous.require_base_off(role)
    if digest(TOKENIZER) != TOK_SHA:
        raise ValueError('student chat32 identity differs')
    if mode == 'contract16':
        jobs = same_jobs(records(previous.OUTPUT, old['raw_manifest']))
    else:
        prereq = json.loads(safe_repo_path(OUTPUTS['contract16'] / 'report.json').read_text(encoding='utf-8'))
        require_contract16(prereq)
        records(OUTPUTS['contract16'], prereq['candidate_manifest'])
        inventory = read_report(previous.pilot.INVENTORY / 'report.json', previous.INVENTORY_SHA)
        jobs = diverse_jobs(records(previous.pilot.INVENTORY, inventory['sample_manifest']))
    return jobs, dict(schema='P106B_GEMMA_TASK_PREFLIGHT_V1', mode=mode,
        wire_contract=tasks.CONTRACT, old_report_sha256=OLD_SHA, role_report_sha256=ROLE_SHA,
        inventory_report_sha256=previous.INVENTORY_SHA, teacher_identity=role['input']['asset_identity'],
        planned_groups=len(jobs), planned_turns=sum(3 if j['task']=='multiturn' else 1 for j in jobs),
        language_groups=dict(Counter(j['language'] for j in jobs)), mtp=False,
        maximum_attempts_per_turn=3, topic_coverage='NOT_REVIEWED',
        split_unit='original source concept, not teacher variants',
        source_family_counts=dict(Counter(j['language']+':'+j['source_family'] for j in jobs)),
        semantic_truth='PSEUDO_UNVERIFIED', formal_train_ready=False,
        student_training='NOT_RUN', new75M_ready=False)


def execute(mode, jobs, info):
    from tokenizers import Tokenizer
    from tinylm.data.sft import encode_conversation, sft_targets
    fresh = teacher.assets(True)
    if any(fresh[k] != info['teacher_identity'][k] for k in ('model_sha256', 'draft_sha256')):
        raise ValueError('teacher identity changed')
    tok = Tokenizer.from_file(str(TOKENIZER)); output = OUTPUTS[mode]
    output.mkdir(exist_ok=False)
    raw, canonical = ShardWriter(output, 'raw'), ShardWriter(output, 'candidates')
    report = dict(schema='P106B_GEMMA_TASK_PILOT_V1', input=info, attempts=0, accepted_groups=0,
                  accepted_student_x_tokens=0, accepted_targets=0, groups=[],
                  student_training='NOT_RUN', new75M_ready=False, semantic_truth='PSEUDO_UNVERIFIED')
    started = time.perf_counter()
    try:
        idle_before_gpu()
        with wall_limit(3600), teacher.GemmaSession(False) as session:
            for index, job in enumerate(jobs):
                turns, refs = [], []
                for turn in range(3 if job['task']=='multiturn' else 1):
                    accepted = None
                    for attempt in range(1, 4):
                        session.check()
                        payload = tasks.payload(job['original'], job['language'], job['task'],
                            20261007+index*100+turn*10+attempt, history=turns)
                        prompt = session.request('/apply-template', {'messages':payload['messages']})['prompt']
                        count = len(session.request('/tokenize', dict(content=prompt, add_special=False, parse_special=True))['tokens'])
                        if count+teacher.MAX_OUTPUT+128 > teacher.CONTEXT:
                            raise ValueError('source budget exceeded; no silent truncation')
                        began=time.perf_counter(); report['attempts']+=1
                        reply=session.request('/v1/chat/completions', payload, timeout=300)
                        parsed=teacher.parsed_response(reply, job['language']); reason=''
                        if parsed['format_status']==teacher.COMPLETE:
                            try: accepted=tasks.learner_turn(parsed['parsed_content'],job['language'],job['task'],history=turns)
                            except (ValueError,TypeError) as exc: reason=str(exc)
                        else: reason=parsed.get('parse_error') or parsed['format_status']
                        raw.append(dict(group=index,turn=turn+1,attempt=attempt,job=job,payload=payload,
                            reply=reply,parsed=parsed,producer_learner_turn=accepted,
                            structural_reason=reason,input_tokens=count,request_sec=time.perf_counter()-began))
                        print('[TASK_ANSWER] '+json.dumps(dict(group=index,language=job['language'],task=job['task'],
                            turn=turn+1,attempt=attempt,question=accepted['user_text'] if accepted else None,
                            answer=parsed.get('teacher_final_content'),structural_reason=reason,
                            semantic_truth='PSEUDO_UNVERIFIED'),ensure_ascii=False),flush=True)
                        if accepted is not None:
                            thought=parsed.get('teacher_reasoning_content','')
                            refs.append(dict(raw_row_1based=raw._total_rows,sha256=hashlib.sha256(thought.encode()).hexdigest().upper(),in_student=False))
                            break
                    if accepted is None: break
                    turns.append(accepted)
                required=3 if job['task']=='multiturn' else 1
                if len(turns)!=required:
                    report['groups'].append(dict(group=index,accepted=False,reason='structural completion insufficient')); continue
                meta=job['original']['meta']
                row=wrap_turns(turns,source_id=meta['source_id'],source_sha256=meta['source_sha256'],
                    teacher_model_sha256=info['teacher_identity']['model_sha256'],language=job['language'],
                    source_license=meta['source_license'],generation_id=mode+'_'+str(index),
                    source_repo=meta['source_repo'],source_revision=meta['source_revision'],source_object_id=meta['source_id'],
                    source_transform='teacher_answer',parent_concept_id=job['source_group_id'],
                    source_rights_status=meta.get('rights_status','CARD_ONLY'))
                row['meta'].update(source_family=job['source_family'],producer='Gemma4-12B',task_profile=job['task'],
                    wire_contract=tasks.CONTRACT,role_origin='producer_contract_teacher_content',teacher_reasoning_refs=refs)
                ids,labels,_=encode_conversation(row,tok); x,y=sft_targets(ids,labels); targets=sum(v>=0 for v in y)
                if not 0<len(x)<=1024 or not targets:
                    report['groups'].append(dict(group=index,accepted=False,reason='student context/mask'));continue
                canonical.append(row);report['accepted_groups']+=1
                report['accepted_student_x_tokens']+=len(x);report['accepted_targets']+=targets
                report['groups'].append(dict(group=index,accepted=True,x_tokens=len(x),source_family=job['source_family']))
            report['memory']=session.memory()
            complete=report['accepted_groups']==len(jobs)
            report.update(status='TASK_PILOT_COMPLETE' if complete else 'GATE_NEGATIVE',returncode=0 if complete else 8)
    except BaseException as exc:
        status,rc=disposition(exc);report.update(status=status,returncode=rc,error_type=type(exc).__name__,error=str(exc)[:1600])
    finally:
        for name,writer in (('raw',raw),('candidate',canonical)):
            if writer._total_rows:
                manifest=writer.close(lineage=info);verify(output,manifest);report[name+'_manifest']=manifest
        report['whole_wall_sec']=time.perf_counter()-started
        report['accepted_student_x_per_sec']=report['accepted_student_x_tokens']/report['whole_wall_sec']
        with (output/'report.json').open('x',encoding='utf-8') as stream:
            json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
        print('[TASK_FINAL] '+json.dumps({k:report.get(k) for k in ('status','returncode','accepted_groups','attempts',
            'accepted_student_x_tokens','accepted_targets','whole_wall_sec','accepted_student_x_per_sec','new75M_ready','error')},ensure_ascii=False),flush=True)
    return report['returncode']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=tuple(OUTPUTS),required=True)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    try:
        jobs,info=check(args.mode)
        if args.check_only:print('[CHECK_ONLY] '+json.dumps(info));return 0
        return execute(args.mode,jobs,info)
    except (FileNotFoundError,FileExistsError) as exc:print('[HOLD] '+str(exc),file=sys.stderr);return 8
    except Exception as exc:print('[ERROR] '+type(exc).__name__+': '+str(exc),file=sys.stderr);return 9


if __name__=='__main__':raise SystemExit(main())
