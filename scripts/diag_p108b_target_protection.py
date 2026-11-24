#!/usr/bin/env python3
"""Matched-norm interpolation with or without original-correct copy keys."""
import argparse
import gc
import json
import time
import traceback
import torch
from scripts import diag_p108b_target_write as previous
from scripts import p108b_target_values as fields
from scripts import p108b_target_protection as constrained
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_value_library as library
from scripts import diag_p108b_policy as existing
from scripts import p108b_policy as metrics
from scripts import p108b_solver as solver
from scripts import p108_weight_space as counts
from scripts import diag_p108_value_edit as native
from scripts import diag_p108_query_value as query
from scripts.p108b_tinylm import TinyAdapter
from scripts import interactive_research_infer as manual
from scripts.p106b_shards import ShardWriter

BASE=atlas.BASE
OUT=BASE/'target_protection_v1'
PROFILE=BASE/'target_protection_profile_v1.json'
INITIAL=BASE/'target_protection_initial_plan_v1.md'
CODE=('scripts/p108b_target_protection.py','scripts/diag_p108b_target_protection.py',
      'scripts/test_p108b_target_protection.py','scripts/p108_nullspace_write.py')

def prepare():
    previous.verify()
    library.write_new(PROFILE,dict(schema='P108B_TARGET_PROTECTION_V1',authority_directive=140,
        deadline=library.DEADLINE.isoformat(),previous_profile_sha256=manual.file_sha(previous.PROFILE),
        sources={n:manual.file_sha(atlas.ROOT/n)for n in CODE},layer=13,
        modes=['SHARED','PER_TARGET'],protection=['NONE','NORMAL7_PREFIX'],
        rank_rtol=1e-8,max_seconds=900,max_new=64,new_generated_answers=657,
        common_absolute_norm=13.8821193483393,norm_rtol=2e-5,
        new_body_optimizer_updates=0,new_auxiliary_optimizer_updates=0,
        initial_plan_sha256=manual.file_sha(atlas.ROOT/library.PLAN)))
    with INITIAL.open('xb')as stream:stream.write((atlas.ROOT/library.PLAN).read_bytes())
    print('[TARGET_PROTECTION_PREPARED] four arms; reused48 fields, no new optimization',flush=True)

def verify():
    parent,_,records=previous.verify();p=json.loads(PROFILE.read_text())
    if(p['authority_directive']!=140 or p['deadline']!=library.DEADLINE.isoformat()or
       p['previous_profile_sha256']!=manual.file_sha(previous.PROFILE)or
       p['initial_plan_sha256']!=manual.file_sha(INITIAL)):
        raise ValueError('preserved authority and preceding native write contract required')
    for name,sha in p['sources'].items():
        if manual.file_sha(atlas.ROOT/name)!=sha:raise ValueError('source changed: '+name)
    return parent,p,records

def prefix_keys(adapter,rows,layer):
    all_keys=[]
    for row in rows:
        item=query.pack(adapter.active,row);captured=[]
        def save(_module,args,_output):captured.append(args[0][0].detach().cpu().clone())
        handle=adapter.modules[layer].register_forward_hook(save)
        try:
            with torch.no_grad():native.target_nll(adapter.active,item)
        finally:handle.remove()
        if len(captured)!=1 or len(captured[0])!=item['x'].shape[1]:
            raise ValueError('every native prefix position and one physical visit required')
        all_keys.append(captured[0])
    return torch.cat(all_keys).double()

