#!/usr/bin/env python3
"""P106B-only stage receipts; shared runlog/queue and teacher defaults unchanged."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
NAMES={
    'balanced':'P106B_Stage4cWc_balanced_final_verdict',
    'lora':'P106B_Stage5cWb_lora_conditioned_final_verdict',
    'review':'P106B_Stage5dWb_review_conditioned_final_verdict',
    'contract':'P106B_Stage5eW_stage_receipt_contract',
}


def phase_commands(mode):
    py=[sys.executable,'-B','-X','utf8']
    if mode=='contract':
        return [('REGRESSION',py+['scripts/test_p106b_stage_receipt.py']),
                ('PREFLIGHT',py+['scripts/p106b_stage_receipt.py','--mode','contract','--check-only']),
                ('EXECUTE',py+['scripts/p106b_stage_receipt.py','--mode','contract','--self-test'])]
    if mode=='balanced':
        test='scripts/test_p106b_stage4_recovery.py'
        base=py+['scripts/diag_p106b_mixed_repeat4.py','--mode','new-balanced']
    elif mode in ('lora','review'):
        test='scripts/test_p106b_mtp_teacher.py'
        base=py+['scripts/diag_p106b_mtp_teacher.py','--mode',mode]
    else:raise ValueError('unsupported P106B mode')
    return [('REGRESSION',py+[test]),('PREFLIGHT',base+['--check-only']),('EXECUTE',base+['--execute'])]


def pipeline(phases,launch,note,*,experiment):
    if [p[0] for p in phases]!=['REGRESSION','PREFLIGHT','EXECUTE']:
        raise ValueError('three exact phases required; zero work is not success')
    states=[{'phase':label,'status':'NOT_RUN','returncode':None} for label,_ in phases]
    rc=0;status='COMPLETE';failed=None;current=None;main_invoked=False
    try:
        for index,(label,command) in enumerate(phases):
            current=index;failed=label
            note(f'[PHASE_BEGIN] {index+1}/3 {label}; child success is not the final experiment verdict')
            states[index]['status']='RUNNING'
            if label=='EXECUTE':main_invoked=True
            child=launch(command)
            if type(child)!=int:raise ValueError('integer child rc required')
            states[index].update(returncode=child,status='PASS' if child==0 else 'INTERRUPTED' if child==130 else 'HOLD' if child==8 and label!='REGRESSION' else 'ERROR')
            note(f'[PHASE_END] {index+1}/3 {label}; rc={child}; status={states[index]["status"]}')
            if child:
                rc=9 if child==8 and label=='REGRESSION' else child
                status='HOLD' if child==8 and label!='REGRESSION' else 'INTERRUPTED' if child==130 else 'ERROR'
                break
            failed=None
    except KeyboardInterrupt:
        rc=130;status='INTERRUPTED'
        if current is not None and states[current]['status']=='RUNNING':
            states[current].update(status='INTERRUPTED',returncode=130)
    except Exception as exc:
        rc=9;status='ERROR'
        if current is not None and states[current]['status']=='RUNNING':
            states[current].update(status='ERROR',returncode=9)
        # Do not print payloads or environment variables in a logging failure.
        print('[RECEIPT_ERROR] '+type(exc).__name__,file=sys.stderr)
    receipt={'schema':'P106B_STAGE_RECEIPT_V1','experiment':experiment,'status':status,
             'returncode':rc,'failed_phase':failed,'phases':states,
             'main_experiment_invoked':main_invoked,
             'evidence_scope':'stage execution, not model quality or scientific adoption'}
    line='[EXPERIMENT_FINAL] '+json.dumps(receipt,ensure_ascii=False,sort_keys=True)
    try:note(line)
    except Exception as exc:
        receipt.update(status='LOG_ERROR',returncode=9)
        print('[RECEIPT_ERROR] final receipt could not be logged: '+type(exc).__name__,file=sys.stderr)
        print('[EXPERIMENT_FINAL] '+json.dumps(receipt,ensure_ascii=False,sort_keys=True),flush=True)
    return receipt


def contract():
    receipts=[]
    for values in ([0,0,0],[0,8],[1]):
        iterator=iter(values);notes=[]
        result=pipeline(phase_commands('contract'),lambda _:next(iterator),notes.append,experiment='CPU_FIXTURE')
        receipts.append(result)
    assert [x['status'] for x in receipts]==['COMPLETE','HOLD','ERROR']
    assert receipts[1]['phases'][2]['status']=='NOT_RUN'
    print('[RECEIPT_CONTRACT] '+json.dumps({'cases':receipts,'model_gpu_training':'NOT_RUN'},ensure_ascii=False))
    return 0


def run(name,mode):
    if NAMES.get(mode)!=name:raise ValueError('exact new stage/name pair required')
    def note(text):
        print(text,flush=True)
    def launch(command):
        note('[PHASE_COMMAND] '+json.dumps(command,ensure_ascii=False))
        return subprocess.run(command,cwd=ROOT,stdin=subprocess.DEVNULL).returncode
    return pipeline(phase_commands(mode),launch,note,experiment=name)['returncode']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=tuple(NAMES),required=True)
    p.add_argument('--name')
    action=p.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute',action='store_true')
    action.add_argument('--check-only',action='store_true')
    action.add_argument('--self-test',action='store_true')
    a=p.parse_args()
    if a.check_only:
        phase_commands(a.mode);print('[CHECK_ONLY] exact P106B stages; this is not the data/model prerequisite check');return 0
    if a.self_test:return contract()
    try:return run(a.name,a.mode)
    except (ValueError,RuntimeError) as exc:
        print('[ERROR] '+str(exc),file=sys.stderr);return 9


if __name__=='__main__':raise SystemExit(main())
