#!/usr/bin/env python3
"""Four global native writes from sealed response/EOT value fields."""
import argparse
import gc
import json
import time
import traceback
import torch
from scripts import diag_p108b_target_values as values
from scripts import p108b_target_values as field
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_value_library as library
from scripts import diag_p108b_policy as existing
from scripts import p108b_policy as policy
from scripts import p108b_solver as solver
from scripts import p108_joint_write as moments
from scripts import p108_weight_space as metrics
from scripts import p108_value_edit as value
from scripts import diag_p108_value_edit as native
from scripts.p108b_tinylm import TinyAdapter
from scripts import interactive_research_infer as manual
from scripts.p106b_shards import ShardWriter

BASE=atlas.BASE
OUT=values.OUT/'writes_v2'
PROFILE=BASE/'target_write_profile_v2.json'
INITIAL=BASE/'target_write_initial_plan_v2.md'
PARTIAL=values.OUT/'writes'
CODE=('scripts/diag_p108b_target_write.py','scripts/test_p108b_target_write.py','scripts/p108b_target_values.py','scripts/diag_p108b_target_values.py')


def progress(record):
    return dict(name=record['name'],fit=record['fit']['exact'],dev_target=record['dev']['target_exact'],
        lost=len(record['lost_original_protected_ids']),norm_match=record['norm_match'])


def value_records(p):
    records={}
    for mode in p['modes']:
        for layer in p['layers']:
            for fact in p['facts']:
                path=values.OUT/'values'/f'{mode}_layer{layer:02d}_{fact}.json'
                records[(mode,layer,fact)]=values.validate_candidate(json.loads(path.read_text()),p,fact,layer,mode)
    return records


def prepare():
    p=values.verify();complete=values.OUT/'values_complete.json';r=json.loads(complete.read_text())
    if r['status']!='TARGET_FIELD_LIBRARY_COMPLETE_NOT_GLOBAL_QUALITY'or not r['original_core_restored']or r['cuda_allocated_after_bytes']or r['cuda_reserved_after_bytes']:
        raise ValueError('complete48 auxiliary fields and strict cleanup required')
    records=value_records(p);old=json.loads((BASE/'geometry/report.json').read_text());refs={}
    for path in(values.OUT/'values').glob('*_layer*.json'):refs[str(path.relative_to(BASE))]=manual.file_sha(path)
    refs[str(complete.relative_to(BASE))]=manual.file_sha(complete)
    for layer in p['layers']:
        for suffix in('calibration','gradient'):refs[f'geometry/layer{layer:02d}_{suffix}.npz']=manual.file_sha(BASE/f'geometry/layer{layer:02d}_{suffix}.npz')
    refs['geometry/report.json']=manual.file_sha(BASE/'geometry/report.json')
    interrupted=json.loads((PARTIAL/'report.json').read_text())
    if interrupted['status']!='TARGET_WRITE_ERROR'or interrupted['error']!="'target'"or len(interrupted['arms'])!=1 or interrupted['cuda_allocated_after_bytes']or interrupted['cuda_reserved_after_bytes']:
        raise ValueError('exact interrupted progress-only failure/closed first arm required')
    for path in PARTIAL.rglob('*'):
        if path.is_file():refs[str(path.relative_to(BASE))]=manual.file_sha(path)
    library.write_new(PROFILE,dict(schema='P108B_TARGET_WRITE_V2',values_profile_sha256=manual.file_sha(values.PROFILE),
        sources={n:manual.file_sha(atlas.ROOT/n)for n in CODE},references=refs,actual_fields=len(records),
        common_absolute_norm=old['common_budget'],norm_rtol=2e-5,finite_epsilon=.003,max_new=64,max_seconds=1200,
        new_body_optimizer_updates=0,new_auxiliary_optimizer_updates=0,new_generated_answers=494,reused_arms=['SHARED_layer09'],
        initial_plan_sha256=manual.file_sha(atlas.ROOT/library.PLAN)))
    with INITIAL.open('xb')as f:f.write((atlas.ROOT/library.PLAN).read_bytes())
    print('[TARGET_WRITE_PREPARED] three new global writes,494 calls; closed first164 reused after native canary',flush=True)


