"""Read-only asset reuse and native two-norm forecast validation on Gemma18."""
import argparse
import gc
import json
from pathlib import Path
import time
import torch
from torch.nn.attention import sdpa_kernel,SDPBackend
from scripts import diag_p108b_hf_canary as previous
from scripts import diag_p106b_external_core6 as external
from scripts import diag_p108b_norm_sweep as study
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_value_library as library
from scripts import diag_p108b_policy as io
from scripts import p108b_hf_suffix_forecast as forecast
from scripts import p108b_lastlayer_forecast as compare
from scripts import p108b_norm_sweep as limits
from scripts import p108b_pm_frozen as pins
from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as metrics

ROOT,BASE,SOURCE=study.ROOT,study.BASE,study.SOURCE
PROFILE=BASE/'hf_suffix_profile_v1.json';OUT=BASE/'hf_suffix_v1'
INDICES=(0,1,2,3,32,33,64,65,96,97,126,127)
CODE=('scripts/p108b_hf_suffix_forecast.py','scripts/test_p108b_hf_suffix_forecast.py',
      'scripts/diag_p108b_hf_suffix_forecast.py','scripts/p108b_lastlayer_forecast.py',
      'scripts/p108b_pm_frozen.py','scripts/diag_p108b_hf_canary.py',*external.SOURCES)


def prepare():
    from transformers.models.gemma3 import modeling_gemma3
    limits.Budget().check();parent=study.read(SOURCE/'hf_canary_profile_v1.json')
    closed=study.read(SOURCE/'hf_canary_v1/report.json');record=closed['layers'][-1]
    if closed['status']!='HF_NATIVE18_TECHNICAL_COMPLETE_NOT_VALUE_POLICY_TRANSFER' or record['layer']!=17:
        raise ValueError('closed native18 technical observation required')
    assets=external.asset_identity('gemma270')
    if assets!=parent['assets']:raise ValueError('unchanged already-admitted local asset required')
    library.write_new(PROFILE,dict(schema='P108B_HF_SUFFIX_FORECAST_V1',authority_directive=141,
        authority_end=limits.AUTHORITY_END.isoformat(),sources=pins.source_identity(CODE),assets=assets,
        model_source_path=modeling_gemma3.__file__,model_source_sha256=manual.file_sha(Path(modeling_gemma3.__file__)),
        old_report_sha256=manual.file_sha(SOURCE/'hf_canary_v1/report.json'),packet=record['packet'],
        before_weight_sha256=record['before_weight_sha256'],calibration_data_sha256=manual.file_sha(SOURCE/'data.json'),
        calibration_indices=list(INDICES),alphas=[1.,4.,16.],max_seconds=600,
        initial_plan_sha256=manual.file_sha(ROOT/library.PLAN),new_fit_or_generation=False,
        scope='TWO_ARCHITECTURE_SUFFIX_NUMERICS_NOT_GENERAL_EDIT_QUALITY'))
    with(BASE/'hf_suffix_initial_plan_v1.md').open('xb')as stream:stream.write((ROOT/library.PLAN).read_bytes())


def verify():
    limits.Budget().check();p=study.read(PROFILE)
    if p['authority_end']!=limits.AUTHORITY_END.isoformat() or p['sources']!=pins.source_identity(CODE):
        raise ValueError('current exact authority/source required')
    if external.asset_identity('gemma270')!=p['assets'] or manual.file_sha(Path(p['model_source_path']))!=p['model_source_sha256']:
        raise ValueError('strict original external assets/runtime code changed')
    for file,key in [('hf_canary_v1/report.json','old_report_sha256'),('data.json','calibration_data_sha256')]:
        if manual.file_sha(SOURCE/file)!=p[key]:raise ValueError('immutable source changed')
    if manual.file_sha(BASE/'hf_suffix_initial_plan_v1.md')!=p['initial_plan_sha256']:raise ValueError('initial plan changed')
    ref=p['packet'];path=ROOT/ref['path']
    if manual.file_sha(path)!=ref['sha256']:raise ValueError('immutable old physical packet changed')
    return p


def observe(body,down,ids):
    captured={};last=body.model.layers[-1]
    def hook(_module,args,output):
        if 'key'in captured:raise ValueError('unique final-layer physical visit required')
        captured.update(key=args[0][0,-1].cpu().clone(),down_output=output[0,-1].cpu().clone())
    def residual(_module,args):captured['residual']=args[0][0,-1].cpu().clone()
    a=down.register_forward_hook(hook);b=last.pre_feedforward_layernorm.register_forward_pre_hook(residual)
    try:captured['logits']=body(input_ids=ids,use_cache=False,logits_to_keep=1).logits[0,-1].cpu().clone()
    finally:a.remove();b.remove()
    return captured


