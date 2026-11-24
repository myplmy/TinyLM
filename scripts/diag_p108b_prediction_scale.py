#!/usr/bin/env python3
"""Held-out step-size prediction on existing Tiny14/HF18 edit directions."""
import argparse
import gc
import json
import math
import time
import traceback
import torch
import torch.nn.functional as F
from torch.nn.attention import sdpa_kernel,SDPBackend
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_value_library as library
from scripts import diag_p108b_policy as packets
from scripts import diag_p108b_hf_canary as hf
from scripts import diag_p108b_readback as readback
from scripts.p108b_tinylm import TinyAdapter
from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as metrics

BASE=atlas.BASE
PROFILE=BASE/'prediction_scale_profile_v1.json'
INITIAL=BASE/'prediction_scale_initial_plan_v1.md'
OUT=BASE/'prediction_scale_v1'
CODE=('scripts/diag_p108b_prediction_scale.py','scripts/test_p108b_prediction_scale.py',
      'scripts/diag_p108b_hf_canary.py','scripts/diag_p108b_readback.py')


def curvature(baseline,plus,minus,h):
    if not all(math.isfinite(x)for x in(baseline,plus,minus,h))or h<=0:
        raise ValueError('finite losses and positive declared calibration step required')
    return (plus+minus-2*baseline)/(h*h)


def predictions(linear_gain,q,alpha,baseline):
    if not all(math.isfinite(x)for x in(linear_gain,q,alpha,baseline))or alpha<=0 or baseline<0:
        raise ValueError('finite declared forward prediction required')
    quadratic=linear_gain-.5*q*alpha*alpha
    return dict(linear=linear_gain,quadratic=quadratic,bounded_linear=min(baseline,linear_gain),bounded_quadratic=min(baseline,quadratic))


def prepare():
    p=atlas.verify();hp=hf.verify();refs={}
    names=['geometry/report.json','hf_canary_v1/report.json']
    names += [f'geometry/layer{i:02d}_{kind}.npz'for i in range(14)for kind in('packet','gradient')]
    names += [f'hf_canary_v1/layer{i:02d}_packet.npz'for i in range(18)]
    for name in names:refs[name]=manual.file_sha(BASE/name)
    library.write_new(PROFILE,dict(schema='P108B_STEP_PREDICTION_V1',tiny_model=p['model'],tiny_origin=p['origin'],
        hf_profile_sha256=manual.file_sha(hf.BASE/'hf_canary_profile_v1.json'),hf_origin=hp['assets'],references=refs,
        sources={n:manual.file_sha(atlas.ROOT/n)for n in CODE},calibration_h=1/32,
        observed_alphas=[1/32,-1/32,1/16,1/8,1/4,1/2],heldout_alphas=[1/16,1/8,1/4,1/2,1],
        reused_alpha=1,seconds=dict(tiny=1200,gemma=300),new_optimizer_updates=0,new_generated_answers=0,checkpoint_writes=0,
        claim_scope='NUMERICAL_STEP_SIZE_PREDICTION_NOT_MODEL_QUALITY_OR_GENERAL_TRANSFER',
        initial_plan_sha256=manual.file_sha(atlas.ROOT/library.PLAN)))
    with INITIAL.open('xb')as f:f.write((atlas.ROOT/library.PLAN).read_bytes())
    print('[STEP_PREDICTION_PREPARED] Tiny14 andGemma18; old full-step effects reused',flush=True)


def verify():
    atlas.verify();hf.verify();p=json.loads(PROFILE.read_text(encoding='utf-8'))
    if manual.file_sha(INITIAL)!=p['initial_plan_sha256']or manual.file_sha(BASE/'hf_canary_profile_v1.json')!=p['hf_profile_sha256']:
        raise ValueError('initial plan/external profile changed')
    for name,sha in p['sources'].items():
        if manual.file_sha(atlas.ROOT/name)!=sha:raise ValueError('step-prediction source changed')
    for name,sha in p['references'].items():
        if manual.file_sha(BASE/name)!=sha:raise ValueError('frozen original direction/report changed')
    return p


