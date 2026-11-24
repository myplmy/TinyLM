"""Train P107 adaptive masking with P109 visits and matched native/recomputed heads."""

import argparse
from datetime import datetime, timedelta
import json
import os
import subprocess
import sys
from unittest.mock import patch

import torch

from scripts import diag_p102a_adaptive_fp32_recompute as head
from scripts import diag_p107_g4_policy_visibility_cpu as policy_probe
from scripts import diag_p107_g4_policy_visibility_cuda as cuda_probe
from scripts import diag_p107_g4_r2_visibility as fixed
from scripts.diag_p102a_g4_recompute_shapes import idle
from tinylm.model import transformer, visibility
from tinylm.train.hybrid_session import HybridTrainingSession


TAG = 'p107_g4_policy_adaptive_v1_20261119'
OUT = fixed.OUT.with_name(TAG)
POLICIES = ('balanced_count', 'second_shuffle_r2')
ARMS = tuple(f'{policy}_{mode}' for policy in POLICIES for mode in ('reference', 'recompute'))
CAP, SEED = 85, 1337
SOURCES = tuple(dict.fromkeys((*policy_probe.SOURCES, *(s for s in fixed.SOURCES if s.endswith('.py')),
    'scripts/diag_p107_g4_policy_visibility_cuda.py','scripts/diag_p107_g4_policy_adaptive.py',
    'tinylm/train/hybrid_session.py','tinylm/train/adaptive_training.py','tinylm/train/adaptive_masking.py')))
SHA, WRITE = head.SHA, head.WRITE


def read(path):
    return json.loads(path.read_bytes())


def planning(cfg, owners):
    receipts = {}
    for name in POLICIES:
        entries = []
        for index in range(head.UPDATES):
            route = list(policy_probe.policy.route_for(cfg, owners, name, SEED, index, head.UPDATES))
            trace = policy_probe.policy.cla.trace(cfg, owners, route)
            entries.append(dict(update=index, route=route, visits=trace['visits'], kv=trace['kv_entries']))
        assert sum(row['visits'] for row in entries) == 28 * head.UPDATES
        receipts[name] = entries
    assert {r['visits'] for r in receipts['balanced_count']} == {16,28,40}
    uniform = list(policy_probe.policy.route_for(cfg,owners,'uniform_r2',SEED,0,head.UPDATES))
    for row in receipts['second_shuffle_r2']:
        assert row['visits'] == 28 and row['route'][:14] == uniform[:14] and row['route'][26:] == uniform[26:]
    assert len({tuple(x['route']) for x in receipts['second_shuffle_r2']}) >= 2
    return receipts


def contract():
    before = fixed.OUT / 'profile.json'
    result = fixed.OUT / 'report.json'
    v = cuda_probe.OUT / 'report.json'
    prior = read(result)
    checks = prior['checks']
    assert prior['gpu_returned'] and set(prior['exits'].values()) == {0}
    assert all(all(x.values()) if isinstance(x,dict) else x for x in checks.values())
    route_probe = read(v)
    assert (route_probe['closed_cases'],route_probe['open_cases']) == (12,9)
    assert SHA(head.warm.PARENT) == head.PARENT_SHA
    archived = read(before)['contract']
    for name, sha in archived['pins'].items():
        if name.endswith('.py'):
            assert SHA(head.ROOT / name) == sha, name
    model = fixed.make_model('cpu')
    routes = planning(model.cfg,model.owner)
    workload = head.BATCH*head.WIDTH*head.MICROS*head.UPDATES
    assert len(archived['updates']) == head.UPDATES and archived['rows'] == head.ROWS
    assert archived['parent'] == head.PARENT_SHA
    return dict(tag=TAG,g4_parent_sha256=head.PARENT_SHA,fixed_profile_sha256=SHA(before),
        fixed_report_sha256=SHA(result),visibility_probe_sha256=SHA(v),sources={s:SHA(head.ROOT / s) for s in SOURCES},
        seed=SEED,routes=routes,inputs_per_arm=workload,visits_per_input=28,token_layer_visits=workload*28,
        updates=head.UPDATES,heads=list(ARMS),approval='WIP176',worker_cap=CAP,checkpoint_writes=0)


