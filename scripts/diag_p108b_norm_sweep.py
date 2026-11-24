#!/usr/bin/env python3
"""Afternoon amplitude control; all morning sources and reports stay frozen."""
import argparse
import gc
import json
from pathlib import Path
import time
import traceback
import torch
from scripts import p108b_norm_sweep as sweep
from scripts import p108b_target_values as field
from scripts import p108b_target_protection as capped
from scripts import diag_p108b_target_protection as morning
from scripts import diag_p108b_target_values as values
from scripts import diag_p108b_target_write as target_io
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_value_library as library
from scripts import diag_p108b_policy as existing
from scripts import p108b_policy as devmetrics
from scripts import p108b_solver as solver
from scripts import p108_weight_space as metrics
from scripts.p108b_tinylm import TinyAdapter
from scripts import interactive_research_infer as manual
from scripts.p106b_shards import ShardWriter

ROOT = atlas.ROOT
SOURCE = atlas.BASE
BASE = ROOT / 'test_result/evidence/p108b_layer_transfer_v3_s1337'
PROFILE = BASE / 'norm_profile_v1.json'
INITIAL = BASE / 'norm_initial_plan_v1.md'
OUT = BASE / 'norm_sweep_v1'
CODE = ('scripts/p108b_norm_sweep.py', 'scripts/test_p108b_norm_sweep.py',
        'scripts/diag_p108b_norm_sweep.py')
PARENT_PROFILES = ('geometry_profile.json', 'target_values_profile_v1.json',
                   'target_write_profile_v2.json', 'target_protection_profile_v1.json')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def reference_set():
    refs = {}
    for name in PARENT_PROFILES:
        path = SOURCE / name
        refs[str(path.relative_to(ROOT))] = manual.file_sha(path)
        parent = read(path)
        for source, expected in parent['sources'].items():
            if manual.file_sha(ROOT / source) != expected:
                raise ValueError('morning source changed: ' + source)
            refs[source] = expected
    for name in ('data.json', 'select_dev.json', 'geometry/report.json',
                 'geometry/layer13_gradient.npz', 'target_protection_v1/report.json',
                 'target_protection_v1/protected_keys.npz', 'target_values_v1/values_complete.json'):
        refs[str((SOURCE/name).relative_to(ROOT))] = manual.file_sha(SOURCE/name)
    for path in sorted((SOURCE/'target_values_v1/values').glob('*_layer*.json')):
        refs[str(path.relative_to(ROOT))] = manual.file_sha(path)
    for mode in field.MODES:
        for protection in ('NONE', 'NORMAL7_PREFIX'):
            directory = SOURCE/'target_protection_v1'/(mode+'_'+protection)
            parent = read(directory/'report.json')
            for path in [directory/'report.json', ROOT/parent['packet']['path']]:
                refs[str(path.relative_to(ROOT))] = manual.file_sha(path)
            for shard in parent['answers_manifest']['shards']:
                path = directory/shard['path']
                if manual.file_sha(path) != shard['sha256']:
                    raise ValueError('closed morning raw answer changed')
                refs[str(path.relative_to(ROOT))] = shard['sha256']
    geometry = read(SOURCE/'geometry/report.json')
    for shard in geometry['baseline']['answers_manifest']['shards']:
        path = SOURCE/'geometry'/shard['path']
        if manual.file_sha(path) != shard['sha256']:
            raise ValueError('original answer shard changed')
        refs[str(path.relative_to(ROOT))] = shard['sha256']
    return refs


def prepare():
    sweep.Budget().check()
    if BASE.exists():raise FileExistsError('fresh afternoon namespace required')
    parent = read(values.PROFILE)
    records = target_io.value_records(parent)
    closed = read(SOURCE/'target_protection_v1/report.json')
    if (len(records) != 48 or not closed['original_core_restored'] or
            closed['cuda_allocated_after_bytes'] or closed['cuda_reserved_after_bytes']):
        raise ValueError('closed morning values/protection/cleanup required')
    refs = reference_set()
    library.write_new(PROFILE, dict(schema='P108B_PROTECTED_NORM_SWEEP_V1', authority_directive=141,
        authority_end=sweep.AUTHORITY_END.isoformat(), cleanup_seconds=sweep.CLEANUP_SECONDS,
        parent_model=parent['model'], origin=parent['origin'], sources={name:manual.file_sha(ROOT/name) for name in CODE},
        references=refs, layer=13, modes=list(field.MODES), signals=[.5, 1., 2.],
        unprotected_control='MATCH_PROTECTED_FULL_SOLUTION_NET', rank_rtol=1e-8,
        old_common_norm=13.8821193483393, budget_rtol=2e-5, max_new=64, max_seconds=1800,
        expected_new_states=8, expected_new_generated_answers=1315,
        body_optimizer_updates=0, auxiliary_optimizer_updates=0, checkpoint_writes=0,
        source_values_checked=48, source_values_used=24, final_or_official_inputs=False,
        initial_plan_sha256=manual.file_sha(ROOT/library.PLAN),
        selection_rule='OLD7_LOSS_DEV_NONPROTECT_EXACT_EMPTY_LOOP_ECHO_ACTUAL_NORM'))
    with INITIAL.open('xb') as stream:stream.write((ROOT/library.PLAN).read_bytes())
    print('[NORM_PREPARED] new afternoon deadline;8 new states;morning values/answers reused', flush=True)


