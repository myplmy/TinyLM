#!/usr/bin/env python3
"""Three immutable endpoints: fictional exact tasks and untouched public128."""
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
from scripts import diag_p106b_relation_train as training
from scripts import p106b_relation_evaluation as method
from scripts import diag_p106b_dualqa_eval as generation
from scripts import diag_p106b_grounded_span as legacy
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
course=training.course
EVIDENCE=course.EVIDENCE/'evaluate'
LOCAL=ROOT/'test_result/evidence/local'/course.TAG/'evaluate'
CODE=('scripts/p106b_relation_evaluation.py','scripts/test_p106b_relation_evaluation.py','scripts/diag_p106b_relation_evaluate.py')


def info():
    return dict(schema='P106B_RELATION_ACTUAL_EVALUATION_V1',tag=course.TAG,
        code_sha256={p:course.training.data.digest(ROOT/p) for p in CODE},
        endpoints=['parent',*training.ARMS],checkpoint_policy='final4epoch primary, no TEST selection',
        precision='FP32_MATH',temperature=0.,top_k=1,max_new=64,auxiliary_used_in_generation=False,
        fictional_roots=256,fictional_language_children=512,actual_answers_per_endpoint=3072,
        supplied_error_last_answers_per_endpoint=512,gold_second_answers_per_endpoint=1536,
        fresh_public128_truth='ORIGINAL_PUBLIC_UNVERIFIED',teacher_calls=0,full_smoke='NOT_RUN')


def fiction(model,cfg,tok,rows,directory):
    import torch
    writer=ShardWriter(directory,'fiction_actual_supplied_and_gold');events=[];emit=generation.emit_function(model,cfg,tok)
    model.eval();model.freeze_quant()
    try:
        with torch.no_grad():
            for view in range(4):
                selected=rows['test'+str(view)]
                if len(selected)!=512 or Counter(x['meta']['language'] for x in selected)!=dict(ko=256,en=256):raise ValueError('512 balanced fiction rows per view')
                for row in selected:
                    for event in method.collect(row,emit):writer.append(event);events.append(event)
                print('[RELATION_EVAL_VIEW] '+json.dumps(dict(view=view,rows=len(selected),events=len(events))),flush=True)
    finally:model.clear_quant();model.train()
    counts=method.summarize(events);manifest=writer.close(lineage=info());verify(directory,manifest)
    coverage=Counter(e['history'] for e in events)
    if dict(coverage)!=dict(ACTUAL_MODEL=3072,GOLD_REFERENCE=1536,PROVIDED_WRONG_HISTORY=512):raise ValueError('complete actual/supplied/gold separation')
    return dict(counts=counts,manifest=manifest,directory=str(directory.relative_to(ROOT)),coverage=dict(coverage),
        scope='producer-known fictional values, not world knowledge or semantic judgment of arbitrary answers')


def fact_teacher_forced(model,selector,tok,rows):
    import torch
    totals=Counter();pad=tok.token_to_id('<|pad|>')
    if pad is None:pad=tok.token_to_id('<pad>')
    if pad is None:raise ValueError('pad missing')
    model.eval();model.freeze_quant()
    try:
        with torch.no_grad():
            for start in range(0,len(rows),8):
                pairs=[training.factory.encode(r,tok) for r in rows[start:start+8]]
                x,y,seg=course.prior.padded([p[0] for p in pairs],pad)
                labels=[p[1] for p in pairs]+[None]*(8-len(pairs))
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    hidden=model(x,return_hidden=True);value,n,q,c=training.fact.auxiliary_sum(selector,hidden,y,seg,labels)
                totals.update(row_loss_sum=float(value),rows=n,queries=q,correct=c)
    finally:model.clear_quant();model.train()
    return dict(totals,row_mean_ce=totals['row_loss_sum']/totals['rows'],
        scope='teacher-forced fact-candidate diagnostic only, never a generation oracle')