def worker(name, frozen):
    from tinylm import model as package

    policy, mode = name.rsplit('_',1)
    out = OUT / name
    out.mkdir(exist_ok=False)
    sig = (fixed.OUT/'profile.json').read_bytes()
    with (out/'profile.json').open('xb') as stream:
        stream.write(sig)
    assert SHA(out/'profile.json') == frozen['fixed_profile_sha256']
    receipts = frozen['routes'][policy]
    route, calls, completed = None, 0, []
    original_update = HybridTrainingSession.update

    def routed(cfg):
        cfg.train_repeat = 2.
        return policy_probe.policy.RoutedG4(cfg)

    def prepare(mask,tokens,cfg,schedule,**kwargs):
        nonlocal calls
        if route is None or tuple(schedule) != route:
            raise ValueError('only the active validated route can use experimental visibility')
        calls += 1
        return visibility.prepare_visibility(mask,tokens,cfg,range(cfg.n_layers),**kwargs)

    def update(session):
        nonlocal route, calls
        index = session.cursor
        item = receipts[index]
        m = session.trainer.model
        assert route is None and m.training_route is None
        assert list(policy_probe.policy.route_for(m.cfg,m.owner,policy,SEED,index,head.UPDATES)) == item['route']
        assert session.trainer.source.cursor == item['update'] == index
        route, calls = tuple(item['route']), 0
        m.training_route = route
        try:
            row = original_update(session)
            assert row['model_forwards'] == calls == head.MICROS and row['optimizer_applied']
            assert session.cursor == index + 1 and m.training_route == route
            completed.append(dict(update=index,visits=item['visits'],kv=item['kv'],visibility_calls=calls,
                                  tokens=row['executed_input_tokens'],optimizer_applied=True))
            return row
        finally:
            route, m.training_route = None, None

    profile = read(fixed.OUT/'profile.json')['contract']
    with (patch.object(head,'OUT',out),patch.object(transformer,'prepare_visibility',prepare),
          patch.object(package,'TiedMLPTransformer',routed),patch.object(HybridTrainingSession,'update',update)):
        code = head.worker(mode,profile)
    total = sum(x['tokens']*x['visits'] for x in completed)
    assert len(completed) == head.UPDATES and total == frozen['token_layer_visits']
    WRITE(out/'routes.json',dict(name=name,completed=completed,token_layer_visits=total))
    return code


def compare(a,b):
    return dict(initial=a['initial']==b['initial'],observations=a['observations']==b['observations'],
        losses=[u['loss'] for u in a['updates']]==[u['loss'] for u in b['updates']],
        norms=[u['pre_clip_gradient_norm'] for u in a['updates']]==[u['pre_clip_gradient_norm'] for u in b['updates']],
        components={k:v==b['states'][k] for k,v in a['states'].items()})


def run(frozen):
    exits, arms = {}, {}
    for name in ARMS:
        if (OUT/'STOP').exists() or not idle():
            exits[name] = None
            break
        cmd = ['timeout','--kill-after=5s',f'{CAP}s',sys.executable,'-B','-u','-X','utf8','-m',
               'scripts.diag_p107_g4_policy_adaptive','worker',name]
        exits[name] = subprocess.run(cmd,cwd=head.ROOT).returncode
        print('P107_G4_POLICY_ADAPTIVE_EXIT',name,exits[name],flush=True)
        if exits[name] == 0:
            mode = name.rsplit('_',1)[1]
            arms[name] = dict(report=read(OUT/name/f'{mode}.json'),routes=read(OUT/name/'routes.json'))
    old = read(fixed.OUT/'report.json')['reports']['recompute']
    checks, against_fixed = {}, {}
    for policy in POLICIES:
        a,b = (arms.get(f'{policy}_{mode}') for mode in ('reference','recompute'))
        if a is not None and b is not None:
            checks[policy] = compare(a['report'],b['report'])
            checks[policy]['actual_routes'] = a['routes']['completed']==b['routes']['completed']
            observed = b['report']['observations']
            against_fixed[policy] = dict(same_initial=old['initial']==b['report']['initial'],
                same_source_state=old['states']['source']==b['report']['states']['source'],
                different_final_model=old['states']['model']!=b['report']['states']['model'],
                mask_differences=[i for i,(x,y) in enumerate(zip(old['observations'],observed,strict=True))
                                  if x['mask']!=y['mask']],
                prediction_differences=[i for i,(x,y) in enumerate(zip(old['observations'],observed,strict=True))
                                        if x['supervised_ids']!=y['supervised_ids']])
    returned = idle()
    same_sources = contract() == frozen
    WRITE(OUT/'report.json',dict(exits=exits,arms=arms,checks=checks,against_fixed=against_fixed,
                                gpu_returned=returned,sources_unchanged=same_sources))
    print('P107_G4_POLICY_ADAPTIVE_COMPLETE',checks,against_fixed,returned,flush=True)
    good = returned and same_sources and len(checks) == len(POLICIES)
    return 0 if good and all(all(all(x.values()) if isinstance(x,dict) else x for x in c.values())
                             for c in checks.values()) else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('prepare','run','worker'))
    parser.add_argument('arm',nargs='?',choices=ARMS)
    args = parser.parse_args()
    if (args.phase=='worker') != (args.arm is not None):
        parser.error('only a worker accepts an arm')
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if args.phase=='prepare' else '0')
    cutoff = head.warm.CUTOFF
    assert datetime.now(cutoff.tzinfo)+timedelta(seconds=len(ARMS)*(CAP+5)) < cutoff
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    current = contract()
    profile = OUT/'route_contract.json'
    if args.phase=='prepare':
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        WRITE(profile,current)
        print('P107_G4_POLICY_ADAPTIVE_READY',{k:[x['visits'] for x in v] for k,v in current['routes'].items()},
              current['token_layer_visits'],flush=True)
        return 0
    assert os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'
    assert current == read(profile)
    return worker(args.arm,current) if args.phase=='worker' else run(current)


if __name__=='__main__':
    sys.exit(main())