def observe_layer(index,module,proposal,score,edit,baseline,previous,gradient,p,budget):
    before=module.weight.detach().cpu().clone();rows=[]
    for alpha in p['observed_alphas']:
        budget.check();requested=proposal*alpha
        with edit(index,requested),torch.no_grad():
            measured=score();after=module.weight.detach().cpu().clone()
            actual=after.double()-before.double()
            linear=(-float((gradient.double()*actual).sum())if gradient is not None else alpha*previous['predicted_gain'])
            row=dict(alpha=alpha,objective=measured,actual_gain=baseline['J']-measured['J'],linear_gain=linear,
                actual_norm=float(actual.norm()),after_weight_sha256=metrics.tensor_sha(after),
                recipe=dict(original_before_weight_sha256=metrics.tensor_sha(before),operation='native_FP32(before + native_FP32(source_requested * exact_alpha))',
                    scalar_is_exact_binary_fraction=True),reused=False)
        if not torch.equal(module.weight.detach().cpu(),before):raise RuntimeError('single-step native matrix did not restore')
        rows.append(row)
    rows.append(dict(alpha=1,objective=previous['objective'],actual_gain=previous['actual_gain'],linear_gain=previous['predicted_gain'],
        actual_norm=previous['actual_norm'],after_weight_sha256=previous['after_weight_sha256'],reused=True))
    h=p['calibration_h'];plus=next(r for r in rows if r['alpha']==h);minus=next(r for r in rows if r['alpha']==-h)
    q=curvature(baseline['J'],plus['objective']['J'],minus['objective']['J'],h)
    heldout=[]
    for row in rows:
        if row['alpha']in p['heldout_alphas']:
            pred=predictions(row['linear_gain'],q,row['alpha'],baseline['J'])
            heldout.append(dict(row,predictions=pred,errors={key:value-row['actual_gain']for key,value in pred.items()}))
    return dict(layer=index,curvature=q,calibration_h=h,observations=rows,heldout=heldout,
        linear_basis='STORED_NATIVE_FP32_PARAMETER_GRADIENT_DOT_REALIZED_DELTA'if gradient is not None else 'STORED_NEGATIVE_GRADIENT_DIRECTION_SCALAR; FP32_ROUNDING_APPROXIMATION')


def summarize(records,alphas):
    result={}
    for alpha in alphas:
        rows=[next(r for r in record['heldout']if r['alpha']==alpha)for record in records]
        actual=[r['actual_gain']for r in rows];by_method={}
        for method in('linear','quadratic','bounded_linear','bounded_quadratic'):
            predicted=[r['predictions'][method]for r in rows]
            by_method[method]=dict(rmse=(sum((a-b)**2 for a,b in zip(actual,predicted))/len(rows))**.5,
                rank_correlation=readback.correlation(readback.ranks(actual).tolist(),readback.ranks(predicted).tolist()),
                predicted_best_layer=max(range(len(rows)),key=lambda i:predicted[i]))
        result[str(alpha)]=dict(layers=len(rows),actual_best_layer=max(range(len(rows)),key=lambda i:actual[i]),methods=by_method)
    return result


