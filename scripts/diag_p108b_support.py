#!/usr/bin/env python3
"""Six conditional same-budget sparse controls after weak gain/cost results."""
import argparse
import gc
import json
import time
import traceback
import torch
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_policy as policies
from scripts import diag_p108b_value_library as library
from scripts import p108b_support as criterion
from scripts import p108b_solver as solver
from scripts import p108b_policy as policy
from scripts.p108b_tinylm import TinyAdapter
from scripts import p108_joint_write as covariance_owner
from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as metrics
from scripts.p106b_shards import ShardWriter

BASE=atlas.BASE
OUT=BASE/'support_v2'
SOURCES=('scripts/p108b_support.py','scripts/test_p108b_support.py','scripts/diag_p108b_support.py')


def prepare():
    parent=policies.verify();layer=parent['selection']['chosen']['layer']
    failures=[]
    for d in(8,32):
        path=policies.OUT/f'SINGLE1_SPARSE{d}/report.json'
        r=json.loads(path.read_text(encoding='utf-8'))
        failures.append(dict(path=str(path.relative_to(atlas.ROOT)),sha256=manual.file_sha(path),dev=r['dev_corrected'],objective=r['objective']))
    if not all(r['dev']['target_exact']==0 for r in failures):raise ValueError('conditional sparse-weakness trigger not met')
    sources=dict(parent['sources']);sources.update({n:manual.file_sha(atlas.ROOT/n)for n in SOURCES})
    p=dict(schema='P108B_SPARSE_UTILITY_V2',authority_directive=140,deadline=library.DEADLINE.isoformat(),
        model=parent['model'],origin=parent['origin'],layer=layer,common_budget=parent['common_budget'],
        kl_weight=parent['selection']['chosen']['kl_weight'],
        sources=sources,conditional_trigger=failures,criteria=['MAG','ABSGAIN','GRADCOST'],denominators=[8,32],
        policy_profile_sha256=manual.file_sha(BASE/'policy_profile_v1.json'),max_new=64,
        initial_plan_sha256=manual.file_sha(atlas.ROOT/library.PLAN),
        body_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0,final_answers_consumed=False,
        rationale='ratio favors tiny proposed entries; compare absolute gradient gain and diagonal normalized gradient utility',
        safeguards='same solver/keys/C0/frozen values/budget/layer; masks re-solved, not merely zeroed')
    library.write_new(BASE/'support_profile_v2.json',p)
    with (BASE/'support_initial_plan_v2.md').open('xb')as stream:stream.write((atlas.ROOT/library.PLAN).read_bytes())
    print('[SUPPORT_PREPARED] six same-budget global sparse states; final sealed',flush=True)


def verify():
    policies.verify();p=json.loads((BASE/'support_profile_v2.json').read_text(encoding='utf-8'));library.Budget().check()
    for n,sha in p['sources'].items():
        if manual.file_sha(atlas.ROOT/n)!=sha:raise ValueError('support source changed: '+n)
    if manual.file_sha(BASE/'policy_profile_v1.json')!=p['policy_profile_sha256']:raise ValueError('parent profile changed')
    if manual.file_sha(BASE/'support_initial_plan_v2.md')!=p['initial_plan_sha256']:raise ValueError('sealed initial support plan changed')
    for ref in p['conditional_trigger']:
        if manual.file_sha(atlas.ROOT/ref['path'])!=ref['sha256']:raise ValueError('original sparse negative changed')
    return p


