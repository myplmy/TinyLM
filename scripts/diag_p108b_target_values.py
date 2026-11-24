#!/usr/bin/env python3
"""Optimize only target-window value fields on the existing completed parent."""
import argparse
from datetime import datetime,timezone
import gc
import json
import time
import traceback
import torch
import torch.nn.functional as F
from scripts import p108b_target_values as field
from scripts import diag_p108b_value_library as library
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108_value_edit as native
from scripts import diag_p108_query_value as query
from scripts import p108_value_edit as value
from scripts import p108_wsp_attention as outputs
from scripts import interactive_research_infer as manual

BASE=atlas.BASE
OUT=BASE/'target_values_v1'
PROFILE=BASE/'target_values_profile_v1.json'
INITIAL=BASE/'target_values_initial_plan_v1.md'
CODE=('scripts/diag_p108b_target_values.py','scripts/p108b_target_values.py','scripts/test_p108b_target_values.py')


def prepare():
    parent=atlas.verify();old=library.verify();data=json.loads((BASE/'data.json').read_text())
    tok=manual.local_tokenizer(manual.verify_manifest());groups={}
    for row in data['rows']:
        if row['split']=='fit':groups.setdefault(row['fact'],[]).append(row)
    lengths={}
    for fact,rows in groups.items():
        tokens=[tok.encode(row['expected']).ids+[4]for row in rows]
        if len(rows)!=2 or tokens[0]!=tokens[1]or len(tokens[0])<2:raise ValueError('same verified answer/EOT for two original FIT prompts required')
        lengths[fact]=len(tokens[0])
    optimizer={k:old[k]for k in('value_steps','value_lr','kl_weight','value_regularization','value_norm_cap')}
    library.write_new(PROFILE,dict(schema='P108B_TARGET_VALUES_V1',model=parent['model'],origin=parent['origin'],
        data_sha256=manual.file_sha(BASE/'data.json'),sources={n:manual.file_sha(atlas.ROOT/n)for n in CODE},
        layers=[9,13],modes=list(field.MODES),facts=list(groups),target_lengths=lengths,optimizer=optimizer,
        expected_candidates=48,expected_auxiliary_updates=1920,max_seconds=1200,
        expected_auxiliary_target_exposures=2*len(field.MODES)*len([9,13])*optimizer['value_steps']*sum(lengths.values()),
        body_optimizer_updates=0,checkpoint_writes=0,new_answer_generation=0,
        initial_plan_sha256=manual.file_sha(atlas.ROOT/library.PLAN)))
    with INITIAL.open('xb')as f:f.write((atlas.ROOT/library.PLAN).read_bytes())
    print('[TARGET_VALUES_PREPARED]48 fields,1920 auxiliary updates; body/GPU not loaded',flush=True)


def verify():
    atlas.verify();p=json.loads(PROFILE.read_text(encoding='utf-8'))
    for name,sha in p['sources'].items():
        if manual.file_sha(atlas.ROOT/name)!=sha:raise ValueError('target-value source changed')
    if manual.file_sha(BASE/'data.json')!=p['data_sha256']or manual.file_sha(INITIAL)!=p['initial_plan_sha256']:
        raise ValueError('original TRAIN or initial target-value plan changed')
    return p


def optimize(active,module,fits,anchors,mode,p,budget):
    packed=[query.pack(active,row)for row in fits];h=len(packed[0]['targets']);dim=module.weight.shape[0]
    if any(item['targets'].tolist()!=packed[0]['targets'].tolist()for item in packed):raise ValueError('same exact targets required')
    captures=[]
    with torch.no_grad():
        for item in packed:
            captured={}
            with field.inject_window(module,item['start'],torch.zeros(h,dim,device='cuda'),capture=captured):native.target_nll(active,item)
            captures.append(captured)
        norms=torch.stack([r['values'].norm(dim=1)for r in captures]).mean(0).to(module.weight)
        refs=[native.prompt_log_probs(active,row).detach()for row in anchors]
    parameters=torch.nn.Parameter(torch.zeros(1 if mode=='SHARED'else h,dim,device='cuda'))
    optimizer=torch.optim.Adam([parameters],lr=p['value_lr']);trace=[];exposures=0
    for step in range(p['value_steps']):
        budget.check();value.refresh_autograd_views(active['model'],active['route']);optimizer.zero_grad(set_to_none=True)
        v=field.value_field(parameters,mode,norms);nlls=[];kls=[]
        for item in packed:
            with field.inject_window(module,item['start'],v):nlls.append(native.target_nll(active,item))
            exposures+=len(item['targets'])
        for row,reference in zip(anchors,refs):
            with query.oracle(active,module,row,v[0]):current=native.prompt_log_probs(active,row)
            kls.append(F.kl_div(current,reference,log_target=True,reduction='sum'))
        regularizer=(v.square().sum(dim=1)/norms.square()).mean()*p['value_regularization']
        loss=torch.stack(nlls).mean()+p['kl_weight']*torch.stack(kls).mean()+regularizer
        if not bool(torch.isfinite(loss)):raise RuntimeError('nonfinite auxiliary target-window loss')
        parameters.grad,=torch.autograd.grad(loss,parameters)
        if not bool(torch.isfinite(parameters.grad).all()):raise RuntimeError('nonfinite auxiliary value-field gradient')
        optimizer.step();field.limit_parameters(parameters,mode,norms,p['value_norm_cap'])
        if step%10==0 or step+1==p['value_steps']:
            trace.append(dict(step=step,nll=float(torch.stack(nlls).mean().detach()),anchor_kl=float(torch.stack(kls).mean().detach())))
    v=field.value_field(parameters,mode,norms).detach();final=[]
    with torch.no_grad():
        for item in packed:
            with field.inject_window(module,item['start'],v):final.append(float(native.target_nll(active,item)))
    return v.cpu(),dict(value_optimizer_updates=p['value_steps'],supervised_target_token_exposures=exposures,
        auxiliary_parameters=parameters.numel(),native_target_positions=h,native_value_norms=norms.detach().cpu().tolist(),
        optimized_position_norms=v.norm(dim=1).cpu().tolist(),trace=trace,final_teacher_forced_nll=sum(final)/len(final),
        oracle_free_generation=False,one_global_model=False)


