#!/usr/bin/env python3
"""CPU-only synthetic policy contracts/costs; no model, corpus, or quality claim."""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import resource as os_resource
import statistics
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

import torch
from scripts import diag_p106b_resource_matrix as resource
from tinylm.train import hybrid_mntp as h
from tinylm.train.adaptive_masking import PolicyConfig,HardMaskPolicy,audit_selection

SCHEMA='P107_HARD_MASK_CPU_CONTRACT_COST_V1'
TAG='p107_hard_mask_policy_v2_20261027'
OWN=('tinylm/train/adaptive_masking.py','tinylm/train/hybrid_mntp.py',
     'scripts/diag_p107_adaptive_masking.py','scripts/test_p107_adaptive_masking.py',
     'scripts/test_p107_adaptive_driver.py','scripts/diag_p106b_resource_matrix.py')
need=resource.need


def identity():
    files={name:resource.digest(resource.safe(name)) for name in OWN}
    return dict(files=files,sha256=resource.sha(files))


def fixture(vocab,index):
    pos=torch.arange(1025)
    # Deliberately repeated synthetic types; labels below are NOT real languages.
    tokens=((pos[None,:]+torch.arange(8)[:,None]*11+index*7)%128+35).long()
    need(vocab>int(tokens.max()),'fixture vocabulary too small')
    docs=(pos//256).clamp_max(3)[None,:].expand(8,-1).clone().long()
    docs[0,-17:]=-1;tokens[0,-17:]=0
    groups={'all':torch.ones_like(tokens,dtype=torch.bool),
            'fixture_ko_label':(pos%2==0)[None,:].expand_as(tokens),
            'fixture_en_label':(pos%2==1)[None,:].expand_as(tokens),
            'fixture_digit_label':tokens%7==0,'fixture_rare_label':tokens>=155}
    return tokens,docs,groups


def config(vocab,unseen,source):
    return PolicyConfig(vocab_size=vocab,mask_rate=.15,ema=.2,refresh_updates=2,
        unseen_policy=unseen,seed=1337,special_max=34,mask_id=13,
        corpus_sha256=resource.sha(dict(fixture='SYNTHETIC_FIXED_TYPES_V1',vocab=vocab)),
        run_sha256=source['sha256'])


def synthetic_predictions(batch):
    # A deterministic fake score for statistics tests, never a model accuracy.
    return torch.where(batch.targets%3==0,batch.targets,torch.zeros_like(batch.targets)).clamp_min(0)


def execute_case(report,vocab,condition,source,budget):
    policy=None if condition=='uniform' else HardMaskPolicy(config(vocab,'keep' if condition=='hard_keep' else 'prior',source))
    generator=torch.Generator().manual_seed(1337)
    row=dict(vocab=vocab,condition=condition,status='STARTED',attempts=[],resume_verified=False,
             classification='SYNTHETIC_LABELS_ONLY_NOT_KOREAN_RARITY_OR_NUMERIC_CORPUS')
    report['cases'].append(row)
    resumed=None;resumed_generator=None
    for index in range(8):
        budget.check();tokens,docs,groups=fixture(vocab,index)
        attempt=dict(index=index,status='STARTED',warmup=index==0);row['attempts'].append(attempt)
        if policy is not None:policy.begin_update(index,split='train',expected_observations=1)
        started=time.perf_counter()
        if policy is None:
            selected=h.uniform_mntp_selection(tokens,docs,vocab_size=vocab,probability=.15,generator=generator)
        else:selected,probabilities=policy.select(tokens,docs,adaptive=True)
        attempt['selection_seconds']=time.perf_counter()-started
        if policy is None:
            eligible=h.eligible_mntp(tokens,docs,vocab_size=vocab)
            probabilities=eligible.double()*.15
        started=time.perf_counter();batch=h.mntp_batch(tokens,docs,selected,vocab_size=vocab)
        attempt['materialize_seconds']=time.perf_counter()-started
        need(batch.target_count>0,'do not force missing targets')
        predictions=synthetic_predictions(batch)
        started=time.perf_counter()
        if policy is not None:policy.observe(batch,predictions,observation_index=0)
        attempt['observe_seconds']=time.perf_counter()-started
        started=time.perf_counter()
        if policy is not None:attempt['virtual_commit']=policy.finish_update(accepted=True)
        attempt['commit_seconds']=time.perf_counter()-started
        eligible=h.eligible_mntp(tokens,docs,vocab_size=vocab)
        need(bool((selected&~eligible).any()) is False,'protected position selected')
        for r in range(tokens.shape[0]):
            need(abs(float(probabilities[r].sum())-.15*int(eligible[r].sum()))<1e-8,'expected row budget drift')
        attempt.update(status='ATTEMPT_COMPLETE',selected_targets=batch.target_count,
            executed_model_input_tokens=0,source_fixture_positions=tokens.numel(),
            group_audit=audit_selection(eligible,selected,probabilities,groups,comparison_dtype=torch.get_default_dtype()))
        if resumed is not None:
            resumed.begin_update(index,split='train',expected_observations=1)
            other,other_prob=resumed.select(tokens,docs,adaptive=True)
            need(torch.equal(selected,other) and torch.equal(probabilities,other_prob),'next resumed selection differs')
            resumed.observe(batch,predictions,observation_index=0);resumed.finish_update(accepted=True)
            need(policy.state_dict()['fingerprint']==resumed.state_dict()['fingerprint'],'resumed statistics differ')
        if resumed_generator is not None:
            other=h.uniform_mntp_selection(tokens,docs,vocab_size=vocab,probability=.15,generator=resumed_generator)
            need(torch.equal(selected,other) and torch.equal(generator.get_state(),resumed_generator.get_state()),
                 'uniform generator resume differs')
        if index==2:
            if policy is None:
                resumed_generator=torch.Generator();resumed_generator.set_state(generator.get_state().clone())
            else:
                started=time.perf_counter();state=policy.state_dict()
                row['state_export_seconds']=time.perf_counter()-started
                started=time.perf_counter();resumed=HardMaskPolicy(policy.config);resumed.load_state_dict(state)
                row['state_load_seconds']=time.perf_counter()-started
                row['state_storage']=policy.storage_audit()
    row.update(status='CASE_COMPLETE',resume_verified=True,
               median_seconds={key:statistics.median(a[key] for a in row['attempts'] if not a['warmup'])
                               for key in ('selection_seconds','materialize_seconds','observe_seconds','commit_seconds')})
    if policy is not None:
        row['final_state_sha256']=policy.state_dict()['fingerprint']
        row['observed_types']=int((policy.lifetime_total>0).sum())
        row['never_observed_types']=int((policy.last_seen<0).sum())
    return row


def validate(profile,args):
    need(profile.get('schema')==SCHEMA and profile.get('tag')==TAG
         and profile.get('root_approved') is True and profile.get('authority_directive')==96
         and profile.get('source_sha256')==identity()['sha256'] and args.max_wall_sec==300
         and profile.get('models')==profile.get('optimizer_updates')==profile.get('checkpoint_writes')==0
         and profile.get('deadline')=='2026-10-27T08:00:00+00:00', 'exact CPU-only profile required')
    if (resource.DEADLINE-datetime.now(timezone.utc)).total_seconds()<=360:
        raise TimeoutError('insufficient CPU/closure deadline margin')
    ref=profile['cpu_contract']
    need(ref['actual_exit']==0 and resource.digest(resource.safe(ref['path']))==ref['sha256'], 'closed CPU contract required')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True);parser.add_argument('--profile-sha256',required=True)
    parser.add_argument('--max-wall-sec',type=int,required=True)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check-only',action='store_true');group.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    profile=resource.read_ref(dict(path=args.profile,sha256=args.profile_sha256));validate(profile,args)
    need(not torch.cuda.is_initialized(),'CPU policy process must not inherit an initialized CUDA context')
    if args.check_only:
        print(json.dumps(dict(status='CPU_POLICY_METADATA_ONLY',models=0,gpu_calls=0)));return 0
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    output=resource.safe('test_result/evidence/'+TAG+'/cpu/report.json');need(not output.exists(),'new namespace required')
    source=identity();budget=resource.Budget(300);rc=9
    report=dict(schema=SCHEMA,tag=TAG,source=source,profile_sha256=args.profile_sha256,
        started_at=datetime.now(timezone.utc).isoformat(),status='STARTED',cases=[],models=0,
        optimizer_updates=0,checkpoint_writes=0,gpu_calls=0,quality_claim=False,
        torch_version=torch.__version__,cpu_threads=1,source_corpus_reads=0,
        draw_dtype=str(torch.get_default_dtype()),expected_budget='ANALYTICAL_FP64;REPRESENTED_THRESHOLDS_RECORDED_SEPARATELY')
    try:
        with resource.wall(300),patch.object(torch,'load',side_effect=ValueError('model load forbidden')), \
             patch.object(torch,'save',side_effect=ValueError('checkpoint save forbidden')):
            for vocab in (32768,262144):
                for condition in ('uniform','hard_keep','hard_prior'):
                    row=execute_case(report,vocab,condition,source,budget)
                    print(json.dumps(dict(vocab=vocab,condition=condition,status=row['status'])),flush=True)
        report['status'],rc='CPU_TECHNICAL_COMPLETE_NOT_QUALITY',0
    except BaseException as exc:
        rc=8 if isinstance(exc,TimeoutError) else 9
        report.update(status='CPU_BUDGET_HOLD' if rc==8 else 'CPU_ERROR',error=dict(type=type(exc).__name__,message=str(exc)[:2000]))
    finally:
        report['cuda_initialized']=torch.cuda.is_initialized();report['source_unchanged']=identity()==source
        if report['cuda_initialized'] or not report['source_unchanged']:
            rc=9;report['status']='CPU_INDEPENDENT_FINAL_CHECK_ERROR'
        report.update(exit_code=rc,seconds=time.monotonic()-budget.started,
            ended_at=datetime.now(timezone.utc).isoformat(),process_lifetime_peak_rss_bytes=os_resource.getrusage(os_resource.RUSAGE_SELF).ru_maxrss*1024)
        resource.write_new(output,report)
        print(json.dumps(dict(status=report['status'],actual_exit=rc,seconds=report['seconds'])))
    return rc


if __name__=='__main__':raise SystemExit(main())
