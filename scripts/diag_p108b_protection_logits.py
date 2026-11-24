#!/usr/bin/env python3
"""Measure actual native logits of seven preserved copy paths, no generation."""
import argparse
import gc
import json
import time
import torch
import torch.nn.functional as F
from torch.nn.attention import sdpa_kernel,SDPBackend
from scripts import diag_p108b_target_protection as parent
from scripts import diag_p108b_value_library as library
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_policy as io
from scripts import diag_p108_query_value as query
from scripts.p108b_tinylm import TinyAdapter
from scripts import interactive_research_infer as manual

BASE=atlas.BASE
OUT=BASE/'target_protection_logits_v1'
PROFILE=BASE/'target_protection_logits_profile_v1.json'
INITIAL=BASE/'target_protection_logits_initial_plan_v1.md'
CODE=('scripts/diag_p108b_protection_logits.py','scripts/test_p108b_protection_logits.py')

def compare(reference,actual,targets):
    if(reference.ndim!=2 or actual.shape!=reference.shape or targets.shape!=(len(reference),)or
       any(not bool(torch.isfinite(t).all())for t in(reference,actual))):raise ValueError('same complete target logits required')
    r=reference.double().log_softmax(-1);a=actual.double().log_softmax(-1)
    difference=(actual.double()-reference.double()).abs()
    return dict(max_absolute_logit_difference=float(difference.max()),rms_logit_difference=float(difference.square().mean().sqrt()),
        mean_original_to_edited_kl=float(F.kl_div(a,r,log_target=True,reduction='sum')/len(r)),
        changed_argmax_positions=int((reference.argmax(-1)!=actual.argmax(-1)).sum()),
        target_logp_before=r.gather(1,targets[:,None]).flatten().tolist(),
        target_logp_after=a.gather(1,targets[:,None]).flatten().tolist(),
        target_ids=targets.tolist(),prediction_positions=len(targets))

def prepare():
    parent.verify();report=json.loads((parent.OUT/'report.json').read_text())
    if not report['original_core_restored']or report['cuda_allocated_after_bytes']or report['cuda_reserved_after_bytes']:
        raise ValueError('closed four-arm protection experiment required')
    library.write_new(PROFILE,dict(sources={n:manual.file_sha(atlas.ROOT/n)for n in CODE},
        parent_profile_sha256=manual.file_sha(parent.PROFILE),report_sha256=manual.file_sha(parent.OUT/'report.json'),
        packet_sha256={a['name']:manual.file_sha(atlas.ROOT/a['packet']['path'])for a in report['arms']},
        initial_plan_sha256=manual.file_sha(atlas.ROOT/library.PLAN),new_generated_answers=0,max_seconds=120))
    with INITIAL.open('xb')as stream:stream.write((atlas.ROOT/library.PLAN).read_bytes())

def verify():
    model,_,_=parent.verify();p=json.loads(PROFILE.read_text())
    if(p['parent_profile_sha256']!=manual.file_sha(parent.PROFILE)or p['report_sha256']!=manual.file_sha(parent.OUT/'report.json')or
       p['initial_plan_sha256']!=manual.file_sha(INITIAL)):
        raise ValueError('closed parent binding changed')
    for name,sha in p['sources'].items():
        if manual.file_sha(atlas.ROOT/name)!=sha:raise ValueError('logit source changed')
    return model,p,json.loads((parent.OUT/'report.json').read_text())

def observe(adapter,rows,directory):
    result={}
    for row in rows:
        adapter.check();item=query.pack(adapter.active,row)
        with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
            hidden=adapter.model(item['x'],return_hidden=True)
            logits=adapter.model._head_logits(hidden[:,item['start']:])[0].detach().cpu()
        targets=item['targets'].detach().cpu()
        if len(logits)!=len(targets):raise ValueError('native shifted target window differs')
        path=directory/('case_'+row['id'].replace(':','_')+'.npz')
        atlas.write_npz(path,logits=logits,targets=targets)
        result[row['id']]=(logits,targets)
    return result

def model_run(model,p,source):
    data=json.loads((BASE/'data.json').read_text());fits=[r for r in data['rows']if r['split']=='fit']
    rows=[r for r in data['rows']if r['id']in source['protected_original_ids']]
    budget=library.Budget(p['max_seconds']);result=dict(models={},body_optimizer_updates=0,value_optimizer_updates=0,new_generated_answers=0,checkpoint_writes=0)
    if len(rows)!=7:raise ValueError('exact seven already-correct input paths required')
    with manual.selected_runtime(manual.resolve_model(model['model']))as active:
        adapter=TinyAdapter(active,fits,data['calibration_questions'],kl_weight=model['optimizer']['kl_weight'],budget=budget)
        try:
            baseline=observe(adapter,rows,OUT/'original')
            for arm in source['arms']:
                if manual.file_sha(atlas.ROOT/arm['packet']['path'])!=p['packet_sha256'][arm['name']]:raise ValueError('saved physical packet changed')
                packet=io.npz_tensors(atlas.ROOT/arm['packet']['path'])
                with adapter.edit(13,packet['requested']):
                    if manual.state_fingerprint(active['model'])!=arm['edited_core_sha256']:raise RuntimeError('exact edited core replay differs')
                    current=observe(adapter,rows,OUT/arm['name'])
                result['models'][arm['name']]={i:compare(baseline[i][0],current[i][0],baseline[i][1])for i in baseline}
            result.update(original_core_restored=manual.state_fingerprint(active['model'])==model['origin']['core_sha256'],
                native_target_forwards=35,counts=dict(adapter.counts))
            if not result['original_core_restored']:raise RuntimeError('native logits did not restore original')
        finally:adapter.close()
    return result

def actual():
    model,p,source=verify();library.resources();torch.set_num_threads(4)
    if OUT.exists():raise FileExistsError('preserve original native logit attempt')
    OUT.mkdir();start=time.monotonic();report={};failure=None
    try:report=model_run(model,p,source);report['status']='NATIVE_PROTECTED_LOGITS_COMPLETE'
    except BaseException as error:failure=error;report.update(status='NATIVE_PROTECTED_LOGITS_ERROR',error=str(error))
    finally:
        gc.collect();cleanup_error=library.cleanup(report)
        if failure is None:failure=cleanup_error
        report['wall_seconds']=time.monotonic()-start;library.write_new(OUT/'report.json',report)
    print(json.dumps({k:report.get(k)for k in('status','wall_seconds','native_target_forwards','original_core_restored','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved native protection logit failure')from failure

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','actual']);a=parser.parse_args()
    if a.phase=='prepare':prepare()
    elif a.phase=='check':verify();print('PROTECTED_LOGIT_PREFLIGHT_MODEL0')
    else:actual()

if __name__=='__main__':main()
