#!/usr/bin/env python3
"""Actual three-turn evidence recovery and fixed retention, independent namespace."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from datetime import datetime,timezone
import gc
import itertools
import json
import time
from scripts import diag_p106b_evidence_preference_train as training
from scripts import p106b_evidence_recovery_evaluation as method
from scripts import diag_p106b_repair_role_evaluate as previous
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
course=training.course
EVIDENCE=course.EVIDENCE/'evaluate'
LOCAL=ROOT/'test_result/evidence/local'/course.TAG/'evaluate'
CODE=(*training.CODE,'scripts/p106b_evidence_recovery_evaluation.py','scripts/test_p106b_evidence_preference_evaluation.py',
    'scripts/diag_p106b_evidence_preference_evaluate.py')


def info():
    return dict(schema='P106B_EVIDENCE_PREFERENCE_ACTUAL_EVALUATION_V1',tag=course.TAG,
        code_sha256={p:course.training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        endpoints=['parent',*course.ARMS],checkpoint_policy='fixed final64, no test-selected epoch',
        new_test='128 new initial-visible neutral facts excluding both old128 cohorts,2languages,4mask/query cells,style3',
        test_conversations=1024,actual_answers=3072,gold_history_answers=2048,
        first_query_intents='512 sufficient scalar and512 insufficient free clarification per endpoint',
        clarification_semantics='POSTHOC_REVIEW; exact phrase agreement not semantic truth',
        source_eval='historical posthoc DEV only; at least one reversed question-generation task, not pure QA truth',
        precision='FP32_MATH',temperature=0.,top_k=1,max_new=64,
        teacher_calls=0,auxiliary_in_inference=False,student_mtp=False,formal_train_ready=False,
        general_intelligence='NOT_ESTABLISHED')


def read_values(spec):
    directory=ROOT/spec['directory'];verify(directory,spec['manifest'])
    return list(course.training.data.stream_rows(directory,spec['manifest']))


def generate(model,cfg,tok,rows,directory,lane):
    import torch
    writer=ShardWriter(directory,lane);events=[];emit=previous.old_eval.reference.generation.emit_function(model,cfg,tok)
    model.eval();model.freeze_quant()
    try:
        with torch.no_grad():
            for i,row in enumerate(rows):
                if lane=='evidence_test':values=method.collect(row,emit)
                elif lane=='role_retention':values=previous.method.collect(row,emit)
                elif lane=='fiction_retention':values=previous.old_eval.reference.method.collect(row,emit)
                else:values=previous.method.collect(row,emit)
                for value in values:writer.append(value);events.append(value)
                if (i+1)%128==0:print('[EVIDENCE_PREFERENCE_EVAL_PROGRESS] '+json.dumps(dict(lane=lane,conversations=i+1,total=len(rows))),flush=True)
    finally:model.clear_quant();model.train()
    manifest=writer.close(lineage=info());verify(directory,manifest)
    counts=(method.counts(events) if lane=='evidence_test' else previous.strata.counts(events) if lane=='fiction_retention'
        else previous.method.counts(events))
    return dict(directory=str(directory.relative_to(ROOT)),manifest=manifest,counts=counts)


def parent_replay(metrics):
    old=course.producer.required(course.PARENT_REPORT);results={}
    for current,prior in (('role_retention','role_retention'),('source_posthoc_dev','source_posthoc_dev')):
        a,b=read_values(metrics[current]),read_values(old['metrics'][prior])
        def indexed(values):return {(x['root'],x['turn'],x['history']):x for x in values}
        left,right=indexed(a),indexed(b)
        if len(left)!=len(a) or set(left)!=set(right):raise ValueError('same complete old parent cases required')
        mismatch=sum(any(left[k][f]!=right[k][f] for f in ('answer','gold','messages')) for k in left)
        if mismatch:raise ValueError('old parent exact-prefix replay differs: '+current)
        results[current]=dict(events=len(a),mismatch=0)
    return results


def run(a):
    import torch
    from tinylm.infer.generate import _strip
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from scripts.p106b_education_followup import answers
    r,rows,_,_=course.read_course()
    reports={arm:course.producer.required(course.EVIDENCE/arm/'report.json') for arm in course.ARMS}
    for arm,p in reports.items():
        if p['status']!='EVIDENCE_PREFERENCE_TRAINED_TEST_PENDING' or p['updates']!=64 or p['code_sha256']!=training.info()['code_sha256']:
            raise ValueError('same-code complete64 preference arms required')
        if course.training.data.digest(ROOT/p['checkpoint'])!=p['checkpoint_sha256']:raise ValueError('trained model changed')
    if EVIDENCE.exists() or LOCAL.exists():raise GateNegative('old evidence-preference outputs preserved')
    test=rows['test_evidence']
    if len(test)!=1024 or len({x['meta']['neutral_root'] for x in test})!=128:raise ValueError('all1024 new paired query cells required')
    idle_before_gpu();EVIDENCE.mkdir(parents=True,exist_ok=False);started=time.perf_counter();endpoints={}
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    with wall_limit(a.max_wall_sec):
        for arm in ('parent',*course.ARMS):
            torch,model,cfg,tok,_,_=training.load_parent();cp=course.PARENT;identity=course.PARENT_SHA
            if arm!='parent':
                p=reports[arm];cp=ROOT/p['checkpoint'];identity=p['checkpoint_sha256'];saved=torch.load(cp,map_location='cpu',weights_only=True)
                if saved['evidence_preference']!=dict(tag=course.TAG,arm=arm,updates=64):raise ValueError('fixed final64 lineage required')
                model.load_state_dict(_strip(saved['model']),strict=True);del saved
            before=course.training.state_fingerprint(model);model=model.cuda();directory=LOCAL/arm
            metrics=dict(evidence_test=generate(model,cfg,tok,test,directory,'evidence_test'),
                role_retention=generate(model,cfg,tok,rows['test_role_style0']+rows['test_role_style2'],directory,'role_retention'),
                source_posthoc_dev=generate(model,cfg,tok,rows['test_source'],directory,'source_posthoc_dev'),
                fiction_retention=generate(model,cfg,tok,rows['retention_fiction'],directory,'fiction_retention'),
                code_development=previous.old_eval.reference.legacy.generate(model,cfg,tok,rows['dev_code'],directory,'old_code640'),
                native32crop=course.training.native_ce(model,course.prior.NATIVE),
                legacy8=answers(PrecisionForward(model,'fp32_math'),cfg,tok,directory,'legacy8'))
            replay=parent_replay(metrics) if arm=='parent' else None
            if course.training.state_fingerprint(model)!=before:raise ValueError('evaluation changed body')
            endpoint=dict(checkpoint=str(cp.relative_to(ROOT)),checkpoint_sha256=identity,core_before_after_sha256=before,
                metrics=metrics,old_parent_exact_replay=replay)
            endpoints[arm]=endpoint;course.training.write(EVIDENCE/(arm+'_report.json'),dict(info(),arm=arm,**endpoint))
            print('[EVIDENCE_PREFERENCE_EVAL_ENDPOINT] '+json.dumps(dict(arm=arm,counts=metrics['evidence_test']['counts']['base']['ACTUAL_MODEL/all'],parent_replay=replay)),flush=True)
            del model;gc.collect();torch.cuda.empty_cache()
    course.training.write(EVIDENCE/'report.json',dict(info(),status='EVIDENCE_PREFERENCE_ACTUAL_EVALUATED',endpoints=endpoints,
        corpus_sha256=course.training.data.digest(course.CORPUS/'report.json'),whole_sec=time.perf_counter()-started));return 0


def readback():
    r=course.producer.required(EVIDENCE/'report.json');target=EVIDENCE/'paired_readback.json'
    if target.exists():raise GateNegative('old evidence-preference raw recount preserved')
    if r['code_sha256']!=info()['code_sha256']:raise ValueError('evaluation CODE changed')
    values={};counts={}
    for arm,p in r['endpoints'].items():
        values[arm]={};counts[arm]={}
        for lane,spec in p['metrics'].items():
            if lane not in ('evidence_test','role_retention','source_posthoc_dev','fiction_retention','code_development'):continue
            actual=read_values(spec);values[arm][lane]=actual
            if lane=='code_development':continue
            count=method.counts(actual) if lane=='evidence_test' else previous.strata.counts(actual) if lane=='fiction_retention' else previous.method.counts(actual)
            if count!=spec['counts']:raise ValueError('complete raw recount differs '+arm+'/'+lane)
            counts[arm][lane]=count
    pairs={}
    for a,b in itertools.combinations(r['endpoints'],2):
        one={};left,right=values[a]['evidence_test'],values[b]['evidence_test']
        one['all']=method.paired(left,right,neutral=True)
        for intent in ('ANSWER','ASK_FOR_MISSING_FACT'):
            one[intent]=method.paired([x for x in left if x['expected_response_intent']==intent],
                [x for x in right if x['expected_response_intent']==intent],neutral=True)
        one['role_retention']=method.paired(values[a]['role_retention'],values[b]['role_retention'],neutral=True)
        one['source_posthoc_descriptive_only']=method.paired(values[a]['source_posthoc_dev'],values[b]['source_posthoc_dev'])
        pairs[a+'__'+b]=one
    result=dict(info(),status='EVIDENCE_PREFERENCE_RAW_RECOUNTED',counts=counts,pairs=pairs,
        evaluation_report_sha256=course.training.data.digest(EVIDENCE/'report.json'),
        scope='scalar/given facts, recovery, free clarification proxy and retention separate; no global semantic classifier or world-truth claim')
    course.training.write(target,result);print('[EVIDENCE_PREFERENCE_PAIRED] '+json.dumps({k:v['ANSWER'] for k,v in pairs.items()}),flush=True);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('evaluate','readback'),required=True);p.add_argument('--max-wall-sec',type=int,default=3600)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=7200:p.error('bounded60..7200')
    if a.check_only:print('[EVIDENCE_PREFERENCE_EVAL_CHECK] '+json.dumps(info()));return 0
    try:
        course.producer.original.prior.producer.legacy.source.deadline()
        if a.mode=='evaluate':
            remaining=(course.producer.original.prior.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds()
            if remaining<a.max_wall_sec+2700:raise GateNegative('evaluation plus45minute closure margin')
            return run(a)
        return readback()
    except GateNegative as exc:print('[EVIDENCE_PREFERENCE_EVAL_HOLD] '+str(exc));return 8
    except KeyboardInterrupt:print('[EVIDENCE_PREFERENCE_EVAL_INTERRUPTED] preserve partial evidence');return 130
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[EVIDENCE_PREFERENCE_EVAL_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