def validate_candidate(candidate,p,fact,layer,mode):
    if(candidate['fact'],candidate['layer'],candidate['mode'])!=(fact,layer,mode)or candidate['source_profile_sha256']!=manual.file_sha(PROFILE):
        raise ValueError('same exact sealed field identity required')
    values=torch.tensor(candidate['target_values'],dtype=torch.float32)
    if values.shape!=(p['target_lengths'][fact],768)or not bool(torch.isfinite(values).all())or candidate['optimization']['value_optimizer_updates']!=40:
        raise ValueError('complete finite original40-update field required')
    return candidate


def actual(resume=False):
    p=verify();library.resources();budget=library.Budget(p['max_seconds']);directory=OUT/'values'
    if directory.exists()and not resume:raise FileExistsError('explicit same-profile resume required')
    if resume and not directory.is_dir():raise ValueError('no partial target library to resume')
    directory.mkdir(parents=True,exist_ok=True);started=time.monotonic();torch.set_num_threads(4)
    report=dict(schema=p['schema'],status='STARTED',source_profile_sha256=manual.file_sha(PROFILE),new_candidates=[],reused_candidates=0,
        body_optimizer_updates=0,checkpoint_writes=0,new_answer_generation=0,resumed=resume)
    active=modules=module=v=None;failure=None
    try:
        data=json.loads((BASE/'data.json').read_text())
        with manual.selected_runtime(manual.resolve_model(p['model']))as active,value.freeze_parameters(active['model']):
            modules=outputs.outputs(active['model'])
            for mode in p['modes']:
                for layer in p['layers']:
                    module=modules[f'mlp:{layer}']
                    for fact in p['facts']:
                        path=directory/f'{mode}_layer{layer:02d}_{fact}.json'
                        if path.exists():validate_candidate(json.loads(path.read_text()),p,fact,layer,mode);report['reused_candidates']+=1;continue
                        fits=[r for r in data['rows']if r['fact']==fact and r['split']=='fit'];subject=fits[0]['subject']
                        texts=([f'{subject}에 관해 간단히 소개하세요.',f'{subject}에 관한 정보를 알려주세요.']if fits[0]['language']=='ko'else
                            [f'Give a short introduction to {subject}.',f'Tell me something about {subject}.'])
                        anchors=[dict(fits[0],question=text,expected=None)for text in texts]
                        v,stats=optimize(active,module,fits,anchors,mode,p['optimizer'],budget)
                        candidate=dict(fact=fact,layer=layer,mode=mode,target_values=v.tolist(),optimization=stats,
                            source_profile_sha256=manual.file_sha(PROFILE),base_core_sha256=active['core_sha256'])
                        validate_candidate(candidate,p,fact,layer,mode);library.write_new(path,candidate)
                        report['new_candidates'].append(dict(fact=fact,layer=layer,mode=mode,optimization=stats));v=None
                        print('[TARGET_VALUE] '+json.dumps(dict(fact=fact,layer=layer,mode=mode,nll=stats['final_teacher_forced_nll'])),flush=True)
            report['original_core_restored']=manual.state_fingerprint(active['model'])==p['origin']['core_sha256']
            if not report['original_core_restored']:raise RuntimeError('auxiliary values changed original masters')
            report['status']='TARGET_FIELD_LIBRARY_COMPLETE_NOT_GLOBAL_QUALITY'
    except BaseException as error:
        failure=error;report.update(status='PAUSED_BUDGET'if isinstance(error,TimeoutError)else'TARGET_VALUE_ERROR',error=str(error),traceback=traceback.format_exc())
    finally:
        active=modules=module=v=None;gc.collect();cleanup_error=library.cleanup(report)
        if failure is None:failure=cleanup_error
        report['wall_seconds']=time.monotonic()-started;stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        library.write_new(directory/f'report_{stamp}.json',report)
        if failure is None:library.write_new(OUT/'values_complete.json',report)
        print('[TARGET_VALUES_END] '+json.dumps({k:report.get(k)for k in('status','wall_seconds','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved target-value attempt')from failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','actual']);parser.add_argument('--resume',action='store_true');a=parser.parse_args()
    if a.phase=='prepare':prepare()
    elif a.phase=='check':verify();print('[TARGET_VALUES_CHECK] sealed source, no model/GPU')
    else:actual(a.resume)


if __name__=='__main__':main()
