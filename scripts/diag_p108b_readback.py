#!/usr/bin/env python3
"""CPU-only reconciliation of completed full14 atlas, not new model evidence."""
from __future__ import annotations
import json
from pathlib import Path
import torch
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_policy as policy_io
from scripts import diag_p108b_value_library as library
from scripts import p108b_policy as policies
from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as metrics


def ranks(values):
    order=sorted(range(len(values)),key=lambda i:values[i]);result=[0.]*len(values);j=0
    while j<len(order):
        k=j+1
        while k<len(order)and values[order[k]]==values[order[j]]:k+=1
        for index in order[j:k]:result[index]=(j+k-1)/2
        j=k
    return torch.tensor(result,dtype=torch.float64)


def correlation(left,right):
    a=torch.tensor(left,dtype=torch.float64);b=torch.tensor(right,dtype=torch.float64)
    a=a-a.mean();b=b-b.mean();den=float(a.norm()*b.norm())
    return float(a.dot(b))/den if den else None


def concept(identifier):
    fact=identifier.split(':')[0]
    return fact[:-3]if fact.endswith(('_ko','_en'))else fact


def fit_scale(rows):
    p=torch.tensor([r['predicted']for r in rows],dtype=torch.float64)
    a=torch.tensor([r['actual']for r in rows],dtype=torch.float64)
    denominator=float(p.square().sum())
    return max(0.,float((p*a).sum())/denominator)if denominator else 0.


def mse(rows,field):return sum((r[field]-r['actual'])**2 for r in rows)/len(rows)


