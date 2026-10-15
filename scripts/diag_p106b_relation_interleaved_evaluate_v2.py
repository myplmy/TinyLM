#!/usr/bin/env python3
"""New roots: saved blocked fact1 versus source-matched interleaved fact1."""
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
from scripts import diag_p106b_relation_interleaved_train_v2 as training
from scripts import diag_p106b_relation_evaluate as reference
from scripts import p106b_relation_strata as strata
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
course=training.course
EVIDENCE=course.EVIDENCE/'evaluate'
LOCAL=ROOT/'test_result/evidence/local'/course.TAG/'evaluate'
CODE=('scripts/diag_p106b_relation_interleaved_evaluate_v2.py','scripts/test_p106b_relation_interleaved_evaluate_v2.py')


def info():
    return dict(schema='P106B_RELATION_INTERLEAVED_ACTUAL_V2',tag=course.TAG,
        code_sha256={p:course.training.data.digest(ROOT/p) for p in CODE},
        endpoints=['blocked_fact1','interleaved_fact1'],precision='FP32_MATH',temperature=0.,top_k=1,max_new=64,
        fictional_neutral_roots=256,actual_self_history_answers=3072,supplied_error_answers=512,gold_second_answers=1536,
        natural_source_cases=32,auxiliary_used_in_generation=False,checkpoint_policy='fixed final4rootpasses',
        old_TEST_used_as_development=True,future_reserved_role_test_evaluated=False,world_truth='NOT_RUN')


def collect_fiction(model,cfg,tok,rows,directory):
    import torch
    events=[];writer=ShardWriter(directory,'new_fiction_actual_and_reference');emit=reference.generation.emit_function(model,cfg,tok)
    model.eval();model.freeze_quant()
    try:
        with torch.no_grad():
            for view in range(4):
                chosen=rows['test'+str(view)]
                if len(chosen)!=512 or Counter(r['meta']['language'] for r in chosen)!=dict(ko=256,en=256):raise ValueError('all balanced512 rows per view required')
                if any(not 8192<=r['meta']['producer_graph']['index']<=8447 for r in chosen):raise ValueError('old developmental TEST cannot be relabeled new')
                for row in chosen:
                    for event in reference.method.collect(row,emit):writer.append(event);events.append(event)
                print('[INTERLEAVED_EVAL_VIEW] '+json.dumps(dict(view=view,events=len(events))),flush=True)
    finally:model.clear_quant();model.train()
    coverage=dict(Counter(e['history'] for e in events))
    if coverage!=dict(ACTUAL_MODEL=3072,PROVIDED_WRONG_HISTORY=512,GOLD_REFERENCE=1536):raise ValueError('history coverage mismatch')
    manifest=writer.close(lineage=info());verify(directory,manifest)
    return dict(directory=str(directory.relative_to(ROOT)),manifest=manifest,counts=strata.counts(events),coverage=coverage)


def endpoints():
    blocked=reference.legacy.required(course.base.EVIDENCE/'fact1/report.json');new=reference.legacy.required(course.EVIDENCE/'fact1/report.json')
    if blocked['checkpoint_sha256']!='219EAA7468173F0F6FEE26EDFE7EAD1190A3A4B1F768FF8B03260E9B11D84506':raise ValueError('preregistered saved blocked endpoint')
    if new['code_sha256']!=training.info()['code_sha256']:raise ValueError('new trainer CODE changed')
    for p in (blocked,new):
        if p['status']!='RELATION_TRAINED_TEST_PENDING' or p['updates']!=688 or p['initial_core_sha256']!=blocked['initial_core_sha256']:raise ValueError('complete688 same parent required')
        for key in ('sft_x_tokens','assistant_targets','native_x_tokens','fact_rows','fact_queries','binary_rows','binary_position_events'):
            if p[key]!=blocked[key]:raise ValueError('global information exposure differs: '+key)
        if course.training.data.digest(ROOT/p['checkpoint'])!=p['checkpoint_sha256']:raise ValueError('endpoint weights changed')
    return [('blocked_fact1',blocked,course.base.TAG),('interleaved_fact1',new,course.TAG)]


