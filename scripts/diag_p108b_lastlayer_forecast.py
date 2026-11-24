"""Frozen same-prefix causal forecast, no value fit or final-answer selection."""
import argparse
import gc
import json
import time
import torch
import torch.nn.functional as F
from torch.nn.attention import sdpa_kernel,SDPBackend
from scripts import p108b_pm_frozen as frozen
from scripts import p108b_norm_sweep as limits
from scripts import p108b_lastlayer_forecast as calculations
from scripts import diag_p108b_norm_sweep as study
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_policy as io
from scripts import diag_p108b_value_library as library
from scripts import diag_p108_weight_space as prompts
from scripts import p108b_replay as replay
from scripts.p108b_tinylm import TinyAdapter
from scripts import interactive_research_infer as manual

ROOT,BASE,SOURCE=frozen.ROOT,frozen.BASE,frozen.SOURCE
PROFILE=BASE/'lastlayer_forecast_profile_v1.json'
OUT=BASE/'lastlayer_forecast_v1'
CODE=('scripts/p108b_lastlayer_forecast.py','scripts/test_p108b_lastlayer_forecast.py',
      'scripts/diag_p108b_lastlayer_forecast.py','scripts/p108b_pm_frozen.py',
      'scripts/p108b_replay.py','scripts/interactive_research_infer.py',
      'scripts/diag_p108b_policy.py','scripts/diag_p108_weight_space.py',
      'scripts/diag_p108b_geometry.py','scripts/diag_p108b_value_library.py')


def cases():
    origin=replay.read_arm('original');edited=frozen.arm(frozen.selection()['name'])
    normal=[r for r in origin['answers'] if r['split']!='select_dev' and r['protected'] and r['exact']]
    dev=[r for r in edited['answers'] if r['split']=='select_dev']
    if len(normal)!=7 or len(dev)!=96:raise ValueError('exact reused seven plus96 DEV')
    return normal+dev,dev[:12]


def prepare():
    limits.Budget().check();chosen=frozen.selection();rows,extra=cases()
    p=study.read(study.PROFILE);refs=dict(p['references'])
    for path in (study.PROFILE,BASE/'norm_selection_v1.json',ROOT/chosen['source'],ROOT/chosen['packet']['path']):
        refs[str(path.relative_to(ROOT))]=manual.file_sha(path)
    library.write_new(PROFILE,dict(schema='P108B_LASTLAYER_CAUSAL_FORECAST_V1',authority_directive=141,
        authority_end=limits.AUTHORITY_END.isoformat(),selected=chosen['name'],origin=p['origin'],model=p['parent_model'],
        sources=frozen.source_identity(CODE),references=refs,case_ids=[r['id'] for r in rows],
        extra_prefix_case_ids=[r['id']for r in extra],restore_ids=[r['id']for r in rows if r['split']=='select_dev'][:8],
        max_seconds=600,initial_plan_sha256=manual.file_sha(ROOT/library.PLAN),final_or_official_input=False))
    with (BASE/'lastlayer_forecast_initial_plan_v1.md').open('xb')as stream:stream.write((ROOT/library.PLAN).read_bytes())


def verify():
    limits.Budget().check();p=study.read(PROFILE)
    if p['sources']!=frozen.source_identity(CODE) or p['authority_end']!=limits.AUTHORITY_END.isoformat():
        raise ValueError('exact afternoon source/authority required')
    for path,sha in p['references'].items():
        if manual.file_sha(ROOT/path)!=sha:raise ValueError('exact input changed: '+path)
    if p['initial_plan_sha256']!=manual.file_sha(BASE/'lastlayer_forecast_initial_plan_v1.md'):
        raise ValueError('initial causal plan changed')
    rows,extra=cases()
    if [r['id']for r in rows]!=p['case_ids'] or [r['id']for r in extra]!=p['extra_prefix_case_ids']:
        raise ValueError('predeclared old DEV/normal inputs required')
    return p,rows,extra


def observe(adapter,ids):
    adapter.check();values={};module=adapter.modules[13];model=adapter.model
    def key(_module,args,_out):
        if 'key'in values:raise ValueError('one last physical visit required')
        values['key']=args[0][0,-1].detach().cpu().clone()
    def residual(_module,args):values['residual']=args[0][0,-1].detach().cpu().clone()
    a=module.register_forward_hook(key);b=model.norm_f.register_forward_pre_hook(residual)
    try:
        values['logits']=model(torch.tensor([ids],device='cuda'),logits_last_only=True)[0,-1].detach().cpu().clone()
    finally:a.remove();b.remove()
    return values