def verify():
    sweep.Budget().check()
    p = read(PROFILE)
    if (p['authority_directive'] != 141 or p['authority_end'] != sweep.AUTHORITY_END.isoformat() or
            p['initial_plan_sha256'] != manual.file_sha(INITIAL)):
        raise ValueError('current afternoon authority and initial plan required')
    for name, expected in dict(p['references'], **p['sources']).items():
        if manual.file_sha(ROOT/name) != expected:
            raise ValueError('frozen source/input changed: ' + name)
    parent = read(values.PROFILE)
    return p, parent, target_io.value_records(parent)


def old_candidate(mode):
    directory = SOURCE/'target_protection_v1'/(mode+'_NORMAL7_PREFIX')
    record = read(directory/'report.json')
    return directory, record


def actual():
    p, parent, records = verify()
    resources = library.resources()
    budget = sweep.Budget(p['max_seconds'])
    if OUT.exists():raise FileExistsError('preserve previous afternoon attempt')
    OUT.mkdir();started = time.monotonic();torch.set_num_threads(4)
    report = dict(schema=p['schema'], status='STARTED', arms=[], reused=[], entry_resources=resources,
                  body_optimizer_updates=0, auxiliary_optimizer_updates=0, checkpoint_writes=0,
                  final_or_official_inputs_consumed=False, source_profile_sha256=manual.file_sha(PROFILE))
    active = adapter = module = None;failure = None
    try:
        data = read(SOURCE/'data.json');fits = [r for r in data['rows'] if r['split']=='fit']
        dev = read(SOURCE/'select_dev.json')['rows']
        geometry = read(SOURCE/'geometry/report.json')
        baseline = existing.read_answers(SOURCE/'geometry', geometry['baseline']['answers_manifest'])
        normal_rows = [r for r in baseline if r['split']!='select_dev' and r['protected'] and r['exact']]
        protected_ids = {r['id'] for r in normal_rows}
        if len(protected_ids)!=7 or any(r['family']!='copy' for r in normal_rows):
            raise ValueError('exact original-correct seven copy rows required')
        with manual.selected_runtime(manual.resolve_model(parent['model'])) as active:
            adapter = TinyAdapter(active, fits, data['calibration_questions'],
                                  kl_weight=parent['optimizer']['kl_weight'], budget=budget)
            try:
                if manual.state_fingerprint(active['model'])!=p['origin']['core_sha256']:
                    raise RuntimeError('original full model core differs')
                canary = adapter.generate(data['rows'][0], variant='ORIGINAL_CANARY')
                expected = next(r for r in baseline if r['id']==canary['id'])
                if canary['generation']['generated_ids']!=expected['generation']['generated_ids']:
                    raise RuntimeError('original full greedy generation differs')
                report['baseline_objective'] = before = adapter.objective()
                if abs(before['J']-geometry['baseline']['objective']['J'])>1e-6:
                    raise RuntimeError('same original objective required')
                normal = existing.npz_tensors(SOURCE/'target_protection_v1/protected_keys.npz')['keys'].double()
                keys, horizons = target_io.target_keys(adapter, p['layer'])
                gradient = existing.npz_tensors(SOURCE/'geometry/layer13_gradient.npz')['gradient']
                module = adapter.modules[p['layer']]
                for mode in p['modes']:
                    ks=[];rs=[]
                    for row in fits:
                        target=torch.tensor(records[(mode, p['layer'], row['fact'])]['target_values'],dtype=torch.float32)
                        k,r=field.question_columns(keys[row['id']],target);ks.append(k);rs.append(r)
                    k=torch.cat(ks,dim=1);r=torch.cat(rs,dim=1)
                    full, stats = sweep.full_solution(k,r,normal,rank_rtol=p['rank_rtol'])
                    unprotected, other_stats = sweep.full_solution(k,r,normal,protect=False,rank_rtol=p['rank_rtol'])
                    atlas.write_npz(OUT/(mode+'_full_solution.npz'),full=full,weighted_keys=k,weighted_values=r)
                    atlas.write_npz(OUT/(mode+'_unprotected_solution.npz'),full=unprotected)
                    directory, previous = old_candidate(mode)
                    stored=existing.npz_tensors(ROOT/previous['packet']['path'])
                    recalculated,_=capped.candidate(k,r,normal,p['old_common_norm'],protect=True,rank_rtol=p['rank_rtol'])
                    if not torch.equal(stored['requested'],recalculated):
                        raise RuntimeError('same morning cap does not exactly reproduce its requested matrix')
                    with adapter.edit(p['layer'],stored['requested']):
                        if manual.state_fingerprint(active['model'])!=previous['edited_core_sha256']:
                            raise RuntimeError('reused cap full model core differs')
                        old_answers=existing.read_answers(directory,previous['answers_manifest'])
                        answer=adapter.generate(old_answers[0],variant=mode+'_OLD_CAP_CANARY')
                        if answer['generation']['generated_ids']!=old_answers[0]['generation']['generated_ids']:
                            raise RuntimeError('reused cap greedy answer differs')
                    report['reused'].append(dict(name=previous['name'],source=str((directory/'report.json').relative_to(ROOT)),
                        source_sha256=manual.file_sha(directory/'report.json'),exact_requested_matrix=True,
                        exact_edited_core=True,exact_greedy_canary=True,reused_answers=164))
                    trials=[(mode+'_PROTECT_S'+str(signal).replace('.','p'),full,signal,True,stats)for signal in p['signals']]
                    ratio=float(full.norm())/float(unprotected.norm())
                    trials.append((mode+'_NONE_NORMMATCH',unprotected,ratio,False,other_stats))
                    for name,solution,signal,protect,local in trials:
                        budget.check();directory=OUT/name
                        delta=sweep.at_signal(solution,signal)
                        after,physical=solver.physical_change(adapter.original[p['layer']],adapter.original[p['layer']],delta)
                        realized=after.double()-adapter.original[p['layer']].double()
                        packet=atlas.write_npz(directory/'packet.npz',requested=delta,after=after)
                        delivery=sweep.delivery(realized,k,r,normal,signal)
                        writer=ShardWriter(directory,'answers',limit=3_000_000);answers=[]
                        with adapter.edit(p['layer'],delta) as receipt:
                            if not torch.equal(module.weight.detach().cpu(),after):
                                raise RuntimeError('CPU/GPU physical after matrix differs')
                            objective=adapter.objective();core=manual.state_fingerprint(active['model'])
                            for row in data['rows']+dev:
                                result=adapter.generate(row,max_new=p['max_new'],variant=name)
                                writer.append(result);answers.append(result)
                        legacy=[a for a in answers if a['split']!='select_dev']
                        kept={a['id']for a in legacy if a['protected']and a['exact']}
                        record=dict(name=name,mode=mode,protection=protect,target_signal=signal,
                            layer=p['layer'],solver=local,physical=physical,
                            relative_weight_change=physical['net_norm']/float(adapter.original[p['layer']].double().norm()),
                            physical_delivery=delivery,predicted_gain=solver.predicted_gain(gradient,realized),
                            objective=objective,actual_gain=before['J']-objective['J'],receipt=receipt,
                            fit=metrics.summarize([a for a in answers if a['split']=='fit']),
                            legacy=metrics.summarize(legacy),dev=devmetrics.dev_summary([a for a in answers if a['split']=='select_dev']),
                            lost_original_protected_ids=sorted(protected_ids-kept),kept_original_protected_ids=sorted(protected_ids&kept),
                            packet=packet,edited_core_sha256=core,one_global_model=True,language_review='ROOT_PENDING')
                        record['answers_manifest']=writer.close(lineage=dict(name=name,edited_core_sha256=core,one_global_model=True))
                        if manual.state_fingerprint(active['model'])!=p['origin']['core_sha256']:
                            raise RuntimeError('original core was not restored')
                        library.write_new(directory/'report.json',record);report['arms'].append(record)
                        print('[NORM_ARM] '+json.dumps(dict(name=name,norm=physical['net_norm'],signal=delivery['target_signal_projection'],
                            fit=record['fit']['exact'],dev=record['dev']['target_exact'],lost=len(protected_ids-kept),J=objective['J'])),flush=True)
                report.update(status='NORM_SWEEP_COMPLETE_ROOT_REVIEW_PENDING',counts=dict(adapter.counts),original_core_restored=True,
                              protected_original_ids=sorted(protected_ids),actual_target_positions=sum(horizons.values()),
                              peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
                if report['counts']['generated_calls']!=p['expected_new_generated_answers']:
                    raise RuntimeError('unexpected actual generation count')
            finally:adapter.close();adapter=module=None
    except BaseException as error:
        failure=error;report.update(status='NORM_SWEEP_ERROR',error=str(error),traceback=traceback.format_exc())
    finally:
        active=adapter=module=None;gc.collect();cleanup_error=library.cleanup(report)
        if failure is None:failure=cleanup_error
        report['wall_seconds']=time.monotonic()-started
        library.write_new(OUT/'report.json',report)
        print('[NORM_END] '+json.dumps({k:report.get(k)for k in('status','wall_seconds','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved afternoon norm-sweep failure')from failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','actual']);args=parser.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='check':verify();print('[NORM_CHECK] afternoon authority/source/input only;model0')
    else:actual()


if __name__=='__main__':main()