def run():
    torch.set_num_threads(4);atlas.verify();base=atlas.BASE/'geometry'
    report=json.loads((base/'report.json').read_text(encoding='utf-8'))
    if len(report['layers'])!=14 or not report['registered_core_unchanged']:raise ValueError('closed14 required')
    originals=policy_io.read_answers(base,report['baseline']['answers_manifest'])
    baseline_legacy=[r for r in originals if r['split']!='select_dev'];baseline_dev=[r for r in originals if r['split']=='select_dev']
    fit_rows=[r for r in baseline_legacy if r['split']=='fit'];observations=[];records=[]
    for record in report['layers']:
        layer=record['layer'];source=base/f'layer{layer:02d}'
        rows=policy_io.read_answers(source,record['answers_manifest'])
        legacy=[r for r in rows if r['split']!='select_dev'];dev=[r for r in rows if r['split']=='select_dev']
        if len(legacy)!=68 or len(dev)!=96:raise ValueError('complete exact panel required')
        packet=policy_io.npz_tensors(base/f'layer{layer:02d}_packet.npz')
        if metrics.tensor_sha(packet['after'])!=record['geometry']['after_weight_sha256']:raise ValueError('actual packet differs')
        key=packet['fit_keys'].double();unit=key/key.norm(dim=0,keepdim=True)
        gram=unit.T@unit;within=[];between=[]
        for i in range(24):
            for j in range(i):
                (within if fit_rows[i]['fact']==fit_rows[j]['fact']else between).append(float(gram[i,j]))
        singular=torch.linalg.svdvals(key);threshold=float(singular[0])*max(key.shape)*torch.finfo(torch.float32).eps
        fd=[dict(epsilon=x['epsilon'],central_gain=x['predicted_gain_from_central_difference'],
                 relative_error=abs(x['predicted_gain_from_central_difference']-record['predicted_gain'])/max(abs(record['predicted_gain']),1e-30))for x in record['finite_difference']]
        baseline_ce=record['baseline_objective']['fit_ce_by_id'];actual_ce=record['objective']['fit_ce_by_id']
        pred=record['baseline_objective']['predicted_fit_gain_by_id']
        for row in fit_rows:
            observations.append(dict(layer=layer,id=row['id'],concept=concept(row['id']),
                predicted=pred[row['id']][str(layer)],actual=baseline_ce[row['id']]-actual_ce[row['id']]))
        dev_summary=policies.dev_summary(dev)
        records.append(dict(layer=layer,predicted_gain=record['predicted_gain'],actual_gain=record['actual_gain'],
            residual_gain=record['actual_gain']-record['predicted_gain'],finite_difference=fd,
            fit_exact=sum(bool(r['exact'])for r in legacy if r['split']=='fit'),
            legacy_exact=sum(bool(r['exact'])for r in legacy),
            legacy_protection=sum(bool(r['exact'])for r in legacy if r['protected']),
            legacy_unwanted_loops=policies.unwanted_loops(legacy),legacy_question_echoes=sum(r['diagnostics']['question_echo']for r in legacy),
            dev=dev_summary,objective=record['objective'],physical=record['geometry']['cpu_physical'],
            transfer=record['transfer'],old_budget_feasible=record['geometry']['old_budget_feasible'],
            key_geometry=dict(within_fact_cosine_mean=sum(within)/len(within),between_fact_cosine_mean=sum(between)/len(between),
                raw_singular_values=singular.tolist(),numeric_rank_fp32_threshold=threshold,
                numeric_rank_fp32=int((singular>threshold).sum()),
                observation_only_not_proof_of_semantic_failure=True)))
    groups=sorted({r['concept']for r in observations});folds=[];held=[]
    for group in groups:
        train=[r for r in observations if r['concept']!=group];test=[dict(r)for r in observations if r['concept']==group]
        scale=fit_scale(train)
        for row in test:row['calibrated']=scale*row['predicted']
        held.extend(test);folds.append(dict(heldout_concept=group,scale=scale,train_count=len(train),test_count=len(test),
            raw_rmse=mse(test,'predicted')**.5,calibrated_rmse=mse(test,'calibrated')**.5))
    original_protected=[r['id']for r in baseline_dev if r['protected']and r['exact']]
    selection_input=[dict(layer=r['layer'],objective=r['objective'],dev_corrected=r['dev'])for r in records]
    result=dict(schema='P108B_CPU_ATLAS_READBACK_V1',source_report_sha256=manual.file_sha(base/'report.json'),
        scope='same one model,14 correlated interventions,24 FIT cases; not336 independent model trials',
        records=records,baseline=dict(legacy=metrics.summarize(baseline_legacy),dev=policies.dev_summary(baseline_dev)),
        layer_gain_pearson=correlation([r['predicted_gain']for r in records],[r['actual_gain']for r in records]),
        layer_gain_spearman=correlation(ranks([r['predicted_gain']for r in records]).tolist(),ranks([r['actual_gain']for r in records]).tolist()),
        predicted_best_layer=max(records,key=lambda r:r['predicted_gain'])['layer'],
        actual_best_layer=max(records,key=lambda r:r['actual_gain'])['layer'],
        original_selector=report['selection'],corrected_selector=policies.choose_selection(selection_input,original_protected),
        concept_heldout_calibration=dict(groups=groups,folds=folds,rows=held,
            raw_rmse=mse(held,'predicted')**.5,calibrated_rmse=mse(held,'calibrated')**.5,
            limitation='one positive scalar cannot improve within-fold layer ranking; no external-model validity'),
        actual_new_model_calls=report['counts']['generated_calls'],new_gpu_execution=False,
        source_original_restored=report['registered_core_unchanged'],source_cuda_allocated_after_bytes=report['cuda_allocated_after_bytes'],
        source_cuda_reserved_after_bytes=report['cuda_reserved_after_bytes'])
    path=atlas.ROOT/'handoff/audit/nov16_p108b/ATLAS_READBACK_v1.json';library.write_new(path,result)
    print(json.dumps({k:result[k]for k in ('predicted_best_layer','actual_best_layer','layer_gain_pearson','layer_gain_spearman','actual_new_model_calls')}))
    print(json.dumps(dict(LOCO_raw_rmse=result['concept_heldout_calibration']['raw_rmse'],LOCO_calibrated_rmse=result['concept_heldout_calibration']['calibrated_rmse'])))


if __name__=='__main__':run()
