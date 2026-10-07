#!/usr/bin/env python3
"""User-only Gemma shortage production with immutable batches and explicit resume.

Existing partial C, raw sources, pilot outputs and weights are read-only.
Every batch is new; published manifests are validated before cursor replay.
An incomplete75M does not load a student. No network/download/protected data.
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
from scripts import p106b_gemma_deficit as control
from scripts import diag_p106b_gemma_task_pilot as gate
from scripts import p106b_gemma_task_contract as tasks
from scripts import p106b_gemma_labels as teacher
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit,disposition
from scripts.p106b_public_refill import english_rows
from scripts.p106b_mixed_scale import TOKENIZER,TOK_SHA,digest,safe_repo_path
from scripts.p106b_teacher_wrapper import wrap_turns
from tinylm.data.sft import conversation_split_key


def require_pilots():
    checks={}
    for mode,count in (('contract16',16),('family64',64)):
        path=safe_repo_path(gate.OUTPUTS[mode]/'report.json');sha=digest(path)
        report=json.loads(path.read_text(encoding='utf-8'));info=report.get('input',{})
        if (report.get('schema')!='P106B_GEMMA_TASK_PILOT_V1' or report.get('status')!='TASK_PILOT_COMPLETE'
                or report.get('accepted_groups')!=count or report.get('candidate_manifest',{}).get('rows')!=count
                or info.get('mode')!=mode or info.get('wire_contract')!=tasks.CONTRACT
                or info.get('old_report_sha256')!=gate.OLD_SHA or info.get('role_report_sha256')!=gate.ROLE_SHA):
            raise FileNotFoundError('successful exact'+mode+' required before bulk teacher allocation')
        verify(path.parent,report['candidate_manifest'])
        checks[mode+'_sha256']=sha
    return dict(checks,base_report_sha256=control.BASE_SHA,tokenizer_sha256=TOK_SHA,
                task_contract=tasks.CONTRACT,mtp=False,sampler=teacher.SAMPLER,
                thinking=teacher.THINKING,max_output=teacher.MAX_OUTPUT,context=teacher.CONTEXT,
                code_sha256={name:digest(ROOT/name) for name in ('scripts/p106b_gemma_deficit.py',
                    'scripts/diag_p106b_gemma_deficit_production.py','scripts/p106b_gemma_task_contract.py',
                    'scripts/p106b_gemma_labels.py','scripts/p106b_gemma_teacher.py',
                    'scripts/p106b_teacher_wrapper.py','tinylm/chat/canonical.py','tinylm/data/sft.py')})


def state_from_saved(tok,base):
    state=control.Quotas(tok)
    for row in control.base_rows(base):
        if state.admit(row,base=True) is None:raise ValueError('base cannot be replayed')
    if dict(state.tokens)!=base['nonpadding_tokens']:
        raise ValueError('base nonpadding counts differ from source report')
    cursor=(-1,-1)
    batches=list(control.batch_reports()) if control.OUTPUT.exists() else []
    for directory,report in batches:
        if report.get('base_report_sha256')!=control.BASE_SHA:raise ValueError('batch lineage differs')
        if 'raw_manifest' in report:verify(directory,report['raw_manifest'])
        if 'candidate_manifest' in report:
            for row in control.rows(directory,report['candidate_manifest']):
                if state.admit(row) is None:raise ValueError('saved teacher admission differs on resume')
        if dict(state.tokens)!=report['nonpadding_tokens']:
            raise ValueError('published batch counter/canonical mismatch; no silent resume')
        cursor=tuple(report['cursor'])
    return state,cursor,len(batches)


def produce_group(session,source,language,profile,seed,raw,identity):
    turns,refs=[],[]
    for turn in range(3 if profile=='multiturn' else 1):
        accepted=None
        for attempt in range(1,4):
            session.check()
            payload=tasks.payload(source,language,profile,(seed+turn*10+attempt)%2147483647,history=turns)
            prompt=session.request('/apply-template',{'messages':payload['messages']})['prompt']
            tokens=session.request('/tokenize',dict(content=prompt,add_special=False,parse_special=True))['tokens']
            if len(tokens)+teacher.MAX_OUTPUT+128>teacher.CONTEXT:
                raise ValueError('source token budget: no silent truncation')
            began=time.perf_counter();reply=session.request('/v1/chat/completions',payload,timeout=300)
            parsed=teacher.parsed_response(reply,language);reason=''
            if parsed['format_status']==teacher.COMPLETE:
                try:accepted=tasks.learner_turn(parsed['parsed_content'],language,profile,history=turns)
                except (ValueError,TypeError) as exc:reason=str(exc)
            else:reason=parsed.get('parse_error') or parsed['format_status']
            raw.append(dict(source=source,language=language,task=profile,turn=turn+1,attempt=attempt,
                payload=payload,reply=reply,parsed=parsed,producer_learner_turn=accepted,
                structural_reason=reason,input_tokens=len(tokens),request_sec=time.perf_counter()-began))
            print('[DEFICIT_ANSWER] '+json.dumps(dict(source_id=source['meta']['source_id'],language=language,
                task=profile,turn=turn+1,attempt=attempt,final=parsed.get('teacher_final_content'),
                structural_reason=reason),ensure_ascii=False),flush=True)
            if accepted is not None:
                thought=parsed.get('teacher_reasoning_content','')
                refs.append(dict(raw_row_1based=raw._total_rows,
                    sha256=hashlib.sha256(thought.encode()).hexdigest().upper(),in_student=False));break
        if accepted is None:return None
        turns.append(accepted)
    m=source['meta'];key=conversation_split_key(source).hex().upper()
    row=wrap_turns(turns,source_id=m['source_id'],source_sha256=m['source_sha256'],
        teacher_model_sha256=identity['model_sha256'],language=language,source_license=m['source_license'],
        generation_id='deficit_'+str(seed),source_repo=m['source_repo'],source_revision=m['source_revision'],
        source_object_id=m['source_id'],source_transform='teacher_answer',parent_concept_id=key,
        source_rights_status=m.get('rights_status','CARD_ONLY'))
    row['meta'].update(source_family=m['source_family'],original_source_language=m['language'],
        producer='Gemma4-12B',task_profile=profile,wire_contract=tasks.CONTRACT,
        teacher_reasoning_refs=refs,role_origin='producer_contract_teacher_content')
    return row


def production(*,resume=False,max_wall_sec=21600):
    from tokenizers import Tokenizer
    operation_began=time.perf_counter()
    info=require_pilots();base=control.base_report()
    if digest(TOKENIZER)!=TOK_SHA:raise ValueError('chat32 tokenizer changed')
    safe_repo_path(control.OUTPUT)
    if control.OUTPUT.exists() and not resume:raise FileExistsError('production exists; explicit resume only')
    if resume and not control.OUTPUT.is_dir():raise FileNotFoundError('no production to resume')
    if resume:
        saved=json.loads(safe_repo_path(control.OUTPUT/'inputs.json').read_text(encoding='utf-8'))
        if saved!=info:raise ValueError('resume source/pilot/teacher controls changed')
    # Only pinned original public source files; never TinyDataset or downloads.
    for spec in base['sources']:
        path=safe_repo_path(ROOT/spec['path'])
        if path.parts[len(ROOT.parts):len(ROOT.parts)+2]!=('HF','sft_sources') or digest(path)!=spec['sha256']:
            raise ValueError('exact pinned public source changed')
    tok=Tokenizer.from_file(str(TOKENIZER));state,cursor,number=state_from_saved(tok,base)
    if state.report()['token_target_ready']:print('[PRODUCTION_ALREADY_READY] finalize next');return 0
    if number:
        last=list(control.batch_reports())[-1][1]
        if last.get('status')=='SOURCE_EXHAUSTED':
            raise FileNotFoundError('pinned source pool exhausted; preserve shortage and add new approved sources, not repeated filler')
    identity=teacher.assets(True)
    role=gate.read_report(gate.previous.role_gate.OUTPUT/'role/report.json',gate.ROLE_SHA)
    if any(identity[k]!=role['input']['asset_identity'][k] for k in ('model_sha256','draft_sha256')):
        raise ValueError('teacher identity differs')
    remaining=max_wall_sec-(time.perf_counter()-operation_began)
    if remaining<=0:raise FileNotFoundError('input verification/replay used the wall budget; no teacher started')
    if not resume:
        control.OUTPUT.mkdir(exist_ok=False)
        with (control.OUTPUT/'inputs.json').open('x',encoding='utf-8') as stream:
            json.dump(info,stream,ensure_ascii=False,indent=2);stream.write('\n')
    directory=control.OUTPUT/('batch_'+str(number).zfill(6));directory.mkdir(exist_ok=False)
    raw,canonical=ShardWriter(directory,'raw'),ShardWriter(directory,'candidates')
    before=state.report();began=time.perf_counter();accepted=0;scanned=0
    report=dict(schema='P106B_GEMMA_DEFICIT_BATCH_V1',input=info,base_report_sha256=control.BASE_SHA,
        cursor=list(cursor),semantic_truth='PSEUDO_UNVERIFIED',formal_train_ready=False,student_training='NOT_RUN')
    try:
        idle_before_gpu()
        with wall_limit(remaining),teacher.GemmaSession(False) as session:
            completed=False
            for source_index,spec in enumerate(base['sources']):
                if source_index<cursor[0]:continue
                for ordinal,source in enumerate(english_rows(spec)):
                    if (source_index,ordinal)<=cursor:continue
                    scanned+=1
                    if scanned%10000==0:
                        print('[DEFICIT_PROGRESS] '+json.dumps(dict(scanned=scanned,cursor=[source_index,ordinal],
                            deficits=state.report()['teacher_deficit_tokens'])),flush=True)
                    key=conversation_split_key(source).hex().upper();m=source['meta']
                    family=control.capability.engine.family_bucket(m['source_family']);split=state.source_split(key)
                    language=m['language'];profile=state.profile(split,language,family,key)
                    if profile is not None:
                        import shutil
                        if shutil.disk_usage(control.OUTPUT).free<8*(1<<30):
                            raise FileNotFoundError('production paused: need8GiB free; published batches preserved')
                        # A interrupted/failed source is consumed, not silently given a fresh3-try budget on resume.
                        report['cursor']=[source_index,ordinal]
                        try:
                            seed=int(hashlib.sha256((str(source_index)+':'+str(ordinal)+':'+language).encode()).hexdigest()[:8],16)&0x7fffffff
                            row=produce_group(session,source,language,profile,
                                seed,raw,identity)
                            row=state.admit(row) if row is not None else None
                        except ValueError as exc:
                            # Structure/budget limits are preserved as rejected candidates, not semantic judgements.
                            raw.append(dict(source_ref={k:m.get(k) for k in ('source_id','source_repo','source_revision','source_sha256','source_family')},
                                structural_stop=str(exc),semantic_truth='PSEUDO_UNVERIFIED'))
                            row=None
                        if row is not None:
                            row['meta']['teacher_batch']=directory.name;canonical.append(row);accepted+=1
                    report['cursor']=[source_index,ordinal]
                    if state.report()['token_target_ready']:completed=True;break
                    if time.perf_counter()-operation_began>=max_wall_sec:completed=True;break
                if completed:break
            report['memory']=session.memory()
            ready=state.report()['token_target_ready']
            report.update(status='PRODUCTION_READY' if ready else 'PRODUCTION_PAUSED' if completed else 'SOURCE_EXHAUSTED',returncode=0 if ready else 8)
    except BaseException as exc:
        status,rc=disposition(exc);report.update(status=status,returncode=rc,error_type=type(exc).__name__,error=str(exc)[:1600])
    finally:
        for name,writer in (('raw',raw),('candidate',canonical)):
            if writer._total_rows:
                manifest=writer.close(lineage=info);verify(directory,manifest);report[name+'_manifest']=manifest
        report.update(state.report(),accepted_groups=accepted,scanned_source_rows=scanned,
                      whole_wall_sec=time.perf_counter()-operation_began,
                      generation_window_sec=time.perf_counter()-began)
        delta=sum(state.tokens['train:'+l]-before['nonpadding_tokens'].get('train:'+l,0) for l in ('ko','en'))
        report['new_train_x_tokens']=delta;report['new_train_x_per_sec']=delta/report['whole_wall_sec']
        report['estimated_remaining_sec']=sum(report['teacher_deficit_tokens'].values())/report['new_train_x_per_sec'] if delta else None
        with (directory/'report.json').open('x',encoding='utf-8') as stream:
            json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
        print('[DEFICIT_FINAL] '+json.dumps({k:report.get(k) for k in ('status','returncode','accepted_groups',
            'new_train_x_tokens','new_train_x_per_sec','teacher_deficit_tokens','task_deficit_tokens',
            'validation_deficit_tokens','estimated_remaining_sec','error')},ensure_ascii=False),flush=True)
    return report['returncode']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('produce','resume','finalize','wire','train','eval'),required=True)
    parser.add_argument('--max-wall-sec',type=int,default=21600,help='produce/resume wall budget including input verification/replay')
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    try:
        if not 60<=args.max_wall_sec<=21600:raise ValueError('wall limit must be60..21600 seconds')
        if args.mode not in ('produce','resume') and '--max-wall-sec' in sys.argv:
            raise ValueError('wall parameter applies only to producer/resume, not ignored learner options')
        if args.mode=='eval':
            result=control.evaluate(execute=args.execute)
            if not args.execute:print('[CHECK_ONLY] '+json.dumps(result));return 0
            return result
        if args.mode in ('wire','train'):
            result=control.learner(args.mode=='wire',execute=args.execute)
            if not args.execute:print('[CHECK_ONLY] '+json.dumps(result));return 0
            return result
        info=require_pilots();control.base_report()
        if args.check_only:print('[CHECK_ONLY] '+json.dumps(info));return 0
        if args.mode=='finalize':
            saved=json.loads(safe_repo_path(control.OUTPUT/'inputs.json').read_text(encoding='utf-8'))
            if saved!=info:raise ValueError('production input/code contract changed before merge')
            from tokenizers import Tokenizer
            if digest(TOKENIZER)!=TOK_SHA:raise ValueError('chat32 tokenizer differs')
            report=control.finalize(Tokenizer.from_file(str(TOKENIZER)))
            print('[FINAL_CORPUS] '+json.dumps(report,ensure_ascii=False));return 0
        return production(resume=args.mode=='resume',max_wall_sec=args.max_wall_sec)
    except (FileNotFoundError,FileExistsError) as exc:print('[HOLD] '+str(exc),file=sys.stderr);return 8
    except KeyboardInterrupt:print('[INTERRUPTED] partial batch preserved',file=sys.stderr);return 130
    except Exception as exc:print('[ERROR] '+type(exc).__name__+': '+str(exc),file=sys.stderr);return 9


if __name__=='__main__':raise SystemExit(main())
