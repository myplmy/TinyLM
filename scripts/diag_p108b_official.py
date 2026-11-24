#!/usr/bin/env python3
"""Reuse the closed official11-task pipeline with new exact P108B packets."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import gc
import hashlib
import json
from pathlib import Path
import sysconfig

import tinylm
import torch
from scripts import diag_p108_frozen_edit_official as owner
from scripts import diag_p108b_evaluate as evaluation
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_value_library as library
from scripts import p108b_replay as new_replay
from scripts import p108b_decode as function_tools
from scripts.p108b_tinylm import TinyAdapter
from scripts import interactive_research_infer as manual
from scripts import p106b_official_lm_adapter as lm_adapter

BASE=atlas.BASE
OUTPUT=BASE/'official_v1'
BASELINE=owner.OUTPUT/'original/report.json'
CODE=('scripts/diag_p108b_official.py','scripts/test_p108b_official.py')


def baseline_reference():
    r=json.loads(BASELINE.read_text(encoding='utf-8'))
    if r['status']!='OFFICIAL_ELEVEN_TASKS_COMPLETE'or r['returncode']!=0 or len(r['actual_counts'])!=11:
        raise ValueError('closed unchanged original11 baseline required')
    if r['policy']!=owner.official.policy():raise ValueError('official prompt/likelihood policy differs from the reusable baseline')
    return dict(path=str(BASELINE.relative_to(atlas.ROOT)),sha256=manual.file_sha(BASELINE),
        origin=r['frozen_model_origin'],actual_counts=r['actual_counts'],task_specs=r['task_specs'],policy=r['policy'])


def identity():
    parent=json.loads((BASE/'evaluation_profile_v1.json').read_text(encoding='utf-8'))
    names=sorted(set(owner.CODE)|set(parent['sources'])|set(CODE))
    files={n:owner.official.digest(atlas.ROOT/n)for n in names}
    return dict(files=files,sha256=hashlib.sha256(lm_adapter.canonical(files)).hexdigest().upper())


def bundle():
    p=evaluation.verify();base=baseline_reference()
    if p['origin']!=base['origin']:raise ValueError('original checkpoint/tokenizer/core differs from existing benchmark baseline')
    return {'actual/report.json':dict(origin=p['origin'])},None,None


@contextmanager
def model_runtime(name,_frozen,_packets,_expected,target):
    p=evaluation.verify();arm=new_replay.read_arm(name)
    data=json.loads((BASE/'data.json').read_text(encoding='utf-8'));fits=[r for r in data['rows']if r['split']=='fit']
    lm=adapter=active=None
    with manual.selected_runtime(manual.resolve_model(p['model']))as active:
        adapter=TinyAdapter(active,fits,data['calibration_questions'],budget=library.Budget(1800))
        try:
            with new_replay.install(adapter,arm)as proof:
                canary=adapter.generate(arm['answers'][0],max_new=64,variant=name+':OFFICIAL_REPLAY_CANARY')
                if canary['generation']['generated_ids']!=arm['answers'][0]['generation']['generated_ids']:
                    raise RuntimeError('official admission exact generation replay differs')
                proof.update(origin=p['origin'],generation_replay_count=1,complete_core_sha_replayed=True,
                    canary=canary,official_evaluation_does_not_use_chat_generation=True)
                lm=lm_adapter.create_adapter(active,runtime_root=Path(sysconfig.get_paths()['purelib']),batch_size=8)
                try:yield lm,proof
                finally:
                    if lm is not None:lm.close();lm=None
        finally:
            if adapter is not None:adapter.close();adapter=None
    active=None;gc.collect()


def evaluator():
    frozen={name:manual.file_sha(BASE/name)for name in('evaluation_profile_v1.json','policy_profile_v1.json','geometry/report.json')}
    return function_tools.private_function(owner.evaluate,identity=identity,bundle=bundle,
        model_runtime=model_runtime,OUTPUT=OUTPUT,BASE=BASE,FROZEN=frozen,TAG='p108b_official11_v1_20261116')


def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check-only',action='store_true');group.add_argument('--execute',action='store_true')
    parser.add_argument('--arm');parser.add_argument('--source-sha256');parser.add_argument('--max-wall-sec',type=int,default=1800)
    args=parser.parse_args();p=evaluation.verify();signature=identity();baseline=baseline_reference()
    if args.check_only:
        print(json.dumps(dict(status='OFFICIAL_CPU_PREFLIGHT_NO_MODEL',arms=p['arms'][1:],source_sha256=signature['sha256'],
            original_baseline_reused=baseline['path'],original_counts=baseline['actual_counts'],new_package_installs=0)))
        return
    if args.arm not in p['arms'][1:]or args.source_sha256!=signature['sha256']or not 60<=args.max_wall_sec<=3600:
        parser.error('one preselected edited arm, exact source SHA and60..3600seconds required; original baseline is reused')
    failure=None;result=dict(status='OFFICIAL_WRAPPER_STARTED')
    try:result=evaluator()(args.arm,args.source_sha256,args.max_wall_sec)
    except BaseException as error:
        failure=error;result.update(status='OFFICIAL_WRAPPER_ERROR',error_type=type(error).__name__,error=str(error))
    finally:
        gc.collect();cleanup_error=library.cleanup(result)
        if failure is None:failure=cleanup_error
        result.update(original_baseline_reference=baseline,source_identity_unchanged=identity()==signature)
        library.write_new(OUTPUT/(args.arm+'_cleanup.json'),result)
        print('[NEW_OFFICIAL_CLOSURE] '+json.dumps({k:result.get(k)for k in('status','arm','seconds','cuda_allocated_after_bytes','cuda_reserved_after_bytes')}),flush=True)
    if failure is not None:raise RuntimeError('preserved official evaluation failure')from failure


if __name__=='__main__':main()
