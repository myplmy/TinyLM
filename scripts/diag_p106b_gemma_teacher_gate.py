#!/usr/bin/env python3
"""User asset CPU gate and bounded teacher-only Gemma4 MTP off/on role pair.

Same4 code-authored profiles and sampler, orders off/on then on/off,16 requests.
One attempt each for throughput attribution; role completion is not truth or
Korean superiority. Raw replies/thoughts/finals are retained. No student or SFT.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_gemma_teacher as profile
from scripts.p106b_mtp_teacher import response_metrics
from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit,disposition
from scripts.p106b_shards import ShardWriter,verify

OUTPUT=ROOT/'HF/sft_ready/p106b_gemma_teacher_v1'
ASSET_FILE=OUTPUT/'assets.json'
COMPLETE_STATUS='TAGGED_COMPLETE'
ROLE_SCHEMA='P106B_GEMMA4_ROLE_MTP_V1'
REQUIRE_TECHNICAL_WIRE=False


def collection_complete(report):
    return (report['actual_requests']==16 and len(report['answers'])==16
            and all(a['format_status']==COMPLETE_STATUS and
                    (not REQUIRE_TECHNICAL_WIRE or a.get('wire',{}).get('technical_ready') is True)
                    for a in report['answers']))


def check(mode):
    if OUTPUT.is_symlink():raise ValueError('linked output refused')
    target=OUTPUT/'assets.json' if mode=='assets' else OUTPUT/'role'
    if target.exists() or target.is_symlink():raise FileExistsError('prior/partial output preserved; use new stage')
    info=profile.assets(False)
    if mode=='role':
        asset=ASSET_FILE
        if asset.is_symlink() or not asset.is_file():raise FileNotFoundError('Gemma full-hash asset gate required first')
        prior=json.loads(asset.read_text(encoding='utf-8'))
        if prior.get('whole_model_hash_check')!='MEASURED':raise ValueError('unmeasured model identity cannot enter role gate')
        info['asset_identity']=dict(model_sha256=prior['model_sha256'],draft_sha256=prior['draft_sha256'])
    return dict(info,mode=mode,output=str(target.relative_to(ROOT)),planned_requests=0 if mode=='assets' else 16,
                maximum_attempts=1,student_training='NOT_RUN',semantic_quality='NOT_REVIEWED')


def role(info):
    from tokenizers import Tokenizer
    from scripts.p106b_mixed_scale import TOKENIZER,TOK_SHA,digest
    if digest(TOKENIZER)!=TOK_SHA:raise ValueError('student chat32 identity differs for diagnostic wire token counts')
    tok=Tokenizer.from_file(str(TOKENIZER))
    fresh=profile.assets(True)
    if any(fresh[key]!=info['asset_identity'][key] for key in ('model_sha256','draft_sha256')):
        raise ValueError('Gemma whole-file identity changed after asset gate')
    target=OUTPUT/'role';target.mkdir(parents=True,exist_ok=False)
    writer=ShardWriter(target,'raw');began=time.perf_counter();session=None
    report=dict(schema=ROLE_SCHEMA,input=info,answers=[],arms=[],actual_requests=0,
                student_updates=0,korean_superiority='NOT_RUN',semantic_truth='NOT_REVIEWED')
    try:
        idle_before_gpu()
        with wall_limit(1800):
            for round_index,order in enumerate(((False,True),(True,False))):
                for mtp in order:
                    arm=dict(round=round_index,mtp=mtp);report['arms'].append(arm)
                    with profile.GemmaSession(mtp) as session:
                        arm.update(startup_sec=session.startup_sec,props=session.props)
                        for ci,case in enumerate(profile.cases()):
                            session.check();start=time.perf_counter();report['actual_requests']+=1
                            reply=session.request('/v1/chat/completions',profile.payload(case,1337+round_index*100+ci),timeout=180)
                            metric=response_metrics(reply,time.perf_counter()-start)
                            parsed=profile.parsed_response(reply,case['language'])
                            wire=profile.wire_counts(parsed,tok)
                            row=dict(round=round_index,mtp=mtp,case=case,reply=reply,metrics=metric,parsed=parsed,
                                     wire=wire,semantic_truth='NOT_REVIEWED',maximum_attempts=1)
                            writer.append(row);report['answers'].append(dict(round=round_index,mtp=mtp,
                                case_id=case['id'],format_status=parsed['format_status'],metrics=metric,wire=wire))
                            print('[GEMMA_ANSWER] '+json.dumps(dict(round=round_index,mtp=mtp,
                                question=case['question'],final=metric['final_text'],format_status=parsed['format_status'],
                                finish_reason=metric['finish_reason'],request_sec=metric['request_wall_sec']),ensure_ascii=False),flush=True)
                        arm.update(memory=session.memory(),signals=session.signals,server_tail=session.tail)
                        selected=[r for r in report['answers'] if r['round']==round_index and r['mtp']==mtp]
                        elapsed=sum(r['metrics']['request_wall_sec'] for r in selected)
                        supplied=sum(r['wire']['x_tokens'] for r in selected)
                        arm.update(request_sum_sec=elapsed,diagnostic_student_x_tokens=supplied,
                            diagnostic_student_x_per_sec=supplied/elapsed if elapsed else None,
                            unique_question_groups=4,production_supply_rate='NOT_MEASURED')
        complete=collection_complete(report)
        report.update(status='ROLE_COLLECTION_COMPLETE' if complete else 'ROLE_WIRE_NEGATIVE',returncode=0 if complete else 8)
    except BaseException as exc:
        status,rc=disposition(exc);report.update(status=status,returncode=rc,error_type=type(exc).__name__,error=str(exc)[:1600])
    finally:
        if writer._total_rows:
            manifest=writer.close(lineage=info);verify(target,manifest);report['raw_manifest']=manifest
        report['whole_wall_sec']=time.perf_counter()-began
        with (target/'report.json').open('x',encoding='utf-8') as stream:
            json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
        print('[GEMMA_FINAL] '+json.dumps({key:report.get(key) for key in
            ('status','returncode','actual_requests','student_updates','korean_superiority','error_type','error')},ensure_ascii=False),flush=True)
    return report['returncode']


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mode',choices=('assets','role'),required=True)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute',action='store_true');action.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    try:
        info=check(args.mode)
        if args.check_only:print('[CHECK_ONLY] '+json.dumps(info,ensure_ascii=False));return 0
        if args.mode=='assets':
            measured=profile.assets(True);OUTPUT.mkdir(parents=True,exist_ok=True)
            with (OUTPUT/'assets.json').open('x',encoding='utf-8') as stream:
                json.dump(measured,stream,ensure_ascii=False,indent=2);stream.write('\n')
            print('[GEMMA_ASSETS] '+json.dumps(measured,ensure_ascii=False));return 0
        return role(info)
    except (FileNotFoundError,FileExistsError) as exc:print('[HOLD] '+str(exc),file=sys.stderr);return 8
    except Exception as exc:print('[ERROR] '+type(exc).__name__+': '+str(exc),file=sys.stderr);return 9


if __name__=='__main__':raise SystemExit(main())
