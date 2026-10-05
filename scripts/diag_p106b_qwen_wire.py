#!/usr/bin/env python3
"""New Qwen wrapper stage; raw replies retained, no student re-training."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_qwen_teacher as p
from scripts.diag_p106b_qwen_coload import QwenSession
from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit,disposition
from scripts.p106b_mtp_teacher import response_metrics

OUTPUT=ROOT/'test_result/evidence/101_P106B_Stage6bW_qwen_wrapper_role.json'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    a=parser.add_mutually_exclusive_group(required=True)
    a.add_argument('--execute',action='store_true');a.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    if OUTPUT.exists() or OUTPUT.is_symlink():raise FileExistsError('preserve original, new stage required')
    info=p.assets(True)
    if args.check_only:print('[CHECK_ONLY] '+json.dumps(info,ensure_ascii=False));return 0
    r=dict(schema='P106B_QWEN_WRAPPER_ROLE_V1',input=info,answers=[],returncode=None,
           student_training='NOT_RUN',checkpoint_saved=False,semantic_quality='NOT_REVIEWED')
    session=None;began=time.perf_counter()
    try:
        idle_before_gpu()
        with wall_limit(300),QwenSession('qwen') as session:
            for index,case in enumerate(p.cases()):
                for attempt in range(1,4):
                    t=time.perf_counter();reply=session.request('/v1/chat/completions',p.payload(case,1337+index+attempt-1),timeout=180)
                    parsed=p.parsed_response(reply,case['language']);session.check()
                    row=dict(case=case,attempt=attempt,reply=reply,parsed=parsed,
                        metrics=response_metrics(reply,time.perf_counter()-t))
                    r['answers'].append(row)
                    print('[QWEN_WRAPPER_ANSWER] '+json.dumps(dict(id=case['id'],attempt=attempt,
                        question=case['question'],final=row['metrics']['final_text'],status=parsed['format_status']),ensure_ascii=False),flush=True)
                    if parsed['format_status']=='TAGGED_COMPLETE':break
            accepted={x['case']['id'] for x in r['answers'] if x['parsed']['format_status']=='TAGGED_COMPLETE'}
            r.update(status='ROLE_WIRE_PASSED' if len(accepted)==4 else 'ROLE_WIRE_NEGATIVE',
                     returncode=0 if len(accepted)==4 else 8,accepted_profiles=len(accepted),memory=session.memory())
    except BaseException as exc:
        status,rc=disposition(exc);r.update(status=status,returncode=rc,error_type=type(exc).__name__,error=str(exc)[:1000])
    finally:
        r['wall_sec']=time.perf_counter()-began
        if session:r.update(server_signals=session.signals,server_tail=session.tail)
        with OUTPUT.open('x',encoding='utf-8') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
        print('[QWEN_WRAPPER_FINAL] '+json.dumps(dict(status=r.get('status'),returncode=r['returncode'],
            accepted_profiles=r.get('accepted_profiles'),evidence=str(OUTPUT.relative_to(ROOT))),ensure_ascii=False),flush=True)
    return r['returncode']


if __name__=='__main__':raise SystemExit(main())
