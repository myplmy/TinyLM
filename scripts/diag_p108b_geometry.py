#!/usr/bin/env python3
"""Full14 actual single-layer atlas with frozen full-path predictions.

One original model, one fixed absolute norm panel, all14 physical layers.
Each variant is one global weight state over every question. The completed
168 auxiliary values are reused and never optimized here. Final-language
answers and official test answers are not consumed by this phase.
"""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import gc
import json
from pathlib import Path
import time
import traceback

import tinylm
import numpy as np
import torch

from scripts import diag_p108b_value_library as library
from scripts import p108b_solver as solver
from scripts import p108b_eval_data as eval_data
from scripts.p108b_tinylm import TinyAdapter,endpoint_transfer
from scripts import interactive_research_infer as manual
from scripts import diag_p108_weight_space as io
from scripts import p108_weight_space as metrics
from scripts.p106b_shards import ShardWriter

ROOT=Path(__file__).resolve().parents[1]
BASE=library.BASE
ORIGINAL_BUDGET=15.679170726429515
PLAN=library.PLAN
SOURCES=('scripts/diag_p108b_geometry.py','scripts/test_p108b_geometry.py',
         'scripts/p108b_tinylm.py','scripts/test_p108b_adapter.py',
         'scripts/p108b_solver.py','scripts/test_p108b_solver.py',
         'scripts/p108b_eval_data.py','scripts/test_p108b_eval_data.py',
         'scripts/p108_joint_write.py','scripts/p106b_shards.py')


def common_budget(weight_norms):
    if set(weight_norms)!=set(range(14)) or any(not np.isfinite(v) or v<=0 for v in weight_norms.values()):
        raise ValueError('all14 finite positive original weight norms required')
    lowest=.05*min(weight_norms.values())
    return ((ORIGINAL_BUDGET,'LEGACY_EXACT_ABSOLUTE_B0') if lowest>=ORIGINAL_BUDGET else
            (lowest*(1-1e-5),'COMMON_LOWER_5PCT_PANEL_NOT_LEGACY_MATCHED'))


def write_npz(path,**values):
    arrays={k:(v.detach().cpu().numpy() if isinstance(v,torch.Tensor) else np.asarray(v)) for k,v in values.items()}
    if any(a.dtype.kind not in 'fiub' or not np.isfinite(a).all() for a in arrays.values()):
        raise ValueError('only finite numeric, non-pickle arrays are allowed')
    if sum(a.nbytes for a in arrays.values())>18_000_000:
        raise ValueError('split arrays before the20MB file limit')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb')as stream:np.savez_compressed(stream,**arrays)
    if path.stat().st_size>=20_000_000:raise RuntimeError('NPZ result exceeds20MB')
    return dict(path=str(path.relative_to(ROOT)),sha256=manual.file_sha(path),bytes=path.stat().st_size)


def summaries(rows):
    return dict(all=metrics.summarize(rows),**{family:metrics.summarize([r for r in rows if r.get('family')==family])
                for family in ('target','other','protect','open')})


def select_lambda(records,baseline_correct):
    """Fit selects a layer for each lambda; separate DEV selects the lambda."""
    choices=[]
    for coefficient in (0.,.0625,.25):
        candidate=min(records,key=lambda r:(r['objective']['fit_ce']+coefficient*r['objective']['preserve_kl'],r['layer']))
        dev=candidate['dev'];nonprotect=dev['target']['exact']+dev['other']['exact']
        losses=len(set(baseline_correct)-set(candidate['dev_protected_correct_ids']))
        preference=(losses,-nonprotect,dev['all']['loop_indicators'],dev['all']['question_echoes'],
                    dev['all']['empty'],0 if coefficient==.0625 else 1 if coefficient==.25 else 2,candidate['layer'])
        choices.append(dict(kl_weight=coefficient,layer=candidate['layer'],dev_key=list(preference)))
    chosen=min(choices,key=lambda r:tuple(r['dev_key']))
    coefficient=chosen['kl_weight']
    order=sorted(records,key=lambda r:(r['objective']['fit_ce']+coefficient*r['objective']['preserve_kl'],r['layer']))
    return dict(chosen=chosen,choices=choices,fixed_layer_order=[r['layer'] for r in order],
                rule='FIT_OBJECTIVE_LAYER_THEN_DEV_PROTECTED_LOSS_NONPROTECT_EXACT_LOOPS_ECHO_EMPTY')