def actual():
    parent,p,records=verify();library.resources();budget=library.Budget(p['max_seconds'])
    if OUT.exists():raise FileExistsError('preserve previous protection attempt')
    OUT.mkdir();started=time.monotonic();torch.set_num_threads(4)
    report=dict(schema=p['schema'],status='STARTED',arms=[],body_optimizer_updates=0,
        value_optimizer_updates=0,checkpoint_writes=0,final_test_consumed=False,
        source_profile_sha256=manual.file_sha(PROFILE))
    active=adapter=None;failure=None
    try:
        data=json.loads((BASE/'data.json').read_text());fits=[r for r in data['rows']if r['split']=='fit']
        dev=json.loads((BASE/'select_dev.json').read_text())['rows']
        atlas_report=json.loads((BASE/'geometry/report.json').read_text())
        baseline=existing.read_answers(BASE/'geometry',atlas_report['baseline']['answers_manifest'])
        protected_rows=[r for r in baseline if r['split']!='select_dev'and r['protected']and r['exact']]
        required={r['id']for r in protected_rows}
        if len(required)!=7 or any(r['family']!='copy'for r in protected_rows):
            raise ValueError('only original-correct seven copy examples may define this constraint')
        with manual.selected_runtime(manual.resolve_model(parent['model']))as active:
            adapter=TinyAdapter(active,fits,data['calibration_questions'],kl_weight=parent['optimizer']['kl_weight'],budget=budget)
            try:
                canary=adapter.generate(data['rows'][0],variant='ORIGINAL_CANARY')
                if canary['generation']['generated_ids']!=next(r for r in baseline if r['id']==canary['id'])['generation']['generated_ids']:
                    raise RuntimeError('original generation replay differs')
                report['baseline_objective']=before=adapter.objective()
                report['protected_original_ids']=sorted(required)
                layer=p['layer'];normal=prefix_keys(adapter,protected_rows,layer)
                atlas.write_npz(OUT/'protected_keys.npz',keys=normal.float())
                keys,horizons=previous.target_keys(adapter,layer)
                gradient=existing.npz_tensors(BASE/f'geometry/layer{layer:02d}_gradient.npz')['gradient']
                for mode in p['modes']:
                    ks=[];rs=[]
                    for row in fits:
                        target=torch.tensor(records[(mode,layer,row['fact'])]['target_values'],dtype=torch.float32)
                        k,r=fields.question_columns(keys[row['id']],target);ks.append(k);rs.append(r)
                    k=torch.cat(ks,dim=1);r=torch.cat(rs,dim=1)
                    for protection in p['protection']:
                        budget.check();name=mode+'_'+protection;directory=OUT/name
                        record=dict(name=name,mode=mode,protection=protection,layer=layer,
                            normal_prefix_positions=len(normal),one_global_model=True)
                        try:
                            delta,stats=constrained.candidate(k,r,normal,p['common_absolute_norm'],
                                protect=protection!='NONE',rank_rtol=p['rank_rtol'])
                        except ValueError as error:
                            if 'infeasible'not in str(error):raise
                            record.update(status='NO_FEASIBLE_INTERPOLATION',reason=str(error))
                            library.write_new(directory/'report.json',record);report['arms'].append(record)
                            print('[PROTECTION_INFEASIBLE] '+json.dumps(record),flush=True);continue
                        after,physical=solver.physical_change(adapter.original[layer],adapter.original[layer],delta)
                        realized=after.double()-adapter.original[layer].double()
                        record.update(interpolation=stats,physical=physical,
                            physical_protected_output_l2=float((realized@normal.T).norm()),
                            predicted_gain=solver.predicted_gain(gradient,realized),
                            norm_match='NET_MATCHED'if abs(physical['net_norm']-p['common_absolute_norm'])<=p['norm_rtol']*p['common_absolute_norm']else'SAME_BUDGET_ONLY',
                            packet=atlas.write_npz(directory/'packet.npz',requested=delta,after=after))
                        epsilon=.003
                        with adapter.edit(layer,realized*epsilon):plus=adapter.objective()
                        with adapter.edit(layer,-realized*epsilon):minus=adapter.objective()
                        record['finite_difference']=dict(epsilon=epsilon,gain=(minus['J']-plus['J'])/(2*epsilon))
                        writer=ShardWriter(directory,'answers',limit=3_000_000);answers=[]
                        with adapter.edit(layer,delta)as receipt:
                            if not torch.equal(adapter.modules[layer].weight.detach().cpu(),after):raise RuntimeError('native matrix replay differs')
                            objective=adapter.objective();core=manual.state_fingerprint(active['model'])
                            for row in data['rows']+dev:
                                answer=adapter.generate(row,variant=name);writer.append(answer);answers.append(answer)
                        legacy=[row for row in answers if row['split']!='select_dev']
                        kept={row['id']for row in legacy if row['protected']and row['exact']}
                        record.update(status='PROTECTED_WRITE_COMPLETE_LANGUAGE_REVIEW_PENDING',objective=objective,
                            actual_gain=before['J']-objective['J'],edited_core_sha256=core,receipt=receipt,
                            fit=counts.summarize([row for row in answers if row['split']=='fit']),
                            legacy=counts.summarize(legacy),dev=metrics.dev_summary([row for row in answers if row['split']=='select_dev']),
                            kept_original_protected_ids=sorted(required&kept),lost_original_protected_ids=sorted(required-kept))
                        record['answers_manifest']=writer.close(lineage=dict(name=name,edited_core_sha256=core,one_global_model=True))
                        if manual.state_fingerprint(active['model'])!=parent['origin']['core_sha256']:
                            raise RuntimeError('original core was not restored')
                        library.write_new(directory/'report.json',record);report['arms'].append(record)
                        print('[PROTECTED_WRITE] '+json.dumps(dict(name=name,fit=record['fit']['exact'],
                            dev=record['dev']['target_exact'],lost=len(required-kept),J=objective['J'])),flush=True)
                report.update(status='PROTECTED_TARGET_MATRIX_COMPLETE_LANGUAGE_REVIEW_PENDING',counts=dict(adapter.counts),original_core_restored=True)
            finally:adapter.close();adapter=None
    except BaseException as error:
        failure=error;report.update(status='PROTECTION_WRITE_ERROR',error=str(error),traceback=traceback.format_exc())
    finally:
        active=adapter=None;gc.collect();cleanup_error=library.cleanup(report)
        if failure is None:failure=cleanup_error
        report['wall_seconds']=time.monotonic()-started;library.write_new(OUT/'report.json',report)
        print('[PROTECTION_END] '+json.dumps({k:report.get(k)for k in('status','wall_seconds','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved target-protection experiment failure')from failure

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','actual']);args=parser.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='check':verify();print('[PROTECTION_PREFLIGHT] source pinned; model0')
    else:actual()

if __name__=='__main__':main()