def verify():
    p=values.verify();r=json.loads(PROFILE.read_text())
    if manual.file_sha(values.PROFILE)!=r['values_profile_sha256']or manual.file_sha(INITIAL)!=r['initial_plan_sha256']:
        raise ValueError('initial write/value binding changed')
    for name,sha in r['sources'].items():
        if manual.file_sha(atlas.ROOT/name)!=sha:raise ValueError('write driver source changed')
    for name,sha in r['references'].items():
        if manual.file_sha(BASE/name)!=sha:raise ValueError('completed field/original geometry changed')
    return p,r,value_records(p)


def target_keys(adapter,layer):
    keys={};horizons={};module=adapter.modules[layer]
    for row in adapter.fits:
        item=adapter.packeds[row['id']];h=len(item['targets']);capture={}
        with torch.no_grad(),field.inject_window(module,item['start'],torch.zeros(h,768,device='cuda'),capture=capture):
            native.target_nll(adapter.active,item)
        keys[row['id']]=capture['keys'];horizons[row['id']]=h
    return keys,horizons


def actual():
    p,config,records=verify();library.resources();budget=library.Budget(config['max_seconds'])
    if OUT.exists():raise FileExistsError('preserve prior physical target-write attempt')
    OUT.mkdir();started=time.monotonic();torch.set_num_threads(4)
    report=dict(schema=config['schema'],status='STARTED',arms=[],body_optimizer_updates=0,auxiliary_optimizer_updates=0,checkpoint_writes=0,
        source_profile_sha256=manual.file_sha(PROFILE),final_test_consumed=False)
    active=adapter=module=None;failure=None
    try:
        data=json.loads((BASE/'data.json').read_text());fits=[r for r in data['rows']if r['split']=='fit'];dev=json.loads((BASE/'select_dev.json').read_text())['rows']
        old=json.loads((BASE/'geometry/report.json').read_text());baseline=existing.read_answers(BASE/'geometry',old['baseline']['answers_manifest'])
        protected={r['id']for r in baseline if r['split']=='select_dev'and r['protected']and r['exact']}
        with manual.selected_runtime(manual.resolve_model(p['model']))as active:
            adapter=TinyAdapter(active,fits,data['calibration_questions'],kl_weight=p['optimizer']['kl_weight'],budget=budget)
            try:
                canary=adapter.generate(data['rows'][0],variant='ORIGINAL_CANARY')
                if canary['generation']['generated_ids']!=next(r for r in baseline if r['id']==canary['id'])['generation']['generated_ids']:
                    raise RuntimeError('original global answer replay canary differs')
                before=adapter.objective();report['baseline_objective']=before
                if abs(before['J']-old['baseline']['objective']['J'])>1e-6:raise RuntimeError('original objective differs')
                for layer in p['layers']:
                    keys,horizons=target_keys(adapter,layer);saved=existing.npz_tensors(BASE/f'geometry/layer{layer:02d}_calibration.npz')['keys']
                    moment,stats=moments.covariance(saved,ridge_ratio=.01);gradient=existing.npz_tensors(BASE/f'geometry/layer{layer:02d}_gradient.npz')['gradient']
                    for mode in p['modes']:
                        budget.check();name=f'{mode}_layer{layer:02d}';directory=OUT/name;writer=ShardWriter(directory,'answers',limit=3_000_000)
                        if name in config['reused_arms']:
                            previous=json.loads((PARTIAL/name/'report.json').read_text())
                            prior_answers=existing.read_answers(PARTIAL/name,previous['answers_manifest'])
                            prior_packet=existing.npz_tensors(PARTIAL/name/'packet.npz')
                            with adapter.edit(layer,prior_packet['requested']):
                                if manual.state_fingerprint(active['model'])!=previous['edited_core_sha256']:raise RuntimeError('closed first-arm full native core replay differs')
                                replay=adapter.generate(prior_answers[0],variant=name+':REUSE_CANARY')
                                if replay['generation']['generated_ids']!=prior_answers[0]['generation']['generated_ids']:raise RuntimeError('closed first-arm actual generation replay differs')
                            previous=dict(previous,reused_from=str((PARTIAL/name).relative_to(atlas.ROOT)),reuse_generation_canary=replay,
                                reused_answers=164,new_arm_answers=0)
                            library.write_new(directory/'reused_report.json',previous);report['arms'].append(previous)
                            print('[TARGET_GLOBAL_REUSED] '+json.dumps(progress(previous)),flush=True)
                            continue
                        ks=[];rs=[]
                        for row in fits:
                            targets=torch.tensor(records[(mode,layer,row['fact'])]['target_values'],dtype=torch.float32)
                            k,r=field.question_columns(keys[row['id']],targets);ks.append(k);rs.append(r)
                        k=torch.cat(ks,dim=1);r=torch.cat(rs,dim=1)
                        proposed,local=solver.solve_increment(k,r,moment,torch.zeros_like(adapter.original[layer],dtype=torch.float64),config['common_absolute_norm'],rounding_margin=1e-6)
                        after,physical=solver.physical_change(adapter.original[layer],adapter.original[layer],proposed)
                        realized=after.double()-adapter.original[layer].double();predicted=solver.predicted_gain(gradient,realized)
                        packet=atlas.write_npz(directory/'packet.npz',requested=proposed,after=after,weighted_keys=k.float(),weighted_values=r.float())
                        epsilon=config['finite_epsilon']
                        with adapter.edit(layer,realized*epsilon):plus=adapter.objective()
                        with adapter.edit(layer,realized*(-epsilon)):minus=adapter.objective()
                        finite=(minus['J']-plus['J'])/(2*epsilon)
                        with adapter.edit(layer,proposed)as receipt:
                            if not torch.equal(adapter.modules[layer].weight.detach().cpu(),after):raise RuntimeError('native FP32 matrix differs from saved after')
                            actual=adapter.objective();core=manual.state_fingerprint(active['model']);answers=[]
                            for row in data['rows']+dev:
                                answer=adapter.generate(row,variant=name);writer.append(answer);answers.append(answer)
                        current_dev=[row for row in answers if row['split']=='select_dev'];summary=policy.dev_summary(current_dev)
                        current_protected={row['id']for row in current_dev if row['protected']and row['exact']}
                        record=dict(name=name,layer=layer,mode=mode,objective=actual,predicted_gain=predicted,actual_gain=before['J']-actual['J'],
                            finite_difference=dict(epsilon=epsilon,gain=finite),physical=physical,
                            norm_match='NET_MATCHED'if abs(physical['net_norm']-config['common_absolute_norm'])<=config['norm_rtol']*config['common_absolute_norm']else'SAME_BUDGET_ONLY',
                            packet=packet,receipt=receipt,local=local,calibration=stats,
                            actual_target_position_columns=sum(horizons.values()),effective_question_weight=24,
                            fit=metrics.summarize([row for row in answers if row['split']=='fit']),
                            legacy=metrics.summarize([row for row in answers if row['split']!='select_dev']),dev=summary,
                            lost_original_protected_ids=sorted(protected-current_protected),new_protected_ids=sorted(current_protected-protected),
                            edited_core_sha256=core,one_global_model=True,language_review='ROOT_REVIEW_PENDING')
                        record['answers_manifest']=writer.close(lineage=dict(name=name,edited_core_sha256=core,one_global_model=True))
                        if manual.state_fingerprint(active['model'])!=p['origin']['core_sha256']:raise RuntimeError('original full core not restored after global write')
                        library.write_new(directory/'report.json',record);report['arms'].append(record)
                        print('[TARGET_GLOBAL] '+json.dumps(progress(record)),flush=True)
                report.update(status='TARGET_GLOBAL_WRITES_COMPLETE_LANGUAGE_REVIEW_PENDING',counts=dict(adapter.counts),original_core_restored=True)
            finally:adapter.close();adapter=module=None
    except BaseException as error:
        failure=error;report.update(status='TARGET_WRITE_ERROR',error=str(error),traceback=traceback.format_exc())
    finally:
        active=adapter=module=None;gc.collect();cleanup_error=library.cleanup(report)
        if failure is None:failure=cleanup_error
        report['wall_seconds']=time.monotonic()-started;library.write_new(OUT/'report.json',report)
        print('[TARGET_WRITE_END] '+json.dumps({k:report.get(k)for k in('status','wall_seconds','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved target-window physical-write failure')from failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','actual']);a=parser.parse_args()
    if a.phase=='prepare':prepare()
    elif a.phase=='check':verify();print('[TARGET_WRITE_CHECK] four frozen proposals admitted, no model/GPU')
    else:actual()


if __name__=='__main__':main()