def prepare():
    lp=library.verify();candidates=library.load_candidates()
    if len(candidates)!=168:raise ValueError('complete168 frozen values are required')
    if (BASE/'geometry_profile.json').exists():raise FileExistsError('fresh geometry profile required')
    reports=[]
    for path in (BASE/'library').glob('report_*.json'):
        record=io.read_json(path)
        if record.get('complete_candidates')==168 and record.get('registered_core_unchanged') and record.get('cuda_allocated_after_bytes')==0:
            reports.append(path)
    if not reports:raise ValueError('successful same-source library cleanup required')
    data=io.read_json(BASE/'data.json');dev=eval_data.selection(data['rows']);final=eval_data.final_language()
    validation=eval_data.validate(dev,final,data['rows'])
    library.write_new(BASE/'select_dev.json',dict(role='SELECT_DEV_ONLY',rows=dev))
    library.write_new(BASE/'final_language.json',dict(role='FINAL_EVALUATION_ONLY_NOT_EDITOR_INPUT',rows=final))
    refs={str((BASE/'library_profile.json').relative_to(ROOT)):manual.file_sha(BASE/'library_profile.json')}
    for path in reports:refs[str(path.relative_to(ROOT))]=manual.file_sha(path)
    for fact,layer in lp['all_pairs']:
        source=(library.SOURCE/'actual' if [fact,layer]in lp['reused_pairs'] else BASE/'library')/f'{fact}_layer{layer}_fit.json'
        refs[str(source.relative_to(ROOT))]=manual.file_sha(source)
    old_manifest=io.read_json(library.SOURCE/'actual/answers_shards_manifest.json')
    refs[str((library.SOURCE/'actual/answers_shards_manifest.json').relative_to(ROOT))]=manual.file_sha(library.SOURCE/'actual/answers_shards_manifest.json')
    for spec in old_manifest['shards']:
        path=library.SOURCE/'actual'/spec['path'];refs[str(path.relative_to(ROOT))]=manual.file_sha(path)
    sources=dict(lp['sources']);sources.update({name:manual.file_sha(ROOT/name)for name in SOURCES})
    library.write_new(BASE/'geometry_profile.json',dict(schema='P108B_FULL14_ATLAS_V1',authority_directive=140,
        deadline=library.DEADLINE.isoformat(),model=lp['model'],origin=lp['source_origin'],
        library_profile_sha256=manual.file_sha(BASE/'library_profile.json'),sources=sources,references=refs,
        data_sha256=manual.file_sha(BASE/'data.json'),select_dev_sha256=manual.file_sha(BASE/'select_dev.json'),
        final_language_sha256=manual.file_sha(BASE/'final_language.json'),eval_validation=validation,
        initial_plan_sha256=manual.file_sha(ROOT/PLAN),absolute_legacy_budget=ORIGINAL_BUDGET,
        actual_absolute_norm_rtol=2e-5,proposal_rounding_margin=1e-6,relative_safety_cap=.05,
        root_kl_weight=.0625,lambda_candidates=[0.,.0625,.25],fd_epsilons=[.001,.003],
        max_phase_seconds=7200,max_new=64,body_optimizer_updates=0,value_optimizer_updates=0,
        training_draw_tokens=0,checkpoint_writes=0,final_answers_consumed=False,
        original_calibration_moment_fixed_for_policy_comparison=True,
        cost_estimate='14 global variants times164 cases; about20-50min, not a quality guarantee'))
    with (BASE/'geometry_initial_plan.md').open('xb')as stream:stream.write((ROOT/PLAN).read_bytes())
    print('[PREPARED] full14 actual atlas, select96/final192; final answers sealed',flush=True)


