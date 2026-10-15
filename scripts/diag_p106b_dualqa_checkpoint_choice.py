#!/usr/bin/env python3
"""Lock DEV-only choices before any primary fresh-TEST model run."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from datetime import datetime,timezone
import json
from scripts import p106b_dualqa_checkpoint_choice as choice
from scripts import diag_p106b_dualqa_curriculum as course
from scripts import diag_p106b_dualqa_eval as evaluate
TARGET=course.EVIDENCE/'devbest_selection.json'
CODE=('scripts/p106b_dualqa_checkpoint_choice.py','scripts/test_p106b_dualqa_checkpoint_choice.py','scripts/diag_p106b_dualqa_checkpoint_choice.py')


def run():
    course.producer.legacy.source.deadline()
    if TARGET.exists():raise FileExistsError('old selection preserved')
    if evaluate.EVIDENCE.exists() or evaluate.LOCAL.exists():raise ValueError('selection must be locked BEFORE primary TEST starts')
    selected={};inputs={}
    for arm in course.data.ARMS:
        path=course.EVIDENCE/arm/'report.json';r=course.producer.legacy.source.required(path)
        if r['code_sha256']!=course.info()['code_sha256']:raise ValueError('matching frozen student code required')
        selected[arm]=choice.choose(r)
        if course.training.data.digest(ROOT/selected[arm]['checkpoint'])!=selected[arm]['checkpoint_sha256']:raise ValueError('selected checkpoint changed')
        inputs[arm]=dict(path=str(path.relative_to(ROOT)),sha256=course.training.data.digest(path))
    result=dict(schema='P106B_DUALQA_DEV_SELECTION_LOCK_V1',tag=course.TAG,created_at_utc=datetime.now(timezone.utc).isoformat(),
        choices=selected,training_report_refs=inputs,code_sha256={p:course.training.data.digest(ROOT/p) for p in CODE},
        corpus_report_sha256=course.training.data.digest(course.CORPUS/'report.json'),primary_test_started=False,
        primary_final4epoch_unchanged=True,models_loaded=0,training=False,semantic_truth='NOT_RUN')
    course.training.write(TARGET,result);print('[DUALQA_DEV_SELECTION_LOCKED] '+json.dumps(result),flush=True);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:p.error('explicit CPU selection lock required')
    try:return run()
    except FileNotFoundError as exc:print('[DUALQA_DEV_SELECTION_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[DUALQA_DEV_SELECTION_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