def run(a):
    import torch
    from tinylm.infer.generate import _strip
    from scripts.p106b_education_followup import answers
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    r,rows,_=course.read_course();reports={arm:legacy.required(course.EVIDENCE/arm/'report.json') for arm in training.ARMS}
    for arm,p in reports.items():
        if p['code_sha256']!=training.info()['code_sha256'] or p['status']!='RELATION_TRAINED_TEST_PENDING' or p['updates']!=688:raise ValueError('same-code completed688 required')
        if course.training.data.digest(ROOT/p['checkpoint'])!=p['checkpoint_sha256']:raise ValueError('final CPT changed')
    if EVIDENCE.exists() or LOCAL.exists():raise GateNegative('old evaluation namespace preserved')
    idle_before_gpu();EVIDENCE.mkdir(parents=True,exist_ok=False);began=time.perf_counter();endpoints={}
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    with wall_limit(a.max_wall_sec):
        for arm in ('parent',*training.ARMS):
            torch,model,cfg,tok,initial=training.load_parent();cp=course.PARENT;identity=course.PARENT_SHA;head_state=None
            if arm!='parent':
                cp=ROOT/reports[arm]['checkpoint'];identity=reports[arm]['checkpoint_sha256'];saved=torch.load(cp,map_location='cpu',weights_only=True)
                if saved['relation_curriculum']!=dict(tag=course.TAG,arm=arm,epoch=4):raise ValueError('final4epoch identity')
                model.load_state_dict(_strip(saved['model']),strict=True);head_state=saved['training_only_fact_auxiliary'];del saved
            initial=course.training.state_fingerprint(model);model=model.cuda();directory=LOCAL/arm
            values=dict(fiction=fiction(model,cfg,tok,rows,directory),
                fresh_public128=legacy.generate(model,cfg,tok,rows['fresh_public_test'],directory,'fresh_public128'),
                known_code_dev640=legacy.generate(model,cfg,tok,rows['known_code_dev'],directory,'known_code_dev640'),
                native32crop=course.training.native_ce(model,course.prior.NATIVE),
                legacy8=answers(PrecisionForward(model,'fp32_math'),cfg,tok,directory,'legacy8'))
            if head_state is not None:
                selector=training.fact.new_head(cfg.dim,'cuda');selector.load_state_dict(head_state,strict=True)
                values['fact_teacher_forced']=fact_teacher_forced(model,selector,tok,sum((rows['test'+str(v)] for v in range(4)),[]));del selector
            else:values['fact_teacher_forced']=dict(status='NOT_APPLICABLE',reason='parent has no relation candidate head')
            if course.training.state_fingerprint(model)!=initial:raise ValueError('evaluation changed body')
            endpoints[arm]=dict(checkpoint=str(cp.relative_to(ROOT)),checkpoint_sha256=identity,core_before_after_sha256=initial,metrics=values)
            course.training.write(EVIDENCE/(arm+'_report.json'),dict(info(),arm=arm,**endpoints[arm]))
            print('[RELATION_EVAL_ENDPOINT] '+json.dumps(dict(arm=arm,fiction=values['fiction']['counts'],native=values['native32crop'])),flush=True)
            del model;gc.collect();torch.cuda.empty_cache()
    course.training.write(EVIDENCE/'report.json',dict(info(),status='RELATION_ALL_ENDPOINTS_EVALUATED',endpoints=endpoints,
        whole_sec=time.perf_counter()-began,training_report_sha256={a:course.training.data.digest(course.EVIDENCE/a/'report.json') for a in training.ARMS},
        corpus_sha256=course.training.data.digest(course.CORPUS/'report.json')))
    return 0


def readback():
    report=legacy.required(EVIDENCE/'report.json')
    if report['code_sha256']!=info()['code_sha256']:raise ValueError('evaluation CODE changed')
    all_events={}
    for arm,p in report['endpoints'].items():
        if course.training.data.digest(ROOT/p['checkpoint'])!=p['checkpoint_sha256']:raise ValueError('CPT changed')
        f=p['metrics']['fiction'];directory=ROOT/f['directory'];verify(directory,f['manifest'])
        events=list(course.training.data.stream_rows(directory,f['manifest']))
        if method.summarize(events)!=f['counts']:raise ValueError('raw coverage/counter mismatch')
        all_events[arm]=events
        for key in ('fresh_public128','known_code_dev640'):
            value=p['metrics'][key];verify(ROOT/value['directory'],value['manifest'])
    pairs={}
    for left,right in (('parent','fact0'),('parent','fact1'),('fact0','fact1')):
        pairs[left+'__'+right]={m:method.paired(all_events[left],all_events[right],m) for m in ('literal','lexical_f1','exact_other_field')}
    result=dict(info(),status='RELATION_RAW_RECOUNTED',pairs=pairs,
        evaluation_report_sha256=course.training.data.digest(EVIDENCE/'report.json'),scope='no post-TEST model selection or automatic training exclusion')
    destination=EVIDENCE/'paired_readback.json'
    if destination.exists():raise GateNegative('old readback preserved')
    course.training.write(destination,result);print('[RELATION_PAIRED] '+json.dumps(pairs),flush=True);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('evaluate','readback'),required=True)
    p.add_argument('--max-wall-sec',type=int,default=10800);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=14400:p.error('bounded60..14400')
    if a.check_only:print('[RELATION_EVAL_CHECK_ONLY] '+json.dumps(info()));return 0
    try:
        course.prior.producer.legacy.source.deadline()
        a.max_wall_sec=min(a.max_wall_sec,int((course.prior.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds())-2700)
        if a.max_wall_sec<60:raise GateNegative('45minute closure margin required')
        return run(a) if a.mode=='evaluate' else readback()
    except (GateNegative,FileNotFoundError) as exc:print('[RELATION_EVAL_HOLD] '+str(exc));return 8
    except KeyboardInterrupt:print('[RELATION_EVAL_INTERRUPTED] preserve raw partial answers');return 130
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[RELATION_EVAL_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
