#!/usr/bin/env python3
"""Frozen single/repeated/distributed physical-edit comparison.

No body optimizer, auxiliary optimization, new dataset, or final-test access.
All accepted writes are recorded as ordered FP32 packets and rolled back.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from dataclasses import asdict
import gc
import json
from pathlib import Path
import time
import traceback

import tinylm
import numpy as np
import torch

from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_value_library as library
from scripts import p108b_policy as policy
from scripts import p108b_solver as solver
from scripts.p108b_tinylm import TinyAdapter
from scripts import interactive_research_infer as manual
from scripts import diag_p108_weight_space as io
from scripts import p108_weight_space as metrics
from scripts import p108_joint_write as covariance_owner
from scripts.p106b_shards import ShardWriter

ROOT=atlas.ROOT
BASE=atlas.BASE
OUT=BASE/'policies_v1'
SOURCES=('scripts/diag_p108b_policy.py','scripts/p108b_policy.py','scripts/test_p108b_policy.py')


def read_answers(directory,manifest):
    rows=[]
    for shard in manifest['shards']:
        path=directory/shard['path']
        if manual.file_sha(path)!=shard['sha256']:raise ValueError('answer shard changed')
        rows.extend(json.loads(line)for line in path.read_text(encoding='utf-8').splitlines())
    if len(rows)!=manifest['rows']:raise ValueError('answer row count differs')
    return rows


def npz_tensors(path):
    with np.load(path,allow_pickle=False)as payload:
        return {key:torch.from_numpy(payload[key].copy())for key in payload.files}


def net_stats(adapter,path_length):
    ds=adapter.displacement()
    return dict(net_norm=sum(float(d.square().sum())for d in ds.values())**.5,
        path_norm=path_length,changed_entries=sum(int(d.ne(0).sum())for d in ds.values()),
        unique_layers=[i for i,d in ds.items()if bool(d.ne(0).any())],
        net_layer_norms={i:float(d.norm())for i,d in ds.items()if bool(d.ne(0).any())})


def prepare():
    parent=atlas.verify();report=io.read_json(BASE/'geometry/report.json')
    if (report['status']!='FULL14_ACTUAL_ATLAS_COMPLETE_QUALITY_REVIEW_SEPARATE' or
            len(report['layers'])!=14 or not report['registered_core_unchanged'] or
            report['cuda_allocated_after_bytes'] or report['cuda_reserved_after_bytes']):
        raise ValueError('closed strict14-layer atlas required')
    records=[];refs={};baseline=read_answers(BASE/'geometry',report['baseline']['answers_manifest'])
    for record in report['layers']:
        directory=BASE/f"geometry/layer{record['layer']:02d}"
        answers=read_answers(directory,record['answers_manifest'])
        record['dev_corrected']=policy.dev_summary([r for r in answers if r['split']=='select_dev'])
        records.append(record)
    baseline_dev=policy.dev_summary([r for r in baseline if r['split']=='select_dev'])
    selected=policy.choose_selection(records,baseline_dev['protected_correct_ids'])
    # Explicitly enumerate only this completed experiment, never protected data.
    for path in sorted((BASE/'geometry').rglob('*')):
        if path.is_file():refs[str(path.relative_to(ROOT))]=manual.file_sha(path)
    sources=dict(parent['sources']);sources.update({name:manual.file_sha(ROOT/name)for name in SOURCES})
    profile=dict(schema='P108B_PROGRESSIVE_NET_POLICY_V1',authority_directive=140,
        deadline=library.DEADLINE.isoformat(),model=parent['model'],origin=parent['origin'],
        sources=sources,references=refs,selection=selected,previous_selection=report['selection'],
        selection_revision='exclude correct requested repetition; reward protection gains; before FINAL',
        common_budget=report['common_budget'],legacy_budget=parent['absolute_legacy_budget'],
        budget_rtol=parent['actual_absolute_norm_rtol'],rounding_margin=parent['proposal_rounding_margin'],
        base_data_sha256=manual.file_sha(BASE/'data.json'),dev_sha256=manual.file_sha(BASE/'select_dev.json'),
        geometry_profile_sha256=manual.file_sha(BASE/'geometry_profile.json'),
        primary=[asdict(s)for s in policy.primary_policies()],diagnostic=[asdict(s)for s in policy.diagnostic_policies()],
        adaptive_shortlist=3,line_search_alphas=[1.,.5,.25],max_new=64,max_phase_seconds=14400,
        fit_count=24,legacy_count=68,selection_count=96,final_answers_consumed=False,
        no_new_protected_errors_in_adaptive_trials=True,body_optimizer_updates=0,value_optimizer_updates=0,
        final_objective='mean FIT CE plus chosen lambda times128 original-prompt KL',
        adaptive_choice='actual common objective after top3 predicted gains and3 alphas; zero/no-edit retained',
        fixed_control='unconditional alpha1; measured damage retained, never adopted automatically',
        residual='original native value plus frozen oracle delta minus current native value',
        support='fixed per-layer support on first visit; no union growth on revisits',
        initial_plan_sha256=manual.file_sha(ROOT/library.PLAN))
    library.write_new(BASE/'policy_profile_v1.json',profile)
    with (BASE/'policy_initial_plan_v1.md').open('xb')as stream:stream.write((ROOT/library.PLAN).read_bytes())
    print('[POLICY_PREPARED] '+json.dumps(selected),flush=True)


def verify():
    atlas.verify();p=io.read_json(BASE/'policy_profile_v1.json');library.Budget().check()
    if p['authority_directive']!=140 or p['deadline']!=library.DEADLINE.isoformat():raise ValueError('authority differs')
    for name,sha in dict(p['sources'],**p['references']).items():
        if manual.file_sha(ROOT/name)!=sha:raise ValueError('pinned policy input changed: '+name)
    for name,key in [('data.json','base_data_sha256'),('select_dev.json','dev_sha256'),
                     ('geometry_profile.json','geometry_profile_sha256'),('policy_initial_plan_v1.md','initial_plan_sha256')]:
        if manual.file_sha(BASE/name)!=p[key]:raise ValueError('sealed policy role/data/plan changed: '+name)
    return p


def propose(adapter,spec,j,layer,cap,moments,base_values,values,gradients,supports,p,capture):
    current=adapter.modules[layer].weight.detach().cpu().clone()
    ds=adapter.displacement()
    if spec.budget_mode=='path':
        layer_cap=cap;displacement=torch.zeros_like(ds[layer])
    else:
        layer_cap=solver.remaining_layer_budget(cap,[d for i,d in ds.items()if i!=layer])
        displacement=ds[layer]
    target=base_values[layer]+torch.stack([values[(r['fact'],layer)]for r in adapter.fits],dim=1).double()
    residual=target-capture['values'][layer]
    if spec.residual_share:residual=residual/(spec.rounds-j+1)
    full,full_stats=solver.solve_increment(capture['keys'][layer],residual,moments[layer],displacement,layer_cap,
                                         rounding_margin=p['rounding_margin'])
    if layer not in supports:
        mask,support_stats=policy.support(spec,full,gradients[layer],moments[layer])
    else:
        mask,support_stats=supports[layer]
        support_stats=dict(support_stats,reused_support=True)
    if mask is None:increment,stats=full,full_stats
    else:
        increment,stats=solver.solve_increment(capture['keys'][layer],residual,moments[layer],displacement,
            layer_cap,support=mask,rounding_margin=p['rounding_margin'])
    after,physical=solver.physical_change(adapter.original[layer],current,increment)
    step=after.double()-current.double()
    prediction=solver.predicted_gain(gradients[layer],step)
    return dict(layer=layer,increment=increment,after=after,mask=mask,support_stats=support_stats,
        stats=dict(local=stats,physical=physical,predicted_gain=prediction,layer_cap=layer_cap,
                   remaining_residual_share=1/(spec.rounds-j+1)if spec.residual_share else 1.,
                   support=support_stats,previous_weight_sha256=metrics.tensor_sha(current)),
        score=prediction/max(physical['step_norm'],1e-30))


def actual_trial(adapter,candidate,alpha,before,protected,baseline_protected,p,cap,path_length,spec):
    layer=candidate['layer'];delta=candidate['increment']*alpha
    current=adapter.modules[layer].weight.detach().cpu().clone()
    expected,physical=solver.physical_change(adapter.original[layer],current,delta)
    prediction=solver.predicted_gain(candidate['gradient'],expected.double()-current.double())
    with adapter.edit(layer,delta):
        observed=adapter.modules[layer].weight.detach().cpu()
        if not torch.equal(observed,expected):raise RuntimeError('CPU/GPU physical write mismatch')
        objective=adapter.objective()
        guard=[adapter.generate(r,max_new=p['max_new'],variant='TRIAL_PROTECT')for r in protected]
        correct={r['id']for r in guard if r['exact']}
        physical_all=net_stats(adapter,path_length+physical['step_norm'])
    limit=cap if spec.budget_mode!='path' else p['common_budget']
    if physical_all['net_norm']>limit*(1+p['budget_rtol']):raise RuntimeError('actual net budget exceeded')
    return dict(layer=layer,alpha=alpha,objective=objective,actual_gain=before['J']-objective['J'],
        predicted_gain=prediction,physical=physical,physical_all=physical_all,
        protected_correct_ids=sorted(correct),lost_protected_ids=sorted(baseline_protected-correct),
        protected_answers=guard,after_weight_sha256=metrics.tensor_sha(expected))


def run(names):
    p=verify();all_specs={s['name']:policy.Policy(**s)for s in p['primary']+p['diagnostic']}
    if not names or len(names)!=len(set(names)) or any(n not in all_specs for n in names):raise ValueError('explicit unique registered policies required')
    OUT.mkdir(parents=True,exist_ok=True)
    if any((OUT/n).exists()for n in names):raise FileExistsError('prior policy attempt preserved; never overwrite')
    budget=library.Budget(p['max_phase_seconds']);started=time.monotonic();adapter=active=None;failure=None
    report=dict(schema=p['schema'],status='RUNNING',policy_names=names,arms=[],origin=p['origin'],
        body_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0,final_answers_consumed=False,
        source_profile_sha256=manual.file_sha(BASE/'policy_profile_v1.json'))
    try:
        report['entry_resources']=library.resources();torch.set_num_threads(4);torch.manual_seed(1337)
        data=io.read_json(BASE/'data.json');legacy=data['rows'];fits=[r for r in legacy if r['split']=='fit']
        dev=io.read_json(BASE/'select_dev.json')['rows'];protected=[r for r in legacy if r['protected']]
        if len(protected)!=16:raise ValueError('original16 protection cases required')
        parent=io.read_json(BASE/'geometry/report.json')
        original_rows=read_answers(BASE/'geometry',parent['baseline']['answers_manifest'])
        baseline_protected={r['id']for r in original_rows if r['split']!='select_dev'and r['protected']and r['exact']}
        moments={};base_values={};base_gradients={}
        for layer in range(14):
            values_i=npz_tensors(BASE/f'geometry/layer{layer:02d}_packet.npz');base_values[layer]=values_i['fit_values'].double()
            sample=npz_tensors(BASE/f'geometry/layer{layer:02d}_calibration.npz')['keys']
            moments[layer],_=covariance_owner.covariance(sample,ridge_ratio=.01)
            base_gradients[layer]=npz_tensors(BASE/f'geometry/layer{layer:02d}_gradient.npz')['gradient'].double()
        values={(r['fact'],r['layer']):torch.tensor(r['value_delta'],dtype=torch.float32)for r in library.load_candidates()}
        with manual.selected_runtime(manual.resolve_model(p['model']))as active:
            adapter=TinyAdapter(active,fits,data['calibration_questions'],kl_weight=p['selection']['chosen']['kl_weight'],budget=budget)
            torch.cuda.reset_peak_memory_stats()
            try:
                baseline=adapter.objective()
                expected=parent['baseline']['objective'];chosen_lambda=p['selection']['chosen']['kl_weight']
                expected_j=expected['fit_ce']+chosen_lambda*expected['preserve_kl']
                if abs(baseline['J']-expected_j)>1e-7:raise RuntimeError('closed atlas objective replay differs')
                # Exact full-budget SINGLE1 is already a closed global atlas arm.
                for name in names:
                    budget.check();spec=all_specs[name];directory=OUT/name;directory.mkdir()
                    if name=='SINGLE1':
                        layer=p['selection']['chosen']['layer'];source=parent['layers'][layer]
                        reused=dict(schema=p['schema'],name=name,spec=asdict(spec),status='REUSED_EXACT_ATLAS_ARM',
                            source_report=str((BASE/f'geometry/layer{layer:02d}/report.json').relative_to(ROOT)),
                            source_sha256=manual.file_sha(BASE/f'geometry/layer{layer:02d}/report.json'),
                            packet=source['packet'],objective=source['objective'],legacy=source['legacy'],dev=source['dev'],
                            actual_core_sha256=source['after_core_sha256'],rounds_executed=1,
                            physical=dict(net_norm=source['geometry']['cpu_physical']['net_norm'],
                                path_norm=source['geometry']['cpu_physical']['step_norm'],unique_layers=[layer]),
                            counts_new=dict(model_forwards=0,generated_calls=0),one_global_model=True)
                        library.write_new(directory/'report.json',reused);report['arms'].append(reused)
                        print('[POLICY_REUSED] '+name,flush=True);continue
                    begin=time.monotonic();path_length=0.;visited=[];supports={};rounds=[];packets=[];stop=None
                    required_protected=set(baseline_protected)
                    counts_before=dict(adapter.counts)
                    with ExitStack()as accepted:
                        before=baseline
                        for j in range(1,spec.rounds+1):
                            budget.check();cap=policy.budget_limit(spec,j,p['common_budget'])
                            if j==1 and chosen_lambda==parent['baseline']['objective']['kl_weight']:gradients=base_gradients
                            else:before,gradients=adapter.objective(gradient=True)
                            eligible=policy.eligible_layers(spec,j,best_layer=p['selection']['chosen']['layer'],
                                fixed_order=p['selection']['fixed_layer_order'],visited=visited)
                            candidates=[];rejections=[];capture=adapter.capture_fit()
                            for layer in eligible:
                                try:
                                    candidate=propose(adapter,spec,j,layer,cap,moments,base_values,values,gradients,supports,p,capture)
                                    candidate['gradient']=gradients[layer];candidates.append(candidate)
                                except ValueError as error:
                                    if 'no budget remains'not in str(error):raise
                                    rejections.append(dict(layer=layer,reason=str(error)))
                            candidates.sort(key=lambda c:(-c['score'],c['layer']))
                            scoreboard=[dict(layer=c['layer'],score=c['score'],**c['stats'])for c in candidates]
                            adaptive=spec.layer_rule.startswith('adaptive')
                            trials=[];chosen=None;resolution=0.
                            if adaptive:
                                replay=adapter.objective();resolution=max(abs(before['J']-replay['J'])*2,1e-10)
                                for c in candidates[:p['adaptive_shortlist']]:
                                    for alpha in p['line_search_alphas']:
                                        trial=actual_trial(adapter,c,alpha,before,protected,required_protected,p,cap,path_length,spec)
                                        trials.append(trial)
                                        if not trial['lost_protected_ids']and trial['actual_gain']>resolution:
                                            key=(trial['objective']['J'],trial['physical']['step_norm'],trial['layer'],-trial['alpha'])
                                            if chosen is None or key<chosen[0]:chosen=(key,c,trial)
                            elif candidates:
                                c=candidates[0]
                                trial=actual_trial(adapter,c,1.,before,protected,required_protected,p,cap,path_length,spec)
                                trials.append(trial);chosen=((trial['objective']['J'],),c,trial)
                            if chosen is None:
                                stop='NO_FEASIBLE_NONDESTRUCTIVE_IMPROVEMENT'if adaptive else'NO_REMAINING_BUDGET'
                                rounds.append(dict(round=j,cap=cap,before=before,candidates=scoreboard,rejections=rejections,
                                    trials=trials,status=stop,numerical_resolution=resolution));break
                            _,candidate,trial=chosen;layer=candidate['layer'];delta=candidate['increment']*trial['alpha']
                            accepted.enter_context(adapter.edit(layer,delta))
                            actual=adapter.modules[layer].weight.detach().cpu().clone()
                            if metrics.tensor_sha(actual)!=trial['after_weight_sha256']:
                                raise RuntimeError('accepted write differs from its tested packet')
                            path_length+=trial['physical']['step_norm'];visited.append(layer)
                            supports.setdefault(layer,(candidate['mask'],candidate['support_stats']))
                            if adaptive:required_protected.update(trial['protected_correct_ids'])
                            packet=atlas.write_npz(directory/f'step{j:02d}_layer{layer:02d}.npz',requested=delta,after=actual,
                                **({'mask':candidate['mask']}if candidate['mask']is not None else{}))
                            packet.update(layer=layer,round=j,before_weight_sha256=candidate['stats']['previous_weight_sha256'],
                                after_weight_sha256=metrics.tensor_sha(actual),alpha=trial['alpha'])
                            packets.append(packet)
                            per_round=[adapter.generate(r,max_new=p['max_new'],variant=name+f':ROUND{j}')for r in fits]
                            retention=dict(correct_ids=[r['id']for r in per_round if r['exact']],items=len(per_round),
                                lost_previous_ids=sorted(set(rounds[-1]['retention']['correct_ids'])-{r['id']for r in per_round if r['exact']})if rounds and 'retention'in rounds[-1]else[])
                            record=dict(round=j,cap=cap,layer=layer,alpha=trial['alpha'],before=before,after=trial['objective'],
                                candidates=scoreboard,rejections=rejections,trials=trials,retention=retention,
                                fit_answers=per_round,physical=net_stats(adapter,path_length),numerical_resolution=resolution,
                                chosen_predicted_gain=trial['predicted_gain'],chosen_actual_gain=trial['actual_gain'],
                                selection_rule='best tested actual J among top3 gain/norm candidates with alpha1/.5/.25 and protection guard'if adaptive else'fixed source order and unconditional alpha1')
                            rounds.append(record);before=trial['objective']
                            print('[POLICY_ROUND] '+json.dumps(dict(name=name,round=j,layer=layer,alpha=trial['alpha'],
                                predicted_gain=trial['predicted_gain'],actual_gain=trial['actual_gain'],net=record['physical']['net_norm'])),flush=True)
                        writer=ShardWriter(directory,'answers',limit=3_000_000);answers=[]
                        for row in legacy+dev:
                            a=adapter.generate(row,max_new=p['max_new'],variant=name);answers.append(a);writer.append(a)
                        core=manual.state_fingerprint(active['model']);physical=net_stats(adapter,path_length)
                        if physical['net_norm']>p['common_budget']*(1+p['budget_rtol']):raise RuntimeError('final physical budget exceeded')
                        arm=dict(schema=p['schema'],name=name,spec=asdict(spec),status=stop or'POLICY_COMPLETE_QUALITY_REVIEW_SEPARATE',
                            rounds=rounds,rounds_executed=len(packets),packets=packets,physical=physical,
                            actual_core_sha256=core,objective=adapter.objective(),one_global_model=True,
                            legacy=metrics.summarize(answers[:len(legacy)]),dev=atlas.summaries(answers[len(legacy):]),
                            dev_corrected=policy.dev_summary(answers[len(legacy):]),
                            legacy_protected_correct_ids=[r['id']for r in answers[:len(legacy)]if r['protected']and r['exact']],
                            lost_protected_ids=sorted(baseline_protected-{r['id']for r in answers[:len(legacy)]if r['protected']and r['exact']}),
                            match_status='NET_MATCHED'if abs(physical['net_norm']-p['common_budget'])<=p['budget_rtol']*p['common_budget']else'SAME_BUDGET_ONLY',
                            wall_seconds=time.monotonic()-begin,counts_new={k:adapter.counts[k]-counts_before[k]for k in adapter.counts})
                        arm['answers_manifest']=writer.close(lineage=dict(core_sha256=core,one_global_model=True,policy=name))
                    if manual.state_fingerprint(active['model'])!=active['core_sha256']:raise RuntimeError('policy rollback differs')
                    arm['original_restored']=True;library.write_new(directory/'report.json',arm)
                    report['arms'].append(dict(name=name,status=arm['status'],physical=physical,objective=arm['objective'],
                        legacy=arm['legacy'],dev_corrected=arm['dev_corrected'],report_sha256=manual.file_sha(directory/'report.json')))
                    print('[POLICY_END] '+json.dumps(report['arms'][-1]),flush=True)
                report['registered_core_unchanged']=manual.state_fingerprint(active['model'])==active['core_sha256']
                report['counts']=dict(adapter.counts);report['peak_allocated_mib']=torch.cuda.max_memory_allocated()/2**20
                report['peak_reserved_mib']=torch.cuda.max_memory_reserved()/2**20
                report['peak_scope']='after load, policy optimization and answer generation; not device total'
            finally:
                if adapter is not None:adapter.close();adapter=None
    except BaseException as error:
        failure=error;report.update(status='ERROR',error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc())
    finally:
        adapter=active=None;gc.collect();cleanup_error=library.cleanup(report)
        if failure is None:failure=cleanup_error
        report['wall_seconds']=time.monotonic()-started
        if failure is None:
            report['status']='POLICY_BATCH_COMPLETE_QUALITY_REVIEW_SEPARATE'
        library.write_new(OUT/('batch_'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'.json'),report)
        print('[POLICY_BATCH_END] '+json.dumps({k:report.get(k)for k in ('status','wall_seconds','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved policy failure')from failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','actual'])
    parser.add_argument('--arms',nargs='+');args=parser.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='check':verify();print('[POLICY_CHECK] pinned sources/data/authority; no model run')
    else:run(args.arms)


if __name__=='__main__':main()
