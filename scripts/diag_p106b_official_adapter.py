#!/usr/bin/env python3
"""Bounded real-checkpoint likelihood oracle, not a benchmark quality test."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import sysconfig
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.p106b_official_lm_adapter import research_adapter, direct_label_oracle
from scripts.prepare_p106b_official_eval import write_report

OUTPUT=ROOT/'test_result/evidence/p106b_official_adapter_v1/native595-f'
CASES=(('Question: one plus one?\nAnswer:',' two'),
       ('','Hello'),('질문: 사과의 색을 말하세요.\n답:',' 빨강'),
       ('A B C D\n',' A B'))
ATOL,RTOL=1e-5,1e-4  # Existing test_p070b_cla_routes.py inference regression.
SOURCES=('scripts/diag_p106b_official_adapter.py','scripts/p106b_official_lm_adapter.py',
         'scripts/test_p106b_official_lm_adapter.py','scripts/interactive_research_infer.py',
         'scripts/diag_p101a_mtp_parity.py','tinylm/infer/dialogue.py')


def sources():
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest().upper() for name in SOURCES}


def execute(expected):
    source=sources();identity=hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest().upper()
    if identity!=expected:raise ValueError('preregistered adapter source fingerprint differs')
    if OUTPUT.exists():raise FileExistsError('old/partial canary preserved')
    if datetime.now(timezone.utc).timestamp()+600>datetime(2026,10,23,7,30,tzinfo=timezone.utc).timestamp():
        raise ValueError('600sec canary no longer fits model deadline')
    OUTPUT.mkdir(parents=True,exist_ok=False)
    tick=time.monotonic();report=dict(schema='P106B_OFFICIAL_ADAPTER_GPU_ORACLE_V1',status='STARTED',
        source_sha256=source,source_set_sha256=identity,requests=[list(x) for x in CASES],
        atol=ATOL,rtol=RTOL,tolerance_source='scripts/test_p070b_cla_routes.py',
        model='native595-f',updates=0,checkpoint_writes=0,quality_claim=False,
        started_at=datetime.now(timezone.utc).isoformat(),oracle_blocks=[])
    try:
        from scripts.p106b_gate_runtime import wall_limit
        from lm_eval.api.instance import Instance
        with wall_limit(600),research_adapter('native595-f',
                runtime_root=Path(sysconfig.get_paths()['purelib']),batch_size=4) as adapter:
            scorer=adapter.core.score_batch
            def compare(batch):
                left=scorer(batch)
                right=direct_label_oracle(scorer.runtime['torch'],scorer.forward,batch,
                                         scorer.runtime['cfg'].vocab_size)
                rows=[]
                for a,b in zip(left,right):
                    close=math.isclose(a[0],b[0],abs_tol=ATOL,rel_tol=RTOL) and a[1]==b[1]
                    rows.append(dict(gather=list(a),full_label=list(b),abs_difference=abs(a[0]-b[0]),close=close))
                report['oracle_blocks'].append(dict(lengths=batch['lengths'],labels=batch['labels'],rows=rows))
                if not all(row['close'] for row in rows):raise ValueError('GPU full-label likelihood oracle negative')
                return left
            compare.close=scorer.close
            adapter.core.score_batch=compare
            requests=[Instance(request_type='loglikelihood',doc={},arguments=row,idx=i,
                       metadata=('synthetic_adapter_canary',i,1)) for i,row in enumerate(CASES)]
            batched=adapter.loglikelihood(requests,disable_tqdm=True)
            adapter.core.batch_size=1
            separate=adapter.loglikelihood(requests,disable_tqdm=True)
            report['batch_vs_separate']=[dict(batched=list(a),separate=list(b),
                abs_difference=abs(a[0]-b[0]),close=math.isclose(a[0],b[0],abs_tol=ATOL,rel_tol=RTOL) and a[1]==b[1])
                for a,b in zip(batched,separate)]
            report['adapter_diagnostics']=adapter.diagnostics()
            if not all(r['close'] for r in report['batch_vs_separate']):
                raise ValueError('GPU right-pad/batch numerical oracle negative')
            # Restore the original owned callback so close() releases its model.
            adapter.core.score_batch=scorer
            scorer=None
        report['sources_unchanged']=sources()==source
        if not report['sources_unchanged']:raise ValueError('source changed during model canary')
        report.update(status='OFFICIAL_ADAPTER_GPU_ORACLE_COMPLETE',returncode=0)
    except BaseException as exc:
        report.update(status='OFFICIAL_ADAPTER_GPU_ORACLE_ERROR',returncode=9,
                      error_type=type(exc).__name__,error=str(exc)[:1800])
        raise
    finally:
        report.update(ended_at=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-tick)
        write_report(OUTPUT/'report.json',report)
    return dict(status=report['status'],report=str(OUTPUT/'report.json'),
                oracle_blocks=len(report['oracle_blocks']),quality_claim=False,
                wall_seconds=report['wall_seconds'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true')
    p.add_argument('--source-sha256');a=p.parse_args()
    if not a.execute:
        source=sources();value=dict(status='SOURCE_ONLY',source_sha256=hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest().upper())
    else:value=execute(a.source_sha256)
    print(json.dumps(value,ensure_ascii=False,sort_keys=True))


if __name__=='__main__':main()
