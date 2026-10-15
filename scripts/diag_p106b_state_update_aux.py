#!/usr/bin/env python3
"""Fresh two-turn update/format study from a dev-selected student; bounded runtime."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
from contextlib import ExitStack,contextmanager
import copy
from datetime import datetime,timezone
import gc
import json
import math
import time
from unittest.mock import patch
from scripts import diag_p106b_binding_auxiliary as driver
from scripts import p106b_state_update_aux as method
from scripts.p106b_native_windows import NATIVE_TRAIN
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
TAG='p106b_state_update_aux_v1_s1337'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
LOCAL=ROOT/'test_result/evidence/local'/TAG
SMALL_CORPUS=driver.CORPUS
SMALL_EVIDENCE=driver.EVIDENCE
CHOICE=ROOT/'test_result/evidence/p106b_binding_scale_v1_s1337/choice.json'
CODE=(*driver.CODE,'scripts/p106b_state_update_aux.py','scripts/test_p106b_state_update_aux.py',
      'scripts/diag_p106b_state_update_aux.py','scripts/test_p106b_state_update_driver.py')
ORIGINAL_INFO=driver.info
ORIGINAL_LOAD=driver.base.training.load_runtime
ARMS={'aux0':(0.,False),'aux100':(1.,False)}


def parent_ref(check=False):
    chosen=driver.required_json(CHOICE,'small final-DEV candidate fixed before final test')
    if chosen['selection_uses_small_fresh_test'] or chosen['candidate'] not in ('aux03','aux100','auxdense100'):
        raise ValueError('development-only parent choice required')
    arm=chosen['candidate'];path=SMALL_EVIDENCE/arm/'report.json';report=driver.required_json(path,'completed selected small parent')
    if driver.base.training.data.digest(path)!=chosen['reference_files'][arm]['sha256'] or report['updates']!=176:
        raise ValueError('parent reference changed')
    if check and driver.base.training.data.digest(ROOT/report['checkpoint'])!=report['checkpoint_sha256']:
        raise ValueError('parent checkpoint changed')
    return dict(arm=arm,path=report['checkpoint'],sha256=report['checkpoint_sha256'],
        report=str(path.relative_to(ROOT)),report_sha256=driver.base.training.data.digest(path),
        choice_sha256=driver.base.training.data.digest(CHOICE),choice_uses_final_test=False,parent_phase_updates=176)


def info():
    value=ORIGINAL_INFO();parent=parent_ref()
    for field in ('dense_arm','all_arms_compute_same_suffix_logits'):value.pop(field,None)
    value.update(schema=method.VERSION,tag=TAG,arms={k:dict(weight=v[0],root_permuted=False) for k,v in ARMS.items()},
        parent_sha256=parent['sha256'],parent_reference=parent,initializer='selected student weights, optimizer reset',
        code_sha256={p:driver.base.training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        expected_updates=416,auxiliary_scope='exact code updated-entity equals final queried-entity bit at LAST assistant predictor',
        same_last_query_logits_all_arms=True,old_public_train_rows_reused=0,
        source_block='NO_ADDITIONAL_PUBLIC_TRAIN; sourceQA belongs to parent history only',
        train_truth='PRODUCER_CODE_FACT_CONTRACT_ONLY',public_eval_truth='PSEUDO_UNVERIFIED_DEVELOPMENT',
        scope='fresh fictional two-turn state/format diagnostic; not75M/300M/general intelligence')
    return value


def freeze():
    driver.base.deadline();parent=parent_ref(True)
    if CORPUS.parent.exists() or EVIDENCE.exists():raise GateNegative('old state namespace preserved')
    old,existing=driver.read_course();rows=method.build_rows(existing)
    from tokenizers import Tokenizer
    from tinylm.train.mtp_sft import encode_record
    import numpy as np
    tok=Tokenizer.from_file(str(driver.base.training.data.TOKENIZER));counts={};labels=[]
    for split,values in rows.items():
        contract=method.approved(values);totals=Counter()
        for row in values:
            rec=encode_record(row,tok);driver.validate_budget([rec],[row]);m=row['meta']
            m.update(actual_x_tokens=rec.x_tokens,assistant_targets=rec.targets)
            totals.update(rows=1,actual_x_tokens=rec.x_tokens,assistant_targets=rec.targets)
            if split=='train':
                bit=method.label(row,contract)
                if bit is not None:labels.append(dict(signature=method.source.sha(row['messages']),bit=bit,
                    root=m['semantic_root_id'],positions=[method.last_predictor(row,rec,tok)]))
        counts[split]=dict(totals,languages=dict(Counter(r['meta']['language'] for r in values)),
            kinds=dict(Counter(r['meta']['kind'] for r in values)))
    if {s:len(v) for s,v in rows.items()}!=dict(train=13312,dev=1600,test=1024,public_eval=16) or len(labels)!=8192:
        raise ValueError('planned state dataset count differs')
    roots={s:{r['meta']['semantic_root_id'] for r in rows[s]} for s in ('train','dev','test')}
    if any(roots[a]&roots[b] for a,b in (('train','dev'),('train','test'),('dev','test'))):raise ValueError('state root overlap')
    old_maps={method.fact_key(r) for v in existing.values() for r in v if r['meta']['kind'].startswith('binding_')}
    if any(method.fact_key(r) in old_maps for v in rows.values() for r in v if r['meta']['kind']!='public_qa'):
        raise ValueError('parent small-course abstract fact reused')
    native=np.memmap(ROOT/NATIVE_TRAIN,dtype=np.uint16,mode='r');updates=4*len(rows['train'])//128
    previous=json.loads((driver.base.CORPUS/'report.json').read_text());exclude=set(previous['native_train_offsets'])
    offsets=[p for p in method.source.native_offsets(len(native),updates*8+len(exclude)+512) if p not in exclude][:updates*8]
    if len(offsets)!=3328 or set(offsets)&exclude:raise ValueError('fresh native windows unavailable')
    CORPUS.mkdir(parents=True,exist_ok=False);manifests={}
    for split,values in rows.items():
        writer=ShardWriter(CORPUS,split)
        for row in values:writer.append(row)
        manifests[split]=writer.close(lineage=info());verify(CORPUS,manifests[split])
    writer=ShardWriter(CORPUS,'aux_labels')
    for row in labels:writer.append(row)
    label_manifest=writer.close(lineage=dict(schema=method.VERSION,scope='last assistant predictor, exact code state only'))
    verify(CORPUS,label_manifest)
    result=dict(info(),status='STATE_AUX_COURSE_FROZEN',parent=parent,counts=counts,manifests=manifests,
        labels_manifest=label_manifest,auxiliary_labels=len(labels),dev_contracts=method.approved(rows['dev']),
        epochs=4,expected_updates=updates,required_cost_arms=list(ARMS),expected_head_position_events=4*len(labels),
        native_access='INDEXED_TRAIN_ONLY',native_train_file=NATIVE_TRAIN,native_train_offsets=offsets,
        native_train_sha256=driver.base.training.data.digest(ROOT/NATIVE_TRAIN),native_parent_window_overlap=0,
        parent_small_course_fact_overlap=0,old_public_rows_extra_exposure=0,
        source_small_course_sha256=driver.base.training.data.digest(SMALL_CORPUS/'report.json'))
    driver.base.training.write(CORPUS/'report.json',result)
    driver.base.training.write(EVIDENCE/'corpus_report.json',{k:v for k,v in result.items() if k!='dev_contracts'})
    print('[STATE_AUX_CORPUS] '+json.dumps(dict(counts=counts,updates=updates,labels=len(labels),parent=parent)),flush=True);return 0


def read_course():
    r=driver.required_json(CORPUS/'report.json','frozen fresh state course')
    if r['status']!='STATE_AUX_COURSE_FROZEN' or r['code_sha256']!=info()['code_sha256']:
        raise ValueError('same-code state course required')
    if driver.base.training.data.digest(ROOT/r['native_train_file'])!=r['native_train_sha256']:raise ValueError('native train changed')
    for manifest in (*r['manifests'].values(),r['labels_manifest']):verify(CORPUS,manifest)
    r['labels']={v['signature']:{k:x for k,x in v.items() if k!='signature'}
        for v in driver.base.training.data.stream_rows(CORPUS,r['labels_manifest'])}
    return r,{s:list(driver.base.training.data.stream_rows(CORPUS,m)) for s,m in r['manifests'].items()}


def load_from_parent(arm):
    torch,model,cfg,tok,ignored=ORIGINAL_LOAD(arm)
    from tinylm.infer.generate import _strip
    parent=parent_ref(True);saved=torch.load(ROOT/parent['path'],map_location='cpu',weights_only=True)
    model.load_state_dict(_strip(saved['model']),strict=True);del saved
    model.clear_quant();model.train();initial=driver.base.training.state_fingerprint(model)
    return torch,model,cfg,tok,initial


def auxiliary_dev(model,head,tok,values,pad,approved=None):
    import torch
    from tinylm.train import mtp_sft as core
    rows=[r for r in values if r['meta']['kind'].startswith('state_update_')];totals=Counter();model.eval()
    if approved is None:raise ValueError('frozen trusted dev state metadata required')
    with torch.no_grad():
        for start in range(0,len(rows),8):
            selected=rows[start:start+8];records=[core.encode_record(r,tok) for r in selected]
            labels=[method.label(r,approved) for r in selected];windows=[[method.last_predictor(r,rec,tok)] for r,rec in zip(selected,records)]
            x,y,seg=core.pad_records(records,pad,'cuda',fixed_width=1024,batch_size=8)
            labels+=[None]*(8-len(labels));windows+=[None]*(8-len(windows))
            with torch.autocast('cuda',dtype=torch.bfloat16):
                hidden=model(x,return_hidden=True);loss,n,correct,events=method.final_auxiliary_sum(head,hidden,y,labels,windows)
            totals.update(loss_sum=float(loss),cases=n,correct=correct)
    model.train();return dict(totals,ce=totals['loss_sum']/totals['cases'],accuracy=totals['correct']/totals['cases'],
        scope='last-prefix true updated-target bit; not free generation')


@contextmanager
def runtime():
    with ExitStack() as stack:
        for name,value in dict(TAG=TAG,CORPUS=CORPUS,EVIDENCE=EVIDENCE,LOCAL=LOCAL,CODE=CODE,info=info,
                read_course=read_course,auxiliary_dev=auxiliary_dev).items():stack.enter_context(patch.object(driver,name,value))
        stack.enter_context(patch.object(driver.method,'ARMS',ARMS))
        stack.enter_context(patch.object(driver.method,'suffix_auxiliary_sum',method.final_auxiliary_sum))
        stack.enter_context(patch.object(driver.base.training,'load_runtime',load_from_parent))
        yield


def forecast(reports,remaining,completed=()):
    estimates={}
    for arm,r in reports.items():
        steady=sorted(r['step_seconds'][1:])
        if len(steady)!=7 or not all(math.isfinite(x) and x>0 for x in steady):raise ValueError('seven valid steady costs required')
        p95=steady[math.ceil(.95*len(steady))-1];estimates[arm]=dict(p95=p95,train_estimate_sec=p95*416+300)
    need=sum(v['train_estimate_sec'] for a,v in estimates.items() if a not in completed)+900+2700
    return dict(arms=estimates,remaining_sec=remaining,needed_sec=need,completed=list(completed),fits=need<remaining,
        evaluation_margin_sec=900,closure_margin_sec=2700,scope='forecast, not guaranteed completion')


def budget(record=False):
    reports={a:driver.required_json(EVIDENCE/('cost_'+a)/'report.json','both actual state cost8') for a in ARMS}
    if any(r['updates']!=8 or r['code_sha256']!=info()['code_sha256'] for r in reports.values()):
        raise ValueError('same-code actual state cost8 required')
    completed=[]
    for arm in ARMS:
        p=EVIDENCE/arm/'report.json'
        if p.exists():
            r=json.loads(p.read_text())
            if r['status']!='TRAINED_FRESH_TEST_PENDING' or r['updates']!=416:raise ValueError('partial state arm preserved')
            completed.append(arm)
    remaining=(driver.base.DEADLINE-datetime.now(timezone.utc)).total_seconds();value=dict(info(),status='BUDGET_MEASURED',**forecast(reports,remaining,completed))
    if record:driver.base.training.write(EVIDENCE/'budget_report.json',value)
    print('[STATE_AUX_BUDGET] '+json.dumps(value),flush=True)
    if not value['fits']:raise GateNegative('state pair cannot fit before17 including evaluation/closure')
    return 0


def state_summary(rows):
    totals=Counter();strata=defaultdict(Counter);roots=defaultdict(list)
    for row in rows:
        m=row['meta']
        if not m['kind'].startswith('state_update_'):continue
        ok=row['exact_code_contract'] is True;gold=row['gold'];rubric=m['rubric'];old=m['previous_gold_value']
        values=dict(cases=1,exact=int(ok),previous_value_copy_with_format=int(method.render_value(old,m['final_format'])==gold),
            always_latest_update_value=int(method.render_value(m['new_value'],m['final_format'])==gold),
            previous_literal_copy=int(method.source.exact(old,gold,rubric) is True),
            old_lookup_ignoring_update=int(method.render_value(m['initial_values'][m['final_requested_entity']],m['final_format'])==gold))
        totals.update(values);strata[(m['language'],m['property_kind'],m['target_updated'],m['final_format'])].update(values)
        roots[m['semantic_root_id']].append(ok)
    if totals['cases']!=512 or any(len(v)!=8 for v in roots.values()):raise ValueError('new512 balanced8-view roots required')
    totals.update(roots=len(roots),all8_exact_roots=sum(all(v) for v in roots.values()))
    return dict(counts=dict(totals),strata={str(k):dict(v) for k,v in strata.items()},scope='new code state512 only; strict final output contract')


def evaluate(args):
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from scripts.p106b_education_followup import answers
    from scripts.diag_p106b_context_quality import probe
    from tinylm.infer.generate import _strip
    r,rows=read_course();target=EVIDENCE/'fresh_test'
    if target.exists():raise GateNegative('old state test preserved')
    trained={a:driver.required_json(EVIDENCE/a/'report.json','both state students') for a in ARMS}
    if any(v['updates']!=416 or v['code_sha256']!=info()['code_sha256'] for v in trained.values()):raise ValueError('same-code two completed state arms required')
    idle_before_gpu();began=time.perf_counter();results={};public={};legacy={};rollouts={};states={}
    with wall_limit(args.max_wall_sec):
        for arm in ('parent',*ARMS):
            driver.base.deadline();torch,model,cfg,tok,initial=load_from_parent('parent_ntp')
            if arm!='parent':
                v=trained[arm]
                if driver.base.training.data.digest(ROOT/v['checkpoint'])!=v['checkpoint_sha256']:raise ValueError('state checkpoint changed')
                saved=torch.load(ROOT/v['checkpoint'],map_location='cpu',weights_only=True);model.load_state_dict(_strip(saved['model']),strict=True);del saved
            model=model.cuda();folder=LOCAL/'fresh_test'/arm
            results[arm]=driver.base.generate(model,cfg,tok,rows['test'],folder,'state_code')
            results[arm]['native']=driver.base.training.native_ce(model,driver.base.NATIVE)
            actual=list(driver.base.training.data.stream_rows(folder,results[arm]['raw_manifest']));states[arm]=state_summary(actual)
            public[arm]=driver.generate_public(model,cfg,tok,rows['public_eval'],folder)
            legacy[arm]=answers(PrecisionForward(model,'fp32_math'),cfg,tok,folder,'legacy8')
            groups={}
            for row in rows['test']:
                m=row['meta']
                if m['kind'].startswith('state_update_'):groups.setdefault((m['language'],m['property_kind'],m['target_updated'],m['final_format']),row)
            rollouts[arm]=probe(model,cfg,tok,list(groups.values()),folder,'actual_state_dialogues')
            print('[STATE_AUX_EVAL] '+json.dumps(dict(arm=arm,state=states[arm],native=results[arm]['native'],legacy8=legacy[arm])),flush=True)
            del model;gc.collect();torch.cuda.empty_cache()
    value=dict(info(),status='STATE_AUX_FRESH_TEST_COLLECTED',arms=results,state=states,public_qa=public,legacy8=legacy,
        actual_dialogues=rollouts,cases_per_arm=1024,new_state_cases_per_arm=512,new_basic_cases_per_arm=512,
        actual_dialogue_scope='subset16 of state512, not additional independent cases; real prior model answers',
        whole_sec=time.perf_counter()-began,head_used_for_generation=False,checkpoint_saved=False,model_training=False)
    driver.base.training.write(target/'report.json',value);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('freeze','cost','budget','train','evaluate'),required=True)
    p.add_argument('--arm',choices=tuple(ARMS),default='aux0');p.add_argument('--max-wall-sec',type=int,default=3600)
    group=p.add_mutually_exclusive_group(required=True);group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true')
    args=p.parse_args()
    if not 60<=args.max_wall_sec<=7200:p.error('bounded60..7200')
    try:
        if args.check_only:print('[CHECK_ONLY] '+json.dumps(info()));return 0
        if not args.execute:p.error('explicit execution required')
        driver.base.deadline();args.max_wall_sec=min(args.max_wall_sec,int((driver.base.DEADLINE-datetime.now(timezone.utc)).total_seconds())-2700)
        if args.max_wall_sec<60:raise GateNegative('closure margin before17 required')
        if args.mode=='freeze':return freeze()
        if args.mode=='budget':return budget(record=True)
        if args.mode=='evaluate':return evaluate(args)
        target=EVIDENCE/(('cost_' if args.mode=='cost' else '')+args.arm)
        if target.exists():raise GateNegative('previous requested state arm preserved before model load')
        if args.mode=='train':budget()
        with runtime():return driver.train(args,cost=args.mode=='cost')
    except GateNegative as exc:print('[STATE_AUX_HOLD] '+str(exc),flush=True);return 8
    except KeyboardInterrupt:print('[STATE_AUX_INTERRUPTED] preserve prior outputs',flush=True);return 130
    except Exception as exc:print('[STATE_AUX_ERROR] '+type(exc).__name__+': '+str(exc),flush=True);return 9


if __name__=='__main__':raise SystemExit(main())