def actual():
    p=verify();layer=p['layer'];adapter=active=None;failure=None;started=time.monotonic()
    if OUT.exists():raise FileExistsError('preserve original sparse-control attempt')
    OUT.mkdir();report=dict(schema=p['schema'],status='STARTED',arms=[],source_profile_sha256=manual.file_sha(BASE/'support_profile_v2.json'))
    try:
        report['entry_resources']=library.resources();torch.set_num_threads(4);budget=library.Budget(5400)
        data=json.loads((BASE/'data.json').read_text(encoding='utf-8'));fits=[r for r in data['rows']if r['split']=='fit']
        dev=json.loads((BASE/'select_dev.json').read_text(encoding='utf-8'))['rows']
        packet=policies.npz_tensors(BASE/f'geometry/layer{layer:02d}_packet.npz')
        g=policies.npz_tensors(BASE/f'geometry/layer{layer:02d}_gradient.npz')['gradient'].double()
        samples=policies.npz_tensors(BASE/f'geometry/layer{layer:02d}_calibration.npz')['keys']
        c,_=covariance_owner.covariance(samples,ridge_ratio=.01)
        library_values={(r['fact'],r['layer']):torch.tensor(r['value_delta'],dtype=torch.float32)for r in library.load_candidates()}
        residual=torch.stack([library_values[(r['fact'],layer)]for r in fits],dim=1).double()
        parent=json.loads((BASE/'geometry/report.json').read_text(encoding='utf-8'))
        with manual.selected_runtime(manual.resolve_model(p['model']))as active:
            adapter=TinyAdapter(active,fits,data['calibration_questions'],kl_weight=p['kl_weight'],budget=budget)
            torch.cuda.reset_peak_memory_stats()
            try:
                baseline=adapter.objective()
                if abs(baseline['J']-parent['baseline']['objective']['J'])>1e-7:raise RuntimeError('baseline objective changed')
                for mode in p['criteria']:
                    for d in p['denominators']:
                        budget.check();name=f'SELECT_{mode}{d}';directory=OUT/name;directory.mkdir()
                        mask,scores=criterion.select(mode,d,g,packet['requested'],c)
                        delta,local=solver.solve_increment(packet['fit_keys'].double(),residual,c,
                            torch.zeros_like(adapter.original[layer],dtype=torch.float64),p['common_budget'],support=mask)
                        after,physical=solver.physical_change(adapter.original[layer],adapter.original[layer],delta)
                        prediction=solver.predicted_gain(g,after.double()-adapter.original[layer].double())
                        ref=atlas.write_npz(directory/f'step01_layer{layer:02d}.npz',requested=delta,after=after,mask=mask)
                        ref.update(layer=layer,round=1,before_weight_sha256=metrics.tensor_sha(adapter.original[layer]),after_weight_sha256=metrics.tensor_sha(after))
                        answers=[];writer=ShardWriter(directory,'answers',limit=3_000_000)
                        with adapter.edit(layer,delta):
                            if not torch.equal(adapter.modules[layer].weight.detach().cpu(),after):raise RuntimeError('actual sparse matrix differs')
                            objective=adapter.objective();core=manual.state_fingerprint(active['model'])
                            for row in data['rows']+dev:
                                a=adapter.generate(row,max_new=p['max_new'],variant=name);answers.append(a);writer.append(a)
                        if manual.state_fingerprint(active['model'])!=active['core_sha256']:raise RuntimeError('sparse rollback failed')
                        arm=dict(schema=p['schema'],name=name,status='SPARSE_CONTROL_COMPLETE_QUALITY_SEPARATE',original_restored=True,
                            packets=[ref],actual_core_sha256=core,rounds_executed=1,
                            physical=dict(physical,path_norm=physical['step_norm'],unique_layers=[layer]),
                            objective=objective,predicted_gain=prediction,actual_gain=baseline['J']-objective['J'],
                            support_selection=scores,local=local,legacy=metrics.summarize(answers[:68]),
                            dev_corrected=policy.dev_summary(answers[68:]),one_global_model=True,
                            match_status='NET_MATCHED'if abs(physical['net_norm']-p['common_budget'])<=2e-5*p['common_budget']else'SAME_BUDGET_ONLY')
                        arm['answers_manifest']=writer.close(lineage=dict(name=name,core_sha256=core))
                        library.write_new(directory/'report.json',arm);report['arms'].append(dict(name=name,predicted_gain=prediction,actual_gain=arm['actual_gain'],dev=arm['dev_corrected']))
                        print('[SUPPORT_ARM] '+json.dumps(report['arms'][-1]),flush=True)
                report.update(status='SIX_SPARSE_CONTROLS_COMPLETE',registered_core_unchanged=manual.state_fingerprint(active['model'])==active['core_sha256'],
                    peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
            finally:
                if adapter is not None:adapter.close();adapter=None
    except BaseException as error:failure=error;report.update(status='SUPPORT_ERROR',error=str(error),traceback=traceback.format_exc())
    finally:
        active=adapter=None;gc.collect();cleanup_error=library.cleanup(report)
        if failure is None:failure=cleanup_error
        report['wall_seconds']=time.monotonic()-started;library.write_new(OUT/'report.json',report)
        print('[SUPPORT_END] '+json.dumps({k:report.get(k)for k in('status','wall_seconds','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved support-control failure')from failure


def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','check','actual']);a=p.parse_args()
    if a.phase=='prepare':prepare()
    elif a.phase=='check':verify();print('[SUPPORT_CHECK] pinned CPU inputs; no model')
    else:actual()


if __name__=='__main__':main()
