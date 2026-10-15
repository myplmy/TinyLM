#!/usr/bin/env python3
"""State-fixed decimal/carry contrast, isolated fresh outputs and deadline gates."""
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
from scripts import diag_p106b_state_update_aux as prior
from scripts import p106b_joint_decimal as method
from scripts.p106b_native_windows import NATIVE_TRAIN
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
driver=prior.driver
TAG='p106b_joint_decimal_v1_s1337'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
LOCAL=ROOT/'test_result/evidence/local'/TAG
CODE=(*prior.CODE,'scripts/p106b_joint_decimal.py','scripts/test_p106b_joint_decimal.py',
      'scripts/diag_p106b_joint_decimal.py','scripts/test_p106b_joint_decimal_driver.py')
ARMS={'digits0':(1.,False),'digits1':(1.,False)}
BETA=0.
TASK_COUNTS=Counter()
HEADS=[]


def info():
    value=prior.info();value.update(schema=method.VERSION,tag=TAG,
        code_sha256={p:driver.base.training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        arms={a:dict(global_multiplier=1.,fixed_state_multiplier=2.,decimal_multiplier=0. if a=='digits0' else 2.) for a in ARMS},
        expected_updates=672,auxiliary_parameters=26146,auxiliary_scope='last-prefix state2 + decimal32; state fixed, decimal contrast',
        raw_effective_auxiliary_rows_scope='generic known-row count; canonical task-active counts belong to joint_report.json',
        canonical_arm_report='joint_report.json',auxiliary_subtasks_per_math_row=3,
        scope='same fresh state21504/addition pair study, not general mathematics/75M/300M')
    return value


def freeze():
    driver.base.deadline();parent=prior.parent_ref(True)
    if CORPUS.parent.exists() or EVIDENCE.exists():raise GateNegative('old joint namespace preserved')
    previous,rows=prior.read_course();small,old=driver.read_course();excluded=method.exclude_parent_pairs(old)
    addition=method.addition_rows(excluded);rows=copy.deepcopy(rows)
    for split in ('train','dev','test'):rows[split]+=addition[split]
    from tokenizers import Tokenizer
    from tinylm.train.mtp_sft import encode_record
    import numpy as np
    tok=Tokenizer.from_file(str(driver.base.training.data.TOKENIZER));counts={};labels=[]
    for split,values in rows.items():
        legal=method.approved(values);totals=Counter()
        for row in values:
            rec=encode_record(row,tok);driver.validate_budget([rec],[row]);m=row['meta']
            m.update(joint_course_version=method.VERSION,actual_x_tokens=rec.x_tokens,assistant_targets=rec.targets)
            totals.update(rows=1,actual_x_tokens=rec.x_tokens,assistant_targets=rec.targets)
            if split=='train':
                code=method.label(row,legal)
                if code is not None:labels.append(dict(signature=method.source.sha(row['messages']),bit=code,
                    root=m['semantic_root_id'],positions=[method.last_position(row,rec,tok)]))
        counts[split]=dict(totals,languages=dict(Counter(r['meta']['language'] for r in values)),
            kinds=dict(Counter(r['meta']['kind'] for r in values)))
    if {s:len(v) for s,v in rows.items()}!=dict(train=21504,dev=2624,test=2048,public_eval=16) or len(labels)!=16384:
        raise ValueError('planned joint dataset count differs')
    roots={s:{r['meta']['semantic_root_id'] for r in rows[s]} for s in ('train','dev','test')}
    if any(roots[a]&roots[b] for a,b in (('train','dev'),('train','test'),('dev','test'))):raise ValueError('joint root overlap')
    parent_native=json.loads((driver.base.CORPUS/'report.json').read_text());exclude=set(parent_native['native_train_offsets'])
    native=np.memmap(ROOT/NATIVE_TRAIN,dtype=np.uint16,mode='r')
    offsets=[p for p in method.source.native_offsets(len(native),5376+len(exclude)+512) if p not in exclude][:5376]
    if len(offsets)!=5376 or set(offsets)&exclude:raise ValueError('new joint native window supply differs')
    CORPUS.mkdir(parents=True,exist_ok=False);manifests={}
    for split,values in rows.items():
        writer=ShardWriter(CORPUS,split)
        for row in values:writer.append(row)
        manifests[split]=writer.close(lineage=info());verify(CORPUS,manifests[split])
    writer=ShardWriter(CORPUS,'aux_labels')
    for row in labels:writer.append(row)
    label_manifest=writer.close(lineage=dict(schema=method.VERSION,state_rows=8192,addition_rows=8192));verify(CORPUS,label_manifest)
    value=dict(info(),status='JOINT_DECIMAL_COURSE_FROZEN',parent=parent,counts=counts,manifests=manifests,
        labels_manifest=label_manifest,dev_contracts=method.approved(rows['dev']),epochs=4,expected_updates=672,
        expected_head_position_events=65536,required_cost_arms=list(ARMS),auxiliary_labels=16384,
        known_state_rows=8192,known_decimal_rows=8192,excluded_parent_addition_pairs=len(excluded),
        native_access='INDEXED_TRAIN_ONLY',native_train_file=NATIVE_TRAIN,native_train_offsets=offsets,
        native_train_sha256=driver.base.training.data.digest(ROOT/NATIVE_TRAIN),native_parent_replay_overlap=0,
        source_state_course_sha256=driver.base.training.data.digest(prior.CORPUS/'report.json'),
        source_small_course_sha256=driver.base.training.data.digest(prior.SMALL_CORPUS/'report.json'),
        new_state_parent_not_used=True,old_public_train_rows_reused=0)
    driver.base.training.write(CORPUS/'report.json',value)
    driver.base.training.write(EVIDENCE/'corpus_report.json',{k:v for k,v in value.items() if k!='dev_contracts'})
    print('[JOINT_DECIMAL_CORPUS] '+json.dumps(dict(counts=counts,updates=672,parent=parent,excluded_pairs=len(excluded))),flush=True);return 0


def read_course():
    r=driver.required_json(CORPUS/'report.json','same-code joint course')
    if r['status']!='JOINT_DECIMAL_COURSE_FROZEN' or r['code_sha256']!=info()['code_sha256']:
        raise ValueError('frozen joint code differs')
    if driver.base.training.data.digest(ROOT/r['native_train_file'])!=r['native_train_sha256']:raise ValueError('native source changed')
    for manifest in (*r['manifests'].values(),r['labels_manifest']):verify(CORPUS,manifest)
    r['labels']={v['signature']:{k:x for k,x in v.items() if k!='signature'} for v in driver.base.training.data.stream_rows(CORPUS,r['labels_manifest'])}
    return r,{s:list(driver.base.training.data.stream_rows(CORPUS,m)) for s,m in r['manifests'].items()}


def owned_head(dim,device='cpu'):
    head=method.new_head(dim,device);HEADS.append(head);return head


def owned_objective(head,hidden,y,labels,windows,dense=False):
    TASK_COUNTS.update(state=sum(v is not None and v<1000 for v in labels),decimal=sum(v is not None and v>=1000 for v in labels))
    return method.objective(head,hidden,y,labels,windows,beta=BETA,dense=dense)


def auxiliary_dev(model,head,tok,values,pad,approved=None):
    import torch
    from tinylm.train import mtp_sft as core
    selected=[r for r in values if r['meta']['kind']=='addition' or r['meta']['kind'].startswith('state_update_')]
    if approved is None:raise ValueError('trusted joint dev contract required')
    totals=Counter();model.eval()
    with torch.no_grad():
        for start in range(0,len(selected),8):
            rows=selected[start:start+8];records=[core.encode_record(r,tok) for r in rows]
            labels=[method.label(r,approved) for r in rows];windows=[[method.last_position(r,rec,tok)] for r,rec in zip(rows,records)]
            x,y,seg=core.pad_records(records,pad,'cuda',fixed_width=1024,batch_size=8)
            labels+=[None]*(8-len(labels));windows+=[None]*(8-len(windows))
            with torch.autocast('cuda',dtype=torch.bfloat16):
                hidden=model(x,return_hidden=True);loss,n,correct,events=method.objective(head,hidden,y,labels,windows,beta=BETA)
            totals.update(loss_sum=float(loss),cases=n,correct=correct)
    model.train();return dict(totals,ce=totals['loss_sum']/totals['cases'],accuracy=totals['correct']/totals['cases'],
        scope='weighted known-row objective; control decimal head intentionally untrained; not free-answer score')


@contextmanager
def runtime(arm):
    global BETA
    before=BETA;BETA=0. if arm=='digits0' else 1.;TASK_COUNTS.clear();HEADS.clear()
    try:
        with ExitStack() as stack:
            for name,value in dict(TAG=TAG,CORPUS=CORPUS,EVIDENCE=EVIDENCE,LOCAL=LOCAL,CODE=CODE,info=info,
                    read_course=read_course,auxiliary_dev=auxiliary_dev).items():stack.enter_context(patch.object(driver,name,value))
            for name,value in dict(ARMS=ARMS,suffix_auxiliary_sum=owned_objective,new_head=owned_head,maybe_flip=method.valid_label).items():
                stack.enter_context(patch.object(driver.method,name,value))
            stack.enter_context(patch.object(driver.base.training,'load_runtime',prior.load_from_parent))
            yield
    finally:BETA=before


def run_arm(args,cost=False):
    arm=args.arm;target=EVIDENCE/(('cost_' if cost else '')+arm)
    with runtime(arm):rc=driver.train(args,cost=cost)
    if rc:raise ValueError('generic joint backend did not complete')
    raw=driver.required_json(target/'report.json','completed generic joint backend')
    if len(HEADS)!=1 or sum(TASK_COUNTS.values())!=raw['auxiliary_targets']:raise ValueError('actual joint task counters differ')
    head=HEADS[0];state_norm=float((head.weight[:2].detach().square().sum()+head.bias[:2].detach().square().sum()).sqrt())
    decimal_norm=float((head.weight[2:].detach().square().sum()+head.bias[2:].detach().square().sum()).sqrt())
    if state_norm==0 or (arm=='digits0' and decimal_norm!=0) or (arm=='digits1' and decimal_norm==0):
        raise ValueError('fixed state and zero/active decimal gradient postcondition failed')
    value=dict(raw,schema='P106B_JOINT_DECIMAL_CANONICAL_ARM_V1',
        status='JOINT_DECIMAL_COST_MEASURED' if cost else 'JOINT_DECIMAL_TRAINED_EVAL_PENDING',
        source_raw_report_sha256=driver.base.training.data.digest(target/'report.json'),
        generic_effective_auxiliary_rows=raw['effective_auxiliary_rows'],
        effective_state_rows=TASK_COUNTS['state'],effective_decimal_rows=TASK_COUNTS['decimal'] if arm=='digits1' else 0,
        computed_known_state_rows=TASK_COUNTS['state'],computed_known_decimal_rows=TASK_COUNTS['decimal'],
        effective_auxiliary_rows=TASK_COUNTS['state']+(TASK_COUNTS['decimal'] if arm=='digits1' else 0),
        fixed_state_multiplier=2.,decimal_multiplier=0. if arm=='digits0' else 2.,
        state_head_parameter_l2=state_norm,decimal_head_parameter_l2=decimal_norm,head_postconditions='PASS',
        metric_scope='generic report counts known rows; canonical task-active counts here; head accuracy is not model answer quality')
    driver.base.training.write(target/'joint_report.json',value)
    print('[JOINT_DECIMAL_FINAL] '+json.dumps({k:value[k] for k in ('arm','status','updates','effective_state_rows','effective_decimal_rows','whole_sec')}),flush=True)
    return 0


def forecast(reports,remaining,completed=()):
    estimates={}
    for arm,r in reports.items():
        steady=sorted(r['step_seconds'][1:])
        if len(steady)!=7 or not all(math.isfinite(t) and t>0 for t in steady):raise ValueError('seven valid joint steady costs required')
        p95=steady[math.ceil(.95*len(steady))-1];estimates[arm]=dict(p95=p95,train_estimate_sec=p95*672+300)
    need=sum(v['train_estimate_sec'] for a,v in estimates.items() if a not in completed)+900+2700
    return dict(arms=estimates,remaining_sec=remaining,needed_sec=need,completed=list(completed),fits=need<remaining,
        evaluation_margin_sec=900,closure_margin_sec=2700,scope='prediction only, not guaranteed completion')


def budget(record=False):
    reports={a:driver.required_json(EVIDENCE/('cost_'+a)/'joint_report.json','both canonical joint costs') for a in ARMS}
    if any(r['updates']!=8 or r['head_postconditions']!='PASS' or r['code_sha256']!=info()['code_sha256'] for r in reports.values()):
        raise ValueError('same-code actual joint cost8/postconditions required')
    completed=[]
    for arm in ARMS:
        p=EVIDENCE/arm/'joint_report.json'
        if p.exists():
            r=json.loads(p.read_text())
            if r['status']!='JOINT_DECIMAL_TRAINED_EVAL_PENDING' or r['updates']!=672:raise ValueError('partial joint arm preserved')
            completed.append(arm)
    value=dict(info(),status='JOINT_BUDGET_MEASURED',**forecast(reports,(driver.base.DEADLINE-datetime.now(timezone.utc)).total_seconds(),completed))
    if record:driver.base.training.write(EVIDENCE/'budget_report.json',value)
    print('[JOINT_DECIMAL_BUDGET] '+json.dumps(value),flush=True)
    if not value['fits']:raise GateNegative('joint pair cannot fit before17 with evaluation/closure')
    return 0


def addition_summary(rows):
    totals=Counter();strata=defaultdict(Counter);roots=defaultdict(list)
    for row in rows:
        m=row['meta']
        if m['kind']!='addition':continue
        ok=row['exact_code_contract'] is True;increment=dict(cases=1,exact=int(ok))
        totals.update(increment);strata[(m['language'],m['view'],m['carry'])].update(increment);roots[m['semantic_root_id']].append(ok)
    if totals['cases']!=1024 or any(len(v)!=4 for v in roots.values()):raise ValueError('new addition1024/four views required')
    totals.update(roots=len(roots),all4_exact_roots=sum(all(v) for v in roots.values()))
    return dict(counts=dict(totals),strata={str(k):dict(v) for k,v in strata.items()},scope='new operand pairs0..99, addition only; not arbitrary math')


def evaluate(args):
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from scripts.p106b_education_followup import answers
    from scripts.diag_p106b_context_quality import probe
    from tinylm.infer.generate import _strip
    r,rows=read_course();target=EVIDENCE/'fresh_test'
    if target.exists():raise GateNegative('old joint test preserved')
    trained={a:driver.required_json(EVIDENCE/a/'joint_report.json','both canonical joint students') for a in ARMS}
    if any(v['updates']!=672 or v['head_postconditions']!='PASS' or v['code_sha256']!=info()['code_sha256'] for v in trained.values()):
        raise ValueError('same-code joint complete arms required')
    idle_before_gpu();began=time.perf_counter();results={};states={};addition={};public={};legacy={};rollouts={}
    with wall_limit(args.max_wall_sec):
        for arm in ('parent',*ARMS):
            driver.base.deadline();torch,model,cfg,tok,initial=prior.load_from_parent('parent_ntp')
            if arm!='parent':
                v=trained[arm]
                if driver.base.training.data.digest(ROOT/v['checkpoint'])!=v['checkpoint_sha256']:raise ValueError('joint checkpoint changed')
                saved=torch.load(ROOT/v['checkpoint'],map_location='cpu',weights_only=True);model.load_state_dict(_strip(saved['model']),strict=True);del saved
            model=model.cuda();folder=LOCAL/'fresh_test'/arm
            results[arm]=driver.base.generate(model,cfg,tok,rows['test'],folder,'joint_code')
            results[arm]['native']=driver.base.training.native_ce(model,driver.base.NATIVE)
            actual=list(driver.base.training.data.stream_rows(folder,results[arm]['raw_manifest']))
            states[arm]=prior.state_summary(actual);addition[arm]=addition_summary(actual)
            public[arm]=driver.generate_public(model,cfg,tok,rows['public_eval'],folder)
            legacy[arm]=answers(PrecisionForward(model,'fp32_math'),cfg,tok,folder,'legacy8')
            groups={}
            for row in rows['test']:
                m=row['meta']
                if m['kind'].startswith('state_update_'):groups.setdefault((m['language'],m['property_kind'],m['target_updated'],m['final_format']),row)
            rollouts[arm]=probe(model,cfg,tok,list(groups.values()),folder,'actual_joint_state_dialogues')
            print('[JOINT_DECIMAL_EVAL] '+json.dumps(dict(arm=arm,state=states[arm],addition=addition[arm],native=results[arm]['native'],legacy8=legacy[arm])),flush=True)
            del model;gc.collect();torch.cuda.empty_cache()
    value=dict(info(),status='JOINT_DECIMAL_FRESH_TEST_COLLECTED',arms=results,state=states,addition=addition,
        public_qa=public,legacy8=legacy,actual_dialogues=rollouts,cases_per_arm=2048,addition_cases_per_arm=1024,
        state_cases_per_arm=512,basic_cases_per_arm=512,whole_sec=time.perf_counter()-began,
        model_training=False,checkpoint_saved=False,head_used_for_generation=False,
        actual_dialogue_scope='subset16 of state512; no independent-case double count')
    driver.base.training.write(target/'report.json',value);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('freeze','cost','budget','train','evaluate'),required=True)
    p.add_argument('--arm',choices=tuple(ARMS),default='digits0');p.add_argument('--max-wall-sec',type=int,default=3600)
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
        if args.mode=='train':budget()
        return run_arm(args,cost=args.mode=='cost')
    except GateNegative as exc:print('[JOINT_DECIMAL_HOLD] '+str(exc),flush=True);return 8
    except KeyboardInterrupt:print('[JOINT_DECIMAL_INTERRUPTED] preserve outputs',flush=True);return 130
    except Exception as exc:print('[JOINT_DECIMAL_ERROR] '+type(exc).__name__+': '+str(exc),flush=True);return 9


if __name__=='__main__':raise SystemExit(main())
