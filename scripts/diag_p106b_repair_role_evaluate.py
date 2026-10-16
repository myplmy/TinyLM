#!/usr/bin/env python3
"""Five immutable endpoints: fresh public QA, code-role generalization, retention."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from datetime import datetime,timezone
import gc
import itertools
import json
import time
from scripts import diag_p106b_repair_role_train as training
from scripts import p106b_repair_role_evaluation as method
from scripts import diag_p106b_original_qa3_evaluate_v2 as old_eval
from scripts import p106b_relation_strata as strata
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
course=training.course
EVIDENCE=course.EVIDENCE/'evaluate'
LOCAL=ROOT/'test_result/evidence/local'/course.TAG/'evaluate'
CODE=(*training.CODE,'scripts/p106b_repair_role_evaluation.py','scripts/test_p106b_repair_role_evaluation.py',
    'scripts/diag_p106b_repair_role_evaluate.py')


def info():
    return dict(schema='P106B_REPAIR_ROLE_ACTUAL_EVALUATION_V1',tag=course.TAG,
        code_sha256={p:course.training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        endpoints=['parent',*course.ARMS],checkpoint_policy='fixed final4 only, no test choice',
        source_eval='new64 original general3QA, not span-filtered, ORIGINAL_PUBLIC_UNVERIFIED',
        source_actual_answers=192,source_gold_history_answers=128,
        role_eval='128 neutral graphs,2 language children,styles0/2; style2 unseen in this factory training only',
        role_conversations=512,role_actual_answers=1536,role_gold_history_answers=1024,
        precision='FP32_MATH',temperature=0.,top_k=1,max_new=64,teacher_calls=0,student_mtp=False,
        auxiliary_in_inference=False,formal_train_ready=False,general_intelligence='NOT_ESTABLISHED')


def generate(model,cfg,tok,rows,directory,lane,fiction=False):
    import torch
    writer=ShardWriter(directory,lane);events=[];emit=old_eval.reference.generation.emit_function(model,cfg,tok)
    model.eval();model.freeze_quant()
    try:
        with torch.no_grad():
            for i,row in enumerate(rows):
                values=old_eval.reference.method.collect(row,emit) if fiction else method.collect(row,emit)
                for value in values:writer.append(value);events.append(value)
                if (i+1)%128==0:print('[REPAIR_ROLE_EVAL_PROGRESS] '+json.dumps(dict(lane=lane,conversations=i+1,total=len(rows))),flush=True)
    finally:model.clear_quant();model.train()
    manifest=writer.close(lineage=info());verify(directory,manifest)
    counts=strata.counts(events) if fiction else method.counts(events)
    if not fiction and Counter(x['history'] for x in events)!=dict(ACTUAL_MODEL=3*len(rows),GOLD_REFERENCE=2*len(rows)):
        raise ValueError('complete actual three-turn and separate gold histories required')
    return dict(directory=str(directory.relative_to(ROOT)),manifest=manifest,counts=counts)


def run(a):
    import torch
    from tinylm.infer.generate import _strip
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from scripts.p106b_education_followup import answers
    r,rows,_=course.read_course();reports={arm:course.producer.required(course.EVIDENCE/arm/'report.json') for arm in course.ARMS}
    for arm,p in reports.items():
        if p['status']!='REPAIR_ROLE_TRAINED_TEST_PENDING' or p['updates']!=216 or p['code_sha256']!=training.info()['code_sha256']:
            raise ValueError('complete same-code216 arms required')
        if course.training.data.digest(ROOT/p['checkpoint'])!=p['checkpoint_sha256']:raise ValueError('trained checkpoint changed')
    if EVIDENCE.exists() or LOCAL.exists():raise GateNegative('old five-endpoint outputs preserved')
    if len(rows['test_source'])!=64 or Counter(x['meta']['language'] for x in rows['test_source'])!=dict(ko=32,en=32):raise ValueError('new64 source cohort required')
    role=rows['test_role_style0']+rows['test_role_style2']
    if len(role)!=512 or len({x['meta']['neutral_root'] for x in role})!=128:raise ValueError('all128 neutral/language/style children required')
    idle_before_gpu();EVIDENCE.mkdir(parents=True,exist_ok=False);started=time.perf_counter();endpoints={}
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    with wall_limit(a.max_wall_sec):
        for arm in ('parent',*course.ARMS):
            torch,model,cfg,tok,_,_=training.load_parent();cp=course.PARENT;identity=course.PARENT_SHA
            if arm!='parent':
                p=reports[arm];cp=ROOT/p['checkpoint'];identity=p['checkpoint_sha256'];saved=torch.load(cp,map_location='cpu',weights_only=True)
                if saved['repair_role_curriculum']!=dict(tag=course.TAG,arm=arm,epoch=4):raise ValueError('fixed final4 lineage required')
                model.load_state_dict(_strip(saved['model']),strict=True);del saved
            before=course.training.state_fingerprint(model);model=model.cuda();directory=LOCAL/arm
            metrics=dict(fresh_source=generate(model,cfg,tok,rows['test_source'],directory,'fresh_source'),
                role_bridge=generate(model,cfg,tok,role,directory,'role_bridge'),
                development_source64=generate(model,cfg,tok,rows['development_source64'],directory,'old_development_source64'),
                fiction_retention=generate(model,cfg,tok,rows['retention_fiction'],directory,'fiction_retention',fiction=True),
                code_development=old_eval.reference.legacy.generate(model,cfg,tok,rows['dev_code'],directory,'old_code640'),
                native32crop=course.training.native_ce(model,course.prior.NATIVE),
                legacy8=answers(PrecisionForward(model,'fp32_math'),cfg,tok,directory,'legacy8'))
            if course.training.state_fingerprint(model)!=before:raise ValueError('evaluation changed body')
            endpoint=dict(checkpoint=str(cp.relative_to(ROOT)),checkpoint_sha256=identity,core_before_after_sha256=before,metrics=metrics)
            endpoints[arm]=endpoint;course.training.write(EVIDENCE/(arm+'_report.json'),dict(info(),arm=arm,**endpoint))
            print('[REPAIR_ROLE_EVAL_ENDPOINT] '+json.dumps(dict(arm=arm,source=metrics['fresh_source']['counts']['base']['ACTUAL_MODEL/all'],
                role=metrics['role_bridge']['counts']['base']['ACTUAL_MODEL/all'],native=metrics['native32crop'],legacy8=metrics['legacy8'])),flush=True)
            del model;gc.collect();torch.cuda.empty_cache()
    course.training.write(EVIDENCE/'report.json',dict(info(),status='REPAIR_ROLE_ACTUAL_EVALUATED',endpoints=endpoints,
        whole_sec=time.perf_counter()-started,corpus_sha256=course.training.data.digest(course.CORPUS/'report.json')));return 0


def readback():
    report=course.producer.required(EVIDENCE/'report.json');target=EVIDENCE/'paired_readback.json'
    if target.exists():raise GateNegative('old repair-role raw recount preserved')
    if report['code_sha256']!=info()['code_sha256']:raise ValueError('evaluation CODE changed')
    lanes={};counts={}
    for arm,p in report['endpoints'].items():
        lanes[arm]={};counts[arm]={}
        for name,spec in p['metrics'].items():
            if name not in ('fresh_source','role_bridge','development_source64','fiction_retention','code_development'):continue
            verify(ROOT/spec['directory'],spec['manifest']);values=list(course.training.data.stream_rows(ROOT/spec['directory'],spec['manifest']))
            lanes[arm][name]=values
            if name=='code_development':continue
            actual=strata.counts(values) if name=='fiction_retention' else method.counts(values)
            if actual!=spec['counts']:raise ValueError('complete raw recount differs: '+arm+'/'+name)
            counts[arm][name]=actual
    pairs={}
    for a,b in itertools.combinations(report['endpoints'],2):
        key=a+'__'+b;pairs[key]={}
        for lane in ('fresh_source','development_source64'):
            pairs[key][lane]=method.paired(lanes[a][lane],lanes[b][lane])
        for style in (0,2):
            left=[x for x in lanes[a]['role_bridge'] if x['question_style']==style]
            right=[x for x in lanes[b]['role_bridge'] if x['question_style']==style]
            pairs[key]['role_style'+str(style)]=method.paired(left,right,neutral=True)
    course.training.write(target,dict(info(),status='REPAIR_ROLE_RAW_RECOUNTED',counts=counts,pairs=pairs,
        evaluation_report_sha256=course.training.data.digest(EVIDENCE/'report.json'),
        scope='same-source and neutral-graph paired recipes; targets/text/amount differ, no pure mechanism or world-truth claim'))
    print('[REPAIR_ROLE_PAIRED] '+json.dumps({k:v['fresh_source'] for k,v in pairs.items()}),flush=True);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('evaluate','readback'),required=True);p.add_argument('--max-wall-sec',type=int,default=3600)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=7200:p.error('bounded60..7200')
    if a.check_only:print('[REPAIR_ROLE_EVAL_CHECK_ONLY] '+json.dumps(info()));return 0
    try:
        course.producer.original.prior.producer.legacy.source.deadline()
        if a.mode=='evaluate':
            remaining=(course.producer.original.prior.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds()
            if remaining<a.max_wall_sec+2700:raise GateNegative('requested evaluation plus45minute closure margin')
            return run(a)
        return readback()
    except GateNegative as exc:print('[REPAIR_ROLE_EVAL_HOLD] '+str(exc));return 8
    except KeyboardInterrupt:print('[REPAIR_ROLE_EVAL_INTERRUPTED] partial outputs preserved');return 130
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[REPAIR_ROLE_EVAL_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
