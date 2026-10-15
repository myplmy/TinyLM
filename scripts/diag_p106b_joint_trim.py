#!/usr/bin/env python3
"""Fresh right-padding execution study on an unchanged, verified joint source course."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from contextlib import ExitStack,contextmanager
import copy
from datetime import datetime,timezone
import json
from unittest.mock import patch
from scripts import diag_p106b_joint_decimal as source
from scripts.p106b_padding_probe import width
from scripts.diag_p106b_validation_cost import projection
from scripts.p106b_gate_runtime import GateNegative
from tinylm.train import mtp_sft as core
TAG='p106b_joint_decimal_trim_v1_s1337'
EVIDENCE=ROOT/'test_result/evidence'/TAG
LOCAL=ROOT/'test_result/evidence/local'/TAG
CODE=(*source.CODE,'scripts/diag_p106b_joint_trim.py','scripts/test_p106b_joint_trim.py','scripts/p106b_padding_probe.py',
      'scripts/diag_p106b_validation_cost.py')
ORIGINAL_PAD=core.pad_records


def trimmed_pad(records,pad_id,device='cpu',*,fixed_width=None,batch_size=None):
    execution_width=width([len(r.x) for r in records],True) if fixed_width==1024 else fixed_width
    return ORIGINAL_PAD(records,pad_id,device,fixed_width=execution_width,batch_size=batch_size)


def metadata(producer):
    value=source.info();value.update(tag=TAG,code_sha256={p:source.driver.base.training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        source_dataset_tag=source.TAG,source_dataset_report=str((source.CORPUS/'report.json').relative_to(ROOT)),
        source_dataset_report_sha256=source.driver.base.training.data.digest(source.CORPUS/'report.json'),
        source_producer_code_sha256=producer['code_sha256'],execution_padding='RIGHT_ONLY_ALIGN128_MAX1024',
        maximum_model_context=1024,source_data_changed=False,production_default_changed=False,
        scope='fresh right-trim execution; same joint task contrast, not v1 numeric identity or general intelligence')
    return value


def adapted_course(producer,run_info):
    r=copy.deepcopy(producer);r.update(tag=TAG,code_sha256=run_info['code_sha256'],
        source_producer_code_sha256=producer['code_sha256'],execution_padding=run_info['execution_padding'],
        source_dataset_report_sha256=run_info['source_dataset_report_sha256'])
    return r


@contextmanager
def execution_scope(producer,rows,run_info):
    adapted=adapted_course(producer,run_info)
    with ExitStack() as stack:
        for name,value in dict(TAG=TAG,EVIDENCE=EVIDENCE,LOCAL=LOCAL,CODE=CODE,
                info=lambda:copy.deepcopy(run_info),read_course=lambda:(adapted,rows)).items():
            stack.enter_context(patch.object(source,name,value))
        stack.enter_context(patch.object(core,'pad_records',trimmed_pad))
        yield


def budget(run_info,record=False):
    estimates={};completed=[];training=source.driver.base.training
    val=source.driver.required_json(ROOT/'test_result/evidence/p106b_validation_cost_v1_s1337/joint/report.json','measured parent dev path')
    if val['status']!='VALIDATION_PATH_TIMED' or val['body_before']!=val['body_after']:raise ValueError('read-only validation timing required')
    for arm in source.ARMS:
        r=source.driver.required_json(EVIDENCE/('cost_'+arm)/'joint_report.json','actual right-trim8 canonical costs')
        if r['updates']!=8 or r['code_sha256']!=run_info['code_sha256'] or r['head_postconditions']!='PASS':
            raise ValueError('same-code actual trim costs/postconditions required')
        if len(r['step_seconds'])!=8:raise ValueError('eight timing samples required')
        estimates[arm]=projection(max(r['step_seconds'][1:]),672,val['validation_sum_sec'])
        p=EVIDENCE/arm/'joint_report.json'
        if p.exists():
            done=json.loads(p.read_text())
            if done['updates']!=672 or done['code_sha256']!=run_info['code_sha256'] or done['head_postconditions']!='PASS':
                raise ValueError('partial/changed trim arm preserved')
            completed.append(arm)
    remaining=(source.driver.base.DEADLINE-datetime.now(timezone.utc)).total_seconds()
    needed=sum(v['estimated_train_sec'] for a,v in estimates.items() if a not in completed)+900+2700
    result=dict(run_info,status='TRIM_VALIDATION_INCLUSIVE_BUDGET',estimates=estimates,completed=completed,
        remaining_sec=remaining,needed_sec=needed,fits=needed<remaining,evaluation_margin_sec=900,closure_margin_sec=2700,
        validation_scope='fixed-width parent timing used with buffer; observation, not guaranteed upper bound')
    if record:training.write(EVIDENCE/'budget_report.json',result)
    print('[JOINT_TRIM_BUDGET] '+json.dumps({k:result[k] for k in ('status','completed','remaining_sec','needed_sec','fits')}),flush=True)
    if not result['fits']:raise GateNegative('trim pair/eval/closing exceeds authority window')
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('freeze','cost','budget','train','evaluate'),required=True)
    p.add_argument('--arm',choices=('digits0','digits1'),default='digits0');p.add_argument('--max-wall-sec',type=int,default=3600)
    mode=p.add_mutually_exclusive_group(required=True);mode.add_argument('--execute',action='store_true');mode.add_argument('--check-only',action='store_true');args=p.parse_args()
    if not 60<=args.max_wall_sec<=7200:p.error('bounded60..7200')
    try:
        source.driver.base.deadline();producer,rows=source.read_course();run_info=metadata(producer)
        if args.check_only:print('[JOINT_TRIM_PREFLIGHT] '+json.dumps(run_info),flush=True);return 0
        if not args.execute:p.error('explicit execution required')
        contract=EVIDENCE/'source_contract.json'
        if args.mode=='freeze':
            if EVIDENCE.exists():raise GateNegative('old trim namespace retained')
            source.driver.base.training.write(contract,dict(status='SOURCE_VERIFIED_RIGHT_PADDING_SCHEDULE_FROZEN',run_metadata=run_info,
                source_counts=producer['counts'],expected_updates=672,epochs=4,actual_train_max=max(r['meta']['actual_x_tokens'] for r in rows['train']),
                source_dataset_not_copied=True,producer_unchanged=True))
            print('[JOINT_TRIM_SOURCE_FROZEN] '+json.dumps(dict(tag=TAG,source_sha256=run_info['source_dataset_report_sha256'],updates=672)),flush=True);return 0
        frozen=source.driver.required_json(contract,'fresh same-code trim source contract')
        if frozen['run_metadata']!=run_info:raise ValueError('trim code/source changed after freeze')
        args.max_wall_sec=min(args.max_wall_sec,int((source.driver.base.DEADLINE-datetime.now(timezone.utc)).total_seconds())-2700)
        if args.max_wall_sec<60:raise GateNegative('closing margin required')
        with execution_scope(producer,rows,run_info):
            if args.mode=='budget':return budget(run_info,True)
            if args.mode=='evaluate':return source.evaluate(args)
            if args.mode=='train':budget(run_info)
            return source.run_arm(args,cost=args.mode=='cost')
    except GateNegative as exc:print('[JOINT_TRIM_HOLD] '+str(exc),flush=True);return 8
    except KeyboardInterrupt:print('[JOINT_TRIM_INTERRUPTED] retain source and partial outputs',flush=True);return 130
    except Exception as exc:print('[JOINT_TRIM_ERROR] '+type(exc).__name__+': '+str(exc),flush=True);return 9


if __name__=='__main__':raise SystemExit(main())
