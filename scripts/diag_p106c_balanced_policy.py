#!/usr/bin/env python3
"""User-run P106C B: paired/color-balanced policies, common8/16/32 boundaries.

Requires the frozen A path gate, not A answer accuracy. Original corpora and
checkpoints are read-only. Parent-relative CE is reported, not auto-approved.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import shutil
import statistics
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.diag_p106c_prompt_cache import (ARMS, POLICY_SHA, PREPARE_SHA, SUBJECTS,
    locked_report, frozen_role, prompt_grid, data_hash, digest)
from scripts.p106c_pair_balance import make_plan
from scripts.p106c_replay import Runner, snapshot, restore, cpu_tree, code_contract
from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit, disposition

A_PATH=ROOT/'test_result/evidence/102_P106C_Stage5Wb_prompt_cache_attribution.json'
A_SHA='8EFE4716D6630F9C9A55EA84C69532087443CE413D1E055D87F2AE0AD415A95D'
OUTPUT=ROOT/'HF/sft_ready/p106c_balanced_policy_v1'
BOUNDARIES=(8,16,32)
MAX_WALL_SEC=1800


def require_a(report):
    if (report.get('status')!='PROMPT_CACHE_DIAGNOSTIC_COMPLETE'
            or report.get('case_count')!=384 or report.get('path_gate_passed') is not True
            or report.get('unresolved_fp32_cache_differences')!=0
            or report.get('training_updates')!=0 or report.get('checkpoint_writes')!=0
            or len(report.get('records',[]))!=192):
        raise ValueError('complete A path gate required; no inference from answer score')
    source=report.get('input',{})
    if source.get('policy_sha256')!=POLICY_SHA or source.get('prepare_sha256')!=PREPARE_SHA:
        raise ValueError('A source identities differ')
    if source.get('subjects')!=[list(s) for s in SUBJECTS]:
        raise ValueError('A checkpoint panel differs')


def validate_native_deltas(native_deltas):
    if set(native_deltas)!={'baseline','selected'}:
        raise ValueError('both policies must reach the same boundary before stopping')
    if not all(math.isfinite(v) for v in native_deltas.values()):
        raise ValueError('nonfinite native delta')
    return dict(native_deltas)


def training_history_evidence(history):
    """Snapshot cumulative steps; never reconstruct missing past measurements."""
    if not history:
        raise ValueError('empty training history is not timing evidence')
    trace=[dict(row) for row in history]
    if not all(math.isfinite(row['wall_sec']) and row['wall_sec']>=0
               and math.isfinite(row['loss']) and math.isfinite(row['grad_norm_preclip']) for row in trace):
        raise ValueError('nonfinite training history')
    return {'training_trace':trace, 'first_update_wall_sec':trace[0]['wall_sec'],
            'post_first_update_count':len(trace)-1,
            'post_first_update_median_sec':statistics.median(r['wall_sec'] for r in trace[1:]) if len(trace)>1 else None,
            'post_first20_grad_peak_preclip':max(r['grad_norm_preclip'] for r in trace[20:]) if len(trace)>20 else None,
            'training_timing_scope':'per update including microbatches/optimizer/synchronize; excludes evaluations and restoration; first may include compile'}


def check():
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError('new/partial B output preserved; use a new stage to retry')
    a_sha=digest(A_PATH)
    if a_sha!=A_SHA:
        raise ValueError('frozen A report changed')
    a=json.loads(A_PATH.read_text(encoding='utf-8'));require_a(a)
    if a['input']['grid_sha256']!=data_hash(prompt_grid(frozen_role('sealed'))):
        raise ValueError('A prompt grid differs')
    policy=locked_report('policy/report.json',POLICY_SHA)
    replay=json.loads((ROOT/'HF/sft_ready/p106c_replay_v1/replay/report.json').read_text(encoding='utf-8'))
    if digest(ROOT/'HF/sft_ready/p106c_replay_v1/replay/report.json')!='1791C104589F5A938BB062F6947E57A53244419DCBA325F0DECC8B6354C9A248':
        raise ValueError('frozen selector result changed')
    for key,sha in (('parent','sha'),('tokenizer','tok_sha')):
        if digest(ROOT/ARMS['b'][key])!=ARMS['b'][sha]:
            raise ValueError('B parent/tokenizer changed')
    if shutil.disk_usage(ROOT).free<8*2**30:
        raise ValueError('8GiB free disk required; no automatic cleanup')
    from tokenizers import Tokenizer
    from scripts.train_sft_p090 import encode_records
    from scripts.p106c_data import canonical
    tok=Tokenizer.from_file(str(ROOT/ARMS['b']['tokenizer']))
    train,rehearsal=frozen_role('train'),frozen_role('rehearsal')
    for role in ('select','dev','retention'):
        frozen_role(role)
    tr=encode_records([canonical(r) for r in train],tok,256,32768)
    rh=encode_records([canonical(r) for r in rehearsal],tok,256,32768)
    plan=make_plan(train,rehearsal,tr,rh,replay['eligible_blocks'])
    return plan,{'schema':'P106C_BALANCED_POLICY_PREFLIGHT_V1','a_sha256':a_sha,
        'policy_sha256':POLICY_SHA,'prepare_sha256':PREPARE_SHA,'parent_sha256':ARMS['b']['sha'],
        'plan_sha256':data_hash(plan),'eligible_blocks':replay['eligible_blocks'],
        'selected_top_fraction':plan['selected_top_fraction'],'max_pair_exposures':plan['max_pair_exposures'],
        'boundaries':list(BOUNDARIES),'max_updates_per_arm':32,'native_parent_limit':None,
        'micro':8,'accum':4,'context':256,'checkpoint_on':True,'teacher_requests':0,
        'code':code_contract(),'driver_sha256':digest(Path(__file__)),
        'plan_source_sha256':digest(ROOT/'scripts/p106c_pair_balance.py'),
        'claim':'matched policies; A and old sealed reused as posthoc diagnostics, not unseen test'}


def write_json(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def execute(plan,info):
    report={'schema':'P106C_BALANCED_POLICY_B_V1','status':'RUNNING','input':info,'boundaries':[],
            'training_updates':0,'checkpoint_writes':0,'teacher_requests':0}
    began=time.perf_counter();runner=None
    idle_before_gpu();OUTPUT.mkdir(parents=True,exist_ok=False)
    write_json(OUTPUT/'batch_plan.json',plan)
    try:
        with wall_limit(MAX_WALL_SEC):
            runner=Runner()
            calibration=json.loads((ROOT/'HF/sft_ready/p106c_replay_v1/calibrate/report.json').read_text())
            if digest(ROOT/'HF/sft_ready/p106c_replay_v1/calibrate/report.json')!='15ADCB9F8C1A8EB378993189BFA95673D9ED02A83BD51F20EA33A5B25E7C3DCB':
                raise ValueError('parent calibration changed')
            if runner.s0_sha256!=calibration['s0_sha256']:
                raise ValueError('fresh state differs from calibrated parent/optimizer/RNG')
            parent_ce=calibration['native_parent']['ce']
            # CPU snapshots preserve each live policy, only one CUDA model is resident.
            states={a:runner.s0 for a in ('baseline','selected')}
            histories={a:[] for a in states}; counts={a:Counter() for a in states}
            probes,controls=frozen_role('sealed'),frozen_role('controls')
            first=0
            for end in BOUNDARIES:
                boundary={'updates_per_arm':end,'arms':[]}
                for arm in ('baseline','selected'):
                    restore(runner.base,runner.optimizers,states[arm])
                    for step in range(first,end):
                        spec=plan[arm][step]
                        rows=[runner.encoded['train'][i] for i in spec['candidate']]+[runner.encoded['rehearsal'][i] for i in spec['rehearsal']]
                        histories[arm].append({'update':step+1,**runner.step(rows,[1]*32,12000+step)})
                        counts[arm]['x_tokens']+=sum(len(r[0]) for r in rows)
                        counts[arm]['targets']+=sum(r[2] for r in rows)
                    states[arm]=snapshot(runner.base,runner.optimizers)
                    answers=runner.answers(probes,OUTPUT,f'{arm}_{end:03d}_transfer')
                    extras=runner.answers(controls,OUTPUT,f'{arm}_{end:03d}_controls')
                    native=runner.native()
                    row={'arm':arm,'updates':end,**dict(counts[arm]),'native_ce':native['ce'],
                         'parent_native_delta':native['ce']-parent_ce,'transfer_probe':answers,'controls':extras,
                         'dev':runner.scores('dev'),'grad_peak_preclip':max(r['grad_norm_preclip'] for r in histories[arm])}
                    row.update(training_history_evidence(histories[arm]))
                    boundary['arms'].append(row)
                    with (OUTPUT/f'{arm}_{end:03d}_student.pt').open('xb') as f:
                        runner.torch.save({'model':cpu_tree(runner.base.state_dict()),'cfg':runner.cfg.__dict__,
                            'sft':{'arm':arm,'updates':end,'input':info,'claim':'POSTHOC_CLOSED_WORLD'}},f)
                    report['checkpoint_writes']+=1
                left,right=boundary['arms']
                if (left['x_tokens'],left['targets'])!=(right['x_tokens'],right['targets']):
                    raise ValueError('matched boundary has different token/target budgets')
                boundary['parent_native_deltas']=validate_native_deltas({r['arm']:r['parent_native_delta'] for r in boundary['arms']})
                report['boundaries'].append(boundary)
                write_json(OUTPUT/f'boundary_{end:03d}.json',boundary)
                print('[B_BOUNDARY] '+json.dumps(boundary,ensure_ascii=False),flush=True)
                first=end
            report.update(status='BALANCED_POLICY_COMPARISON_COMPLETE',exit_code=0)
            report.update(parent_native_ce=parent_ce,completed_updates_per_arm=first,
                          actual_training_updates=runner.updates,policy_adoption='NOT_DECIDED',
                          evaluation_scope='POSTHOC_REUSED_PROBES_NOT_NEW_SEALED_GENERALIZATION')
    except (Exception,KeyboardInterrupt) as exc:
        status,rc=disposition(exc)
        report.update(status=status,exit_code=rc,reason=f'{type(exc).__name__}: {exc}')
    finally:
        if runner is not None:
            report['training_updates']=runner.updates
            report['peak_reserved_mib']=runner.torch.cuda.max_memory_reserved()/2**20
        report['whole_wall_sec']=time.perf_counter()-began
        write_json(OUTPUT/'report.json',report)
        print('[P106C_B_SUMMARY] '+json.dumps({k:v for k,v in report.items() if k!='boundaries'},ensure_ascii=False),flush=True)
    return report['exit_code']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--check-only',action='store_true');g.add_argument('--execute',action='store_true')
    args=p.parse_args()
    try:
        plan,info=check()
        if args.check_only:print(json.dumps(info,ensure_ascii=False));return 0
        return execute(plan,info)
    except Exception as exc:
        print(f'[HOLD] {type(exc).__name__}: {exc}',file=sys.stderr);return 8


if __name__=='__main__':
    raise SystemExit(main())