def verify():
    p=io.read_json(BASE/'geometry_profile.json');library.Budget().check()
    if p['authority_directive']!=140 or p['deadline']!=library.DEADLINE.isoformat():raise ValueError('authority differs')
    for name,sha in dict(p['sources'],**p['references']).items():
        if manual.file_sha(ROOT/name)!=sha:raise ValueError('pinned source/reference changed: '+name)
    for name,key in [('data.json','data_sha256'),('select_dev.json','select_dev_sha256'),
                     ('final_language.json','final_language_sha256'),('geometry_initial_plan.md','initial_plan_sha256')]:
        if manual.file_sha(BASE/name)!=p[key]:raise ValueError('sealed role/data/plan changed: '+name)
    return p


def old_baseline(rows):
    manifest=io.read_json(library.SOURCE/'actual/answers_shards_manifest.json');found={}
    for spec in manifest['shards']:
        for line in (library.SOURCE/'actual'/spec['path']).read_text().splitlines():
            record=json.loads(line)
            if record['variant']=='original':
                if record['id']in found:raise ValueError('duplicate original answer')
                found[record['id']]=record
    if set(found)!={r['id']for r in rows}:raise ValueError('complete original68 required')
    for row in rows:
        if any(found[row['id']].get(k)!=v for k,v in row.items()):raise ValueError('original exact prompt/target changed')
    return [dict(found[r['id']],reused_from=str(library.SOURCE.relative_to(ROOT)))for r in rows]