def actual():
    p,rows,extra=verify();library.resources();budget=limits.Budget(p['max_seconds'])
    if OUT.exists():raise FileExistsError('preserve previous forecast attempt')
    OUT.mkdir();start=time.monotonic();torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    result=dict(status='STARTED',rows=[],optimizer_updates=0,new_generated_answers=0,checkpoint_writes=0,
        source_profile_sha256=manual.file_sha(PROFILE));failure=None
    active=adapter=module=model=None
    try:
        data=study.read(SOURCE/'data.json');arm=frozen.arm(p['selected']);packet=frozen.packet_loader(arm['packets'][0])
        with manual.selected_runtime(manual.resolve_model(p['model']))as active:
            adapter=TinyAdapter(active,[r for r in data['rows']if r['split']=='fit'],data['calibration_questions'],budget=budget)
            try:
                model=adapter.model;module=adapter.modules[13]
                if (model.visit_schedule()!=list(range(14)) or model.layers[-1].has_lora or model.layers[-1].has_lrm or
                        model.layers[-1].has_film or getattr(model,'_emb_fmt',None) is not None):
                    raise ValueError('one unique float last down followed by supported RMS/linear head required')
                physical=packet['after'].double()-adapter.original[13].double();gate=float(model.layers[13].gates[1])
                if not torch.isfinite(torch.tensor(gate)):raise ValueError('finite native branch gate required')
                entries=[]
                for row in rows:
                    ids=prompts.prompt_ids(active,row['question']);entries.append(dict(id=row['id'],position=0,ids=ids))
                    if row['id']in p['extra_prefix_case_ids']:
                        emitted=list(row['generation']['generated_ids']);terminal=row['generation']['terminal_ids']
                        if terminal:emitted=emitted[:-len(terminal)]
                        if emitted:entries.append(dict(id=row['id'],position=1,ids=ids+emitted[:1]))
                predictions=[];pins=[]
                with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                    for index,item in enumerate(entries):
                        original=observe(adapter,item['ids']);h=original['residual'];key=original['key']
                        shift=(physical@key.double())*gate
                        nonlinear_h=(h.double()+shift).float().to('cuda')
                        nonlinear=model._head_logits(model.norm_f(nonlinear_h[None,None])*model.norm_f_scale)[0,0].cpu()
                        baseline_norm=model.norm_f(h.to('cuda')[None,None])[0,0]
                        differential=calculations.rms_direction(h,shift,model.norm_f.eps).float().to('cuda')
                        linear=model._head_logits(((baseline_norm+differential)*model.norm_f_scale)[None,None])[0,0].cpu()
                        path=OUT/'predictions'/f'case_{index:03d}.npz'
                        pin=atlas.write_npz(path,original_logits=original['logits'],predicted_nonlinear=nonlinear,
                            predicted_linear=linear,original_residual=h,original_key=key,raw_shift=shift.float())
                        predictions.append(dict(item=item,original=original,nonlinear=nonlinear,linear=linear,shift=shift))
                        pins.append(dict(id=item['id'],position=item['position'],packet=pin))
                    library.write_new(OUT/'PREDICTIONS_BEFORE_EDITED_FORWARD_v1.json',dict(pins=pins,
                        prediction_source_profile_sha256=manual.file_sha(PROFILE),edited_native_forward_count_at_seal=0,
                        note='original observations and closed-form forecasts only; frozen edited packet was not refit'))
                    with replay.install(adapter,arm,packets_loader=frozen.packet_loader)as proof:
                        result['weight_replay']=proof
                        for index,entry in enumerate(predictions):
                            item=entry['item'];observed=observe(adapter,item['ids']);original=entry['original']
                            if not torch.equal(observed['key'],original['key']):raise RuntimeError('last-layer-only edit unexpectedly changed its own input key')
                            predicted_residual=original['residual'].double()+entry['shift']
                            logp=observed['logits'].double().log_softmax(-1);oldlp=original['logits'].double().log_softmax(-1)
                            detail=dict(id=item['id'],position=item['position'],input_key_exact=True,
                                branch_gate=gate,raw_shift_norm=float(entry['shift'].norm()),
                                original_residual_norm=float(original['residual'].norm()),
                                residual_max_error=float((observed['residual'].double()-predicted_residual).abs().max()),
                                linear=calculations.compare(original['logits'],observed['logits'],entry['linear']),
                                nonlinear=calculations.compare(original['logits'],observed['logits'],entry['nonlinear']),
                                original_top=int(original['logits'].argmax()),edited_top=int(observed['logits'].argmax()),
                                original_top_text=active['tokenizer'].decode([int(original['logits'].argmax())]),
                                edited_top_text=active['tokenizer'].decode([int(observed['logits'].argmax())]),
                                original_eot_probability=float(oldlp[4].exp()),edited_eot_probability=float(logp[4].exp()),
                                original_eos_probability=float(oldlp[2].exp()),edited_eos_probability=float(logp[2].exp()))
                            if item['position']==0 and item['id']in p['restore_ids']:
                                base=adapter.original[13].to(module.weight)
                                def restore(_module,args,_out):return F.linear(args[0],base)
                                handle=module.register_forward_hook(restore)
                                try:restored=observe(adapter,item['ids'])
                                finally:handle.remove()
                                detail['restore_original_down_output']=dict(max_logit_error=float((restored['logits']-original['logits']).abs().max()),
                                    exact_argmax=bool(restored['logits'].argmax()==original['logits'].argmax()))
                                base=None
                            detail['actual_packet']=atlas.write_npz(OUT/'actual'/f'case_{index:03d}.npz',
                                actual_logits=observed['logits'],actual_residual=observed['residual'],actual_key=observed['key'])
                            result['rows'].append(detail)
                    result['original_core_restored']=proof['original_core_restored']
                result.update(status='LASTLAYER_CAUSAL_FORECAST_COMPLETE',native_observation_forwards=2*len(entries)+len(p['restore_ids']),
                    prediction_sealed_before_actual=True,model_counts=dict(adapter.counts))
            finally:
                if adapter is not None:adapter.close()
        active=adapter=module=model=None
    except BaseException as error:failure=error;result.update(status='LASTLAYER_FORECAST_ERROR',error=str(error))
    finally:
        active=adapter=module=model=None
        base=nonlinear_h=baseline_norm=differential=None
        gc.collect();cleanup_error=library.cleanup(result)
        if failure is None:failure=cleanup_error
        result['wall_seconds']=time.monotonic()-start;library.write_new(OUT/'report.json',result)
        print('[LASTLAYER_FORECAST_END] '+json.dumps({k:result.get(k)for k in ('status','native_observation_forwards','wall_seconds','original_core_restored','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved last-layer forecast failure')from failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','actual']);args=parser.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='check':verify();print('LASTLAYER_CPU_PREFLIGHT_NO_MODEL')
    else:actual()


if __name__=='__main__':main()