def actual():
    p=verify();library.resources();budget=limits.Budget(600);torch.set_num_threads(4)
    if OUT.exists():raise FileExistsError('preserve previous external suffix attempt')
    OUT.mkdir();start=time.monotonic();failure=None
    report=dict(status='STARTED',external_runtime_proof={},rows=[],new_generated_answers=0,
        optimizer_updates=0,checkpoint_writes=0,source_profile_sha256=manual.file_sha(PROFILE),scope=p['scope'])
    body=lm=down=layer=ids=exact=linear=delta_gpu=None
    try:
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        with external.model_runtime('gemma270',torch,p['assets'],proof=report['external_runtime_proof'])as(lm,_):
            body=lm.model;tok=lm.tokenizer;layer=body.model.layers[-1];down=previous.modules(body)[17]
            if len(body.model.layers)!=18 or metrics.tensor_sha(down.weight)!=p['before_weight_sha256']:
                raise ValueError('same native last17 original matrix required')
            if any(type(m).__name__!='Gemma3RMSNorm'for m in (layer.post_feedforward_layernorm,body.model.norm)):
                raise ValueError('verified Gemma two-norm path required')
            base=down.weight.detach().cpu().clone();old=io.npz_tensors(ROOT/p['packet']['path'])['requested']
            data=study.read(SOURCE/'data.json')['calibration_questions'];originals=[];predictions=[];references=[]
            with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                for index in p['calibration_indices']:
                    budget.check();question=data[index];text='Question: '+question+'\nAnswer:'
                    native_ids=tok.encode(text,add_special_tokens=True);ids=torch.tensor([native_ids],device='cuda')
                    originals.append(dict(index=index,question=question,ids=native_ids,values=observe(body,down,ids)))
                for alpha in p['alphas']:
                    requested=(old.double()*alpha).float();after=base+requested;physical=after.double()-base.double()
                    for item in originals:
                        budget.check();v=item['values'];change=(physical@v['key'].double()).float().to('cuda')
                        exact,linear=forecast.predict(layer.post_feedforward_layernorm,body.model.norm,body.lm_head,
                            v['residual'].to('cuda'),v['down_output'].to('cuda'),change,body.config.final_logit_softcapping)
                        exact=exact.cpu();linear=linear.cpu()
                        ref=atlas.write_npz(OUT/'predictions'/f"a{int(alpha):02d}_case{item['index']:03d}.npz",
                            original=v['logits'],predicted_exact=exact,predicted_linear=linear,
                            original_key=v['key'],original_residual=v['residual'],original_down=v['down_output'])
                        references.append(dict(alpha=alpha,index=item['index'],packet=ref))
                        predictions.append(dict(alpha=alpha,item=item,exact=exact,linear=linear,requested=requested,
                            physical_norm=float(physical.norm())))
                library.write_new(OUT/'PREDICTIONS_BEFORE_NATIVE_EDITS_v1.json',dict(references=references,edited_native_forwards=0))
                for alpha in p['alphas']:
                    requested=(old.double()*alpha).float()
                    with previous.edit(down,requested.to(down.weight)):
                        for entry in [x for x in predictions if x['alpha']==alpha]:
                            item=entry['item'];ids=torch.tensor([item['ids']],device='cuda');actual=observe(body,down,ids);original=item['values']
                            if not torch.equal(original['key'],actual['key']) or not torch.equal(original['residual'],actual['residual']):
                                raise RuntimeError('last-only write unexpectedly changed preceding key/residual')
                            report['rows'].append(dict(alpha=alpha,calibration_index=item['index'],question=item['question'],
                                physical_norm=entry['physical_norm'],relative_weight_change=entry['physical_norm']/float(base.double().norm()),
                                actual_key_and_residual_exact=True,linear=compare.compare(original['logits'],actual['logits'],entry['linear']),
                                nonlinear=compare.compare(original['logits'],actual['logits'],entry['exact']),
                                actual_packet=atlas.write_npz(OUT/'actual'/f"a{int(alpha):02d}_case{item['index']:03d}.npz",logits=actual['logits'])))
                    if metrics.tensor_sha(down.weight)!=p['before_weight_sha256']:raise RuntimeError('original HF last matrix not restored')
            report.update(status='HF_SUFFIX_NATIVE36_COMPLETE_NOT_QUALITY',native_forwards=48,
                two_norm_convention='Gemma3:postFFN RMS1+weight,residual,final RMS1+weight,linear head,optional softcap',
                softcap=body.config.final_logit_softcapping,all_predictions_frozen_before_native=True)
            body=lm=down=layer=ids=exact=linear=delta_gpu=change=None
    except BaseException as error:failure=error;report.update(status='HF_SUFFIX_ERROR',error=str(error))
    finally:
        body=lm=down=layer=ids=exact=linear=delta_gpu=change=None;gc.collect();cleanup_error=library.cleanup(report)
        if failure is None:failure=cleanup_error
        report['wall_seconds']=time.monotonic()-start;library.write_new(OUT/'report.json',report)
        print('[HF_SUFFIX_END] '+json.dumps({k:report.get(k)for k in ('status','native_forwards','wall_seconds','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved external suffix observation failure')from failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','actual']);args=parser.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='check':verify();print('HF_SUFFIX_CPU_SOURCE_CHECK_NO_MODEL')
    else:actual()


if __name__=='__main__':main()