def run():
    p=verify();out=BASE/'geometry'
    if out.exists():raise FileExistsError('preserve every prior geometry attempt; use a new version for a change')
    out.mkdir()
    budget=library.Budget(p['max_phase_seconds']);started=time.monotonic();failure=None
    report=dict(schema=p['schema'],status='RUNNING',origin=p['origin'],layers=[],
        body_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0,
        final_answers_consumed=False,source_profile_sha256=manual.file_sha(BASE/'geometry_profile.json'))
    adapter=active=captured=moments=samples=proposals=gradients=module=None
    try:
        report['entry_resources']=library.resources()
        torch.set_num_threads(4);torch.manual_seed(1337)
        data=io.read_json(BASE/'data.json');legacy=data['rows'];fits=[r for r in legacy if r['split']=='fit']
        selection=io.read_json(BASE/'select_dev.json')
        if selection['role']!='SELECT_DEV_ONLY' or any(r['split']!='select_dev'for r in selection['rows']):
            raise ValueError('final evaluation cannot enter the selector')
        dev=selection['rows'];reused=old_baseline(legacy)
        values={(r['fact'],r['layer']):torch.tensor(r['value_delta'],dtype=torch.float32)for r in library.load_candidates()}
        with manual.selected_runtime(manual.resolve_model(p['model']))as active:
            adapter=TinyAdapter(active,fits,data['calibration_questions'],kl_weight=p['root_kl_weight'],budget=budget)
            torch.cuda.reset_peak_memory_stats()
            try:
                # One required original-generation canary; the other old68 answers are reused.
                probe=adapter.generate(legacy[0],variant='ORIGINAL_CANARY')
                if probe['generation']['generated_ids']!=reused[0]['generation']['generated_ids']:
                    raise RuntimeError('original greedy/EOT/source parity differs')
                captured=adapter.capture_fit()
                moments,moment_stats,samples=adapter.calibration_moments(return_samples=True)
                norms={i:float(w.double().norm())for i,w in adapter.original.items()}
                norm,policy=common_budget(norms);report.update(common_budget=norm,budget_policy=policy,weight_norms=norms)
                proposals={};realized={};proposal_stats={};packet_refs={}
                for layer in range(14):
                    budget.check()
                    residual=torch.stack([values[(r['fact'],layer)]for r in fits],dim=1).double()
                    e,stats=solver.solve_increment(captured['keys'][layer],residual,moments[layer],
                        torch.zeros_like(adapter.original[layer],dtype=torch.float64),norm,
                        rounding_margin=p['proposal_rounding_margin'])
                    after,physical=solver.physical_change(adapter.original[layer],adapter.original[layer],e)
                    proposals[layer]=e;realized[layer]=after.double()-adapter.original[layer].double()
                    proposal_stats[layer]=dict(local=stats,cpu_physical=physical,
                        old_budget_feasible=ORIGINAL_BUDGET<=.05*norms[layer],
                        base_weight_sha256=metrics.tensor_sha(adapter.original[layer]),after_weight_sha256=metrics.tensor_sha(after))
                    if abs(physical['net_norm']-norm)>p['actual_absolute_norm_rtol']*norm:
                        proposal_stats[layer]['norm_match_status']='SAME_BUDGET_ONLY'
                    else:proposal_stats[layer]['norm_match_status']='NET_MATCHED'
                    packet_refs[layer]=write_npz(out/f'layer{layer:02d}_packet.npz',requested=e,after=after,
                        fit_keys=captured['keys'][layer].float(),fit_values=captured['values'][layer].float())
                    write_npz(out/f'layer{layer:02d}_calibration.npz',keys=samples[layer])
                objective,gradients=adapter.objective(gradient=True,directions=realized)
                baseline_writer=ShardWriter(out,'baseline_answers',limit=3_000_000)
                for row in reused:baseline_writer.append(row)
                baseline_dev=[]
                for row in dev:
                    answer=adapter.generate(row,variant='ORIGINAL_DEV');baseline_dev.append(answer);baseline_writer.append(answer)
                baseline_manifest=baseline_writer.close(lineage=dict(origin=p['origin'],new_dev_only=True,legacy68_reused=True))
                baseline_protected=[r['id']for r in baseline_dev if r['protected']and r['exact']]
                baseline=dict(objective=objective,legacy=io.read_json(library.SOURCE/'actual/report.json').get('baseline'),
                              dev=summaries(baseline_dev),dev_protected_correct_ids=baseline_protected,
                              answers_manifest=baseline_manifest,origin=p['origin'])
                library.write_new(out/'baseline_report.json',baseline)
                write_npz(out/'baseline_endpoints.npz',prefix=captured['prefix_endpoint'].float(),answer=captured['answer_endpoint'].float())
                for layer in range(14):
                    budget.check();layer_out=out/f'layer{layer:02d}';writer=ShardWriter(layer_out,'answers',limit=3_000_000)
                    oracle=adapter.oracle_geometry(layer,values)
                    write_npz(out/f'layer{layer:02d}_oracle_endpoints.npz',prefix=oracle['prefix_endpoint'].float(),answer=oracle['answer_endpoint'].float())
                    write_npz(out/f'layer{layer:02d}_gradient.npz',gradient=gradients[layer].float())
                    fd=[]
                    for epsilon in p['fd_epsilons']:
                        with adapter.edit(layer,proposals[layer]*epsilon):plus=adapter.objective()
                        with adapter.edit(layer,proposals[layer]*(-epsilon)):minus=adapter.objective()
                        fd.append(dict(epsilon=epsilon,predicted_gain_from_central_difference=-(plus['J']-minus['J'])/(2*epsilon),
                                       plus=plus,minus=minus))
                    with adapter.edit(layer,proposals[layer])as receipt:
                        physical=adapter.modules[layer].weight.detach().cpu()
                        if metrics.tensor_sha(physical)!=proposal_stats[layer]['after_weight_sha256']:
                            raise RuntimeError('CPU predicted and actual CUDA physical write differ')
                        live_capture=adapter.capture_fit();actual=adapter.objective()
                        core=manual.state_fingerprint(active['model'])
                        legacy_answers=[];dev_answers=[]
                        for row in legacy:
                            answer=adapter.generate(row,variant=f'LAYER{layer}_GLOBAL');legacy_answers.append(answer);writer.append(answer)
                        for row in dev:
                            answer=adapter.generate(row,variant=f'LAYER{layer}_DEV');dev_answers.append(answer);writer.append(answer)
                        record=dict(layer=layer,status='GLOBAL_SINGLE_LAYER_ACTUAL_COMPLETE',budget=norm,
                            packet=packet_refs[layer],geometry=proposal_stats[layer],receipt=receipt,
                            after_core_sha256=core,objective=actual,baseline_objective=objective,
                            predicted_gain=solver.predicted_gain(gradients[layer],realized[layer]),
                            actual_gain=objective['J']-actual['J'],
                            transfer=endpoint_transfer(captured,oracle,live_capture),finite_difference=fd,
                            legacy=metrics.summarize(legacy_answers),dev=summaries(dev_answers),
                            dev_protected_correct_ids=[r['id']for r in dev_answers if r['protected']and r['exact']],
                            legacy_protected_correct_ids=[r['id']for r in legacy_answers if r['protected']and r['exact']],
                            base_optimizer_updates=0,value_optimizer_updates=0,counts=dict(adapter.counts))
                    record['answers_manifest']=writer.close(lineage=dict(after_core_sha256=core,one_global_model=True,layer=layer))
                    library.write_new(layer_out/'report.json',record);report['layers'].append(record)
                    print('[ATLAS_LAYER] '+json.dumps(dict(layer=layer,legacy_exact=record['legacy']['exact'],
                        dev_exact=record['dev']['all']['exact'],predicted_gain=record['predicted_gain'],
                        actual_gain=record['actual_gain'],norm=record['geometry']['cpu_physical']['net_norm'])),flush=True)
                report['selection']=select_lambda(report['layers'],baseline_protected)
                report['baseline']=baseline;report['counts']=dict(adapter.counts)
                report['registered_core_unchanged']=manual.state_fingerprint(active['model'])==active['core_sha256']
                if not report['registered_core_unchanged']:raise RuntimeError('atlas did not restore original model')
                report['peak_allocated_mib']=torch.cuda.max_memory_allocated()/2**20
                report['peak_reserved_mib']=torch.cuda.max_memory_reserved()/2**20
                report['peak_scope']='AFTER_MODEL_LOAD_THROUGH_ATLAS_NOT_LOAD_CONSTRUCTION'
                report['status']='FULL14_ACTUAL_ATLAS_COMPLETE_QUALITY_REVIEW_SEPARATE'
            finally:
                if adapter is not None:adapter.close()
    except BaseException as exc:
        failure=exc;report.update(status='PAUSED_BUDGET'if isinstance(exc,TimeoutError)else'TECHNICAL_ERROR',
            error=repr(exc),traceback=traceback.format_exc())
    finally:
        active=adapter=module=None;gc.collect()
        cleanup_error=library.cleanup(report)
        if failure is None:failure=cleanup_error
        report['wall_seconds']=time.monotonic()-started
        library.write_new(out/'report.json',report)
        print('[ATLAS_END] '+json.dumps(dict(status=report['status'],layers=len(report['layers']),
            wall_seconds=report['wall_seconds'],cuda_allocated=report.get('cuda_allocated_after_bytes'),
            cuda_reserved=report.get('cuda_reserved_after_bytes'))),flush=True)
    if failure is not None:raise failure


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=['prepare','actual','check'])
    args=parser.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='check':verify();print('[CHECK] frozen atlas source/data/roles verified; GPU NOT_RUN')
    else:run()


if __name__=='__main__':main()