def run(a):
    import torch
    from tinylm.infer.generate import _strip
    from scripts.p106b_education_followup import answers
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    r,rows,_=course.read_course();models=endpoints()
    if EVIDENCE.exists() or LOCAL.exists():raise GateNegative('old new-root evaluation preserved')
    if len(rows['fresh_public_test'])!=32 or Counter(x['meta']['language'] for x in rows['fresh_public_test'])!=dict(ko=16,en=16):raise ValueError('new32 natural source required')
    idle_before_gpu();EVIDENCE.mkdir(parents=True,exist_ok=False);began=time.perf_counter();results={}
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    with wall_limit(a.max_wall_sec):
        for arm,p,tag in models:
            torch,model,cfg,tok,_=training.load_parent();saved=torch.load(ROOT/p['checkpoint'],map_location='cpu',weights_only=True)
            if saved['relation_curriculum']!=dict(tag=tag,arm='fact1',epoch=4):raise ValueError('exact final4 lineage')
            model.load_state_dict(_strip(saved['model']),strict=True);del saved;initial=course.training.state_fingerprint(model);model=model.cuda();directory=LOCAL/arm
            values=dict(fiction=collect_fiction(model,cfg,tok,rows,directory),
                natural32=reference.legacy.generate(model,cfg,tok,rows['fresh_public_test'],directory,'new_natural32'),
                known_code_dev640=reference.legacy.generate(model,cfg,tok,rows['known_code_dev'],directory,'known_code_dev640'),
                native32crop=course.training.native_ce(model,course.prior.NATIVE),legacy8=answers(PrecisionForward(model,'fp32_math'),cfg,tok,directory,'legacy8'))
            if course.training.state_fingerprint(model)!=initial:raise ValueError('evaluation changed body parameters')
            results[arm]=dict(checkpoint=p['checkpoint'],checkpoint_sha256=p['checkpoint_sha256'],core_before_after_sha256=initial,metrics=values)
            course.training.write(EVIDENCE/(arm+'_report.json'),dict(info(),arm=arm,**results[arm]))
            print('[INTERLEAVED_ENDPOINT] '+json.dumps(dict(arm=arm,actual=values['fiction']['counts']['ACTUAL_MODEL/all'],provided=values['fiction']['counts']['PROVIDED_WRONG_HISTORY/all'],natural=values['natural32']['counts'])),flush=True)
            del model;gc.collect();torch.cuda.empty_cache()
    course.training.write(EVIDENCE/'report.json',dict(info(),status='INTERLEAVED_NEW_ROOTS_EVALUATED',endpoints=results,
        whole_sec=time.perf_counter()-began,corpus_report_sha256=course.training.data.digest(course.CORPUS/'report.json')))
    return 0


def readback():
    report=reference.legacy.required(EVIDENCE/'report.json');target=EVIDENCE/'paired_readback.json'
    if target.exists():raise GateNegative('old paired report preserved')
    if report['code_sha256']!=info()['code_sha256']:raise ValueError('evaluation CODE changed')
    events={};counts={};invariance={}
    for arm,p in report['endpoints'].items():
        f=p['metrics']['fiction'];directory=ROOT/f['directory'];verify(directory,f['manifest'])
        rows=list(course.training.data.stream_rows(directory,f['manifest']))
        if strata.counts(rows)!=f['counts']:raise ValueError('all raw counters differ')
        invariance[arm]=strata.first_invariance(rows)
        if invariance[arm]['root_language_groups']!=512 or invariance[arm]['first_output_disagreements']:raise ValueError('same-first-prefix output differs')
        events[arm]=rows;counts[arm]=f['counts']
        for key in ('natural32','known_code_dev640'):
            m=p['metrics'][key];verify(ROOT/m['directory'],m['manifest'])
    pairs=strata.pairs_by_lane(events['blocked_fact1'],events['interleaved_fact1'])
    course.training.write(target,dict(info(),status='INTERLEAVED_NEW_ROOTS_RAW_VERIFIED',counts=counts,pairs=pairs,first_prefix_invariance=invariance,
        evaluation_sha256=course.training.data.digest(EVIDENCE/'report.json'),scope='fixed new fictional roots, natural32 only descriptive; no TEST-selected checkpoint'))
    print('[INTERLEAVED_PAIRED] '+json.dumps(dict(actual=pairs['ACTUAL_MODEL/all']['literal'],provided=pairs['PROVIDED_WRONG_HISTORY/all']['literal'])),flush=True);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('evaluate','readback'),required=True);p.add_argument('--max-wall-sec',type=int,default=10800)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=14400:p.error('bounded60..14400')
    if a.check_only:print('[INTERLEAVED_EVAL_CHECK_ONLY] '+json.dumps(info()));return 0
    try:
        course.prior.producer.legacy.source.deadline();a.max_wall_sec=min(a.max_wall_sec,int((course.prior.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds())-2700)
        if a.max_wall_sec<60:raise GateNegative('45minute closure margin')
        return run(a) if a.mode=='evaluate' else readback()
    except (GateNegative,FileNotFoundError) as exc:print('[INTERLEAVED_EVAL_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[INTERLEAVED_EVAL_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
