#!/usr/bin/env python3
"""CPU only, immutable relation responses split by history/field/language."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
import json
from scripts import diag_p106b_relation_evaluate as evaluation
from scripts import p106b_relation_strata as method
from scripts.p106b_gate_runtime import GateNegative
from scripts.p106b_shards import verify
CODE=('scripts/p106b_relation_strata.py','scripts/test_p106b_relation_strata.py','scripts/diag_p106b_relation_strata.py')


def info():
    return dict(schema='P106B_RELATION_HISTORY_FIELD_STRATA_V1',code_sha256={p:evaluation.course.training.data.digest(ROOT/p) for p in CODE},
        operation='CPU_RAW_READBACK_ONLY',student_or_teacher_loading='NOT_RUN',data_or_checkpoint_writes=False,
        semantic_judgment=False,automatic_training_exclusion=False,primary_checkpoint='final4epoch')


def run():
    evaluation.course.prior.producer.legacy.source.deadline()
    destination=evaluation.EVIDENCE/'strata_readback.json'
    if destination.exists():raise GateNegative('old strata report preserved')
    report=evaluation.legacy.required(evaluation.EVIDENCE/'report.json')
    if report['status']!='RELATION_ALL_ENDPOINTS_EVALUATED' or report['code_sha256']!=evaluation.info()['code_sha256']:raise ValueError('complete same-code endpoint evaluation required')
    rows={};summaries={};invariance={}
    for arm,p in report['endpoints'].items():
        f=p['metrics']['fiction'];directory=ROOT/f['directory'];verify(directory,f['manifest'])
        rows[arm]=list(evaluation.course.training.data.stream_rows(directory,f['manifest']))
        if evaluation.method.summarize(rows[arm])!=f['counts']:raise ValueError('raw primary score counters differ')
        summaries[arm]=method.counts(rows[arm]);invariance[arm]=method.first_invariance(rows[arm])
        if invariance[arm]['root_language_groups']!=512 or invariance[arm]['first_output_disagreements']:raise ValueError('same-first-input determinism failed')
    pairs={a+'__'+b:method.pairs_by_lane(rows[a],rows[b]) for a,b in (('parent','fact0'),('parent','fact1'),('fact0','fact1'))}
    result=dict(info(),status='RELATION_HISTORY_FIELD_RAW_VERIFIED',counts=summaries,pairs=pairs,first_prefix_invariance=invariance,
        evaluation_report_sha256=evaluation.course.training.data.digest(evaluation.EVIDENCE/'report.json'),
        interpretation='provided wrong history is not self-error recovery; exact fictional contract is not natural world truth; fixed sample CIs not adjusted discovery thresholds')
    evaluation.course.training.write(destination,result)
    print('[RELATION_STRATA] '+json.dumps(dict(invariance=invariance,actual={a:summaries[a]['ACTUAL_MODEL/all'] for a in rows},provided_error={a:summaries[a]['PROVIDED_WRONG_HISTORY/all'] for a in rows})),flush=True);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if a.check_only:print('[RELATION_STRATA_CHECK_ONLY] '+json.dumps(info()));return 0
    try:return run()
    except (GateNegative,FileNotFoundError) as exc:print('[RELATION_STRATA_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[RELATION_STRATA_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
