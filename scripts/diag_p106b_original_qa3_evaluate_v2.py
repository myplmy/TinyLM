#!/usr/bin/env python3
"""Reserved original three-QA actual histories and separate retention probes."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from datetime import datetime,timezone
import gc
import json
import time
from scripts import diag_p106b_original_qa3_train_v2 as training
from scripts import p106b_original_qa3_evaluation as method
from scripts import diag_p106b_relation_evaluate as reference
from scripts import p106b_relation_strata as strata
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
course=training.course
EVIDENCE=course.EVIDENCE/'evaluate'
LOCAL=ROOT/'test_result/evidence/local'/course.TAG/'evaluate'
CODE=('scripts/p106b_original_qa3_evaluation.py','scripts/test_p106b_original_qa3_evaluation.py',
    'scripts/diag_p106b_original_qa3_evaluate_v2.py')


def info():
    return dict(schema='P106B_ORIGINAL_QA3_ACTUAL_V2',tag=course.TAG,code_sha256={p:course.training.data.digest(ROOT/p) for p in CODE},
        endpoints=['parent',*course.ARMS],natural_source_roots=64,actual_answers_per_endpoint=192,gold_later_answers_per_endpoint=128,
        precision='FP32_MATH',temperature=0.,top_k=1,max_new=64,auxiliary_used_in_generation=False,
        semantic_truth='ORIGINAL_PUBLIC_UNVERIFIED',retention_fiction_scope='previously inspected held-out development probe, not new intelligence TEST',
        checkpoint_policy='fixed final4epoch, no TEST choice')


def generations(model,cfg,tok,rows,directory,fiction=False):
    import torch
    writer=ShardWriter(directory,'fiction_retention' if fiction else 'natural_three_qa');events=[];emit=reference.generation.emit_function(model,cfg,tok)
    model.eval();model.freeze_quant()
    try:
        with torch.no_grad():
            for row in rows:
                values=reference.method.collect(row,emit) if fiction else method.collect(row,emit)
                for event in values:writer.append(event);events.append(event)
    finally:model.clear_quant();model.train()
    manifest=writer.close(lineage=info());verify(directory,manifest)
    counts=strata.counts(events) if fiction else method.counts(events)
    if not fiction:
        coverage=Counter(e['history'] for e in events)
        if dict(coverage)!=dict(ACTUAL_MODEL=192,GOLD_REFERENCE=128):raise ValueError('all64 three-turn actual192/gold128 required')
    return dict(directory=str(directory.relative_to(ROOT)),manifest=manifest,counts=counts)


def run(a):
    import torch
    from tinylm.infer.generate import _strip
    from scripts.p106b_education_followup import answers
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    r,rows,_=course.read_course();reports={arm:reference.legacy.required(course.EVIDENCE/arm/'report.json') for arm in course.ARMS}
    for arm,p in reports.items():
        if p['code_sha256']!=training.info()['code_sha256'] or p['status']!='ORIGINAL_QA3_TRAINED_TEST_PENDING' or p['updates']!=200:raise ValueError('complete same-code full200 arms required')
        if course.training.data.digest(ROOT/p['checkpoint'])!=p['checkpoint_sha256']:raise ValueError('trained endpoint changed')
    if EVIDENCE.exists() or LOCAL.exists():raise GateNegative('old evaluation outputs preserved')
    test=rows['test_natural_three']
    if len(test)!=64 or Counter(x['meta']['language'] for x in test)!=dict(ko=32,en=32):raise ValueError('reserved64 exact cohort required')
    idle_before_gpu();EVIDENCE.mkdir(parents=True,exist_ok=False);began=time.perf_counter();result={}
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    with wall_limit(a.max_wall_sec):
        for arm in ('parent',*course.ARMS):
            torch,model,cfg,tok,_,_=training.load_parent();cp=course.PARENT;identity=course.PARENT_SHA
            if arm!='parent':
                p=reports[arm];cp=ROOT/p['checkpoint'];identity=p['checkpoint_sha256'];saved=torch.load(cp,map_location='cpu',weights_only=True)
                if saved['original_qa3_curriculum']!=dict(tag=course.TAG,arm=arm,epoch=4):raise ValueError('fixed final4 lineage')
                model.load_state_dict(_strip(saved['model']),strict=True);del saved
            initial=course.training.state_fingerprint(model);model=model.cuda();directory=LOCAL/arm
            values=dict(natural=generations(model,cfg,tok,test,directory),fiction_retention=generations(model,cfg,tok,rows['retention_fiction'],directory,fiction=True),
                code_development=reference.legacy.generate(model,cfg,tok,rows['dev_code'],directory,'known_code_dev640'),
                native32crop=course.training.native_ce(model,course.prior.NATIVE),legacy8=answers(PrecisionForward(model,'fp32_math'),cfg,tok,directory,'legacy8'))
            if course.training.state_fingerprint(model)!=initial:raise ValueError('evaluation changed body')
            result[arm]=dict(checkpoint=str(cp.relative_to(ROOT)),checkpoint_sha256=identity,core_before_after_sha256=initial,metrics=values)
            course.training.write(EVIDENCE/(arm+'_report.json'),dict(info(),arm=arm,**result[arm]))
            print('[ORIGINAL_QA3_EVAL_ENDPOINT] '+json.dumps(dict(arm=arm,natural=values['natural']['counts'],native=values['native32crop'],legacy8=values['legacy8'])),flush=True)
            del model;gc.collect();torch.cuda.empty_cache()
    course.training.write(EVIDENCE/'report.json',dict(info(),status='ORIGINAL_QA3_ACTUAL_EVALUATED',endpoints=result,
        whole_sec=time.perf_counter()-began,corpus_sha256=course.training.data.digest(course.CORPUS/'report.json')));return 0


def readback():
    report=reference.legacy.required(EVIDENCE/'report.json');target=EVIDENCE/'paired_readback.json'
    if target.exists():raise GateNegative('old raw recount preserved')
    if report['code_sha256']!=info()['code_sha256']:raise ValueError('evaluation CODE changed')
    natural={};fiction={};counts={}
    for arm,p in report['endpoints'].items():
        natural_rows=None;fiction_rows=None
        for lane in ('natural','fiction_retention','code_development'):
            m=p['metrics'][lane];verify(ROOT/m['directory'],m['manifest'])
            rows=list(course.training.data.stream_rows(ROOT/m['directory'],m['manifest']))
            if lane=='natural':
                if method.counts(rows)!=m['counts']:raise ValueError('natural raw counter mismatch')
                natural_rows=rows
            elif lane=='fiction_retention':
                if strata.counts(rows)!=m['counts']:raise ValueError('fiction raw counter mismatch')
                fiction_rows=rows
        natural[arm]=natural_rows;fiction[arm]=fiction_rows;counts[arm]=method.counts(natural_rows)
    pairs={a+'__'+b:method.paired(natural[a],natural[b]) for a,b in (('parent','first'),('parent','three'),('first','three'))}
    retention=strata.pairs_by_lane(fiction['first'],fiction['three'])
    course.training.write(target,dict(info(),status='ORIGINAL_QA3_RAW_RECOUNTED',counts=counts,pairs=pairs,fiction_retention_pairs=retention,
        evaluation_sha256=course.training.data.digest(EVIDENCE/'report.json'),interpretation='information/targets/turns differ; not pure role format, not semantic truth'))
    print('[ORIGINAL_QA3_PAIRED] '+json.dumps(pairs),flush=True);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('evaluate','readback'),required=True);p.add_argument('--max-wall-sec',type=int,default=7200)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=10800:p.error('bounded60..10800')
    if a.check_only:print('[ORIGINAL_QA3_EVAL_CHECK_ONLY] '+json.dumps(info()));return 0
    try:
        course.prior.producer.legacy.source.deadline();a.max_wall_sec=min(a.max_wall_sec,int((course.prior.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds())-2700)
        if a.max_wall_sec<60:raise GateNegative('45minute closure margin')
        return run(a) if a.mode=='evaluate' else readback()
    except (GateNegative,FileNotFoundError) as exc:print('[ORIGINAL_QA3_EVAL_HOLD] '+str(exc));return 8
    except KeyboardInterrupt:print('[ORIGINAL_QA3_EVAL_INTERRUPTED] preserve partial outputs');return 130
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[ORIGINAL_QA3_EVAL_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