def actual(arm):
    p=verify();library.resources();budget=library.Budget(p['seconds'][arm]);directory=OUT/arm
    if directory.exists():raise FileExistsError('preserve prior step-prediction attempt')
    directory.mkdir(parents=True);started=time.monotonic();torch.set_num_threads(4)
    report=dict(schema=p['schema'],arm=arm,status='STARTED',records=[],new_optimizer_updates=0,new_generated_answers=0,
        checkpoint_writes=0,source_profile_sha256=manual.file_sha(PROFILE),claim_scope=p['claim_scope'])
    active=adapter=body=lm=module=downs=ids=targets=proposal=gradient=None;failure=None
    try:
        if arm=='tiny':
            previous=json.loads((BASE/'geometry/report.json').read_text());data=json.loads((BASE/'data.json').read_text())
            fits=[r for r in data['rows']if r['split']=='fit']
            with manual.selected_runtime(manual.resolve_model(p['tiny_model']))as active,sdpa_kernel(SDPBackend.MATH):
                adapter=TinyAdapter(active,fits,data['calibration_questions'],kl_weight=.0625,budget=budget)
                try:
                    baseline=adapter.objective();report['baseline']=baseline
                    if abs(baseline['J']-previous['baseline']['objective']['J'])>1e-6:raise RuntimeError('exact original Tiny objective canary differs')
                    for old in previous['layers']:
                        index=old['layer'];module=adapter.modules[index];packet=packets.npz_tensors(BASE/f'geometry/layer{index:02d}_packet.npz')
                        proposal=packet['requested'];gradient=packets.npz_tensors(BASE/f'geometry/layer{index:02d}_gradient.npz')['gradient']
                        reference=dict(old,actual_norm=old['geometry']['cpu_physical']['net_norm'],after_weight_sha256=old['geometry']['after_weight_sha256'])
                        record=observe_layer(index,module,proposal,adapter.objective,adapter.edit,baseline,reference,gradient,p,budget)
                        record['source_packet_sha256']=p['references'][f'geometry/layer{index:02d}_packet.npz']
                        if manual.state_fingerprint(active['model'])!=p['tiny_origin']['core_sha256']:raise RuntimeError('complete Tiny core rollback differs')
                        library.write_new(directory/f'layer{index:02d}.json',record);report['records'].append(record)
                        print('[STEP_LAYER] '+json.dumps(dict(arm=arm,layer=index,curvature=record['curvature'])),flush=True)
                    report['new_model_forwards']=adapter.counts['model_forwards'];report['original_core_restored']=True
                finally:adapter.close();adapter=module=None
        else:
            hp=hf.verify();previous=json.loads((BASE/'hf_canary_v1/report.json').read_text())
            report['external_runtime_proof']={}
            with hf.external.model_runtime(hp['model'],torch,hp['assets'],proof=report['external_runtime_proof'])as(lm,_):
                body=lm.model;downs=hf.modules(body);hf.validate_config(body.config.to_dict())
                prompt=previous['prompt_ids'];target=previous['targets']
                ids=torch.tensor([prompt+target[:-1]],device='cuda');targets=torch.tensor(target,device='cuda')
                forwards=[0]
                def score():
                    budget.check();forwards[0]+=1
                    with torch.no_grad():loss=F.cross_entropy(body(input_ids=ids,use_cache=False,logits_to_keep=len(target)).logits[0].float(),targets)
                    return dict(J=float(loss))
                baseline=score();report['baseline']=baseline
                if abs(baseline['J']-previous['baseline_nll'])>1e-6:raise RuntimeError('native HF original objective canary differs')
                original=manual.state_fingerprint(body)
                for old in previous['layers']:
                    index=old['layer'];module=downs[index];proposal=packets.npz_tensors(BASE/f'hf_canary_v1/layer{index:02d}_packet.npz')['requested']
                    reference=dict(old,objective=dict(J=baseline['J']-old['actual_gain']))
                    record=observe_layer(index,module,proposal,score,lambda layer,delta:hf.edit(downs[layer],delta.to(downs[layer].weight)),
                        baseline,reference,None,p,budget)
                    record['source_packet_sha256']=p['references'][f'hf_canary_v1/layer{index:02d}_packet.npz']
                    if manual.state_fingerprint(body)!=original:raise RuntimeError('complete HF rollback differs')
                    library.write_new(directory/f'layer{index:02d}.json',record);report['records'].append(record)
                    print('[STEP_LAYER] '+json.dumps(dict(arm=arm,layer=index,curvature=record['curvature'])),flush=True)
                report.update(new_model_forwards=forwards[0],original_core_restored=True)
                active=adapter=body=lm=module=downs=ids=targets=proposal=gradient=None
        report.update(status='STEP_SIZE_PREDICTION_COMPLETE_NOT_QUALITY',summary=summarize(report['records'],p['heldout_alphas']))
    except BaseException as error:
        failure=error;report.update(status='STEP_PREDICTION_ERROR',error=str(error),traceback=traceback.format_exc())
    finally:
        active=adapter=body=lm=module=downs=ids=targets=proposal=gradient=None
        gc.collect();cleanup_error=library.cleanup(report)
        if failure is None:failure=cleanup_error
        report['wall_seconds']=time.monotonic()-started;library.write_new(directory/'report.json',report)
        print('[STEP_PREDICTION_END] '+json.dumps({k:report.get(k)for k in('arm','status','new_model_forwards','wall_seconds','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved step-prediction failure')from failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','actual']);parser.add_argument('--arm',choices=['tiny','gemma']);a=parser.parse_args()
    if a.phase=='prepare':prepare()
    elif a.phase=='check':verify();print('[STEP_PREDICTION_CHECK] sealed CPU-only source')
    elif a.arm:actual(a.arm)
    else:parser.error('one serial model arm required')


if __name__=='__main__':main()
