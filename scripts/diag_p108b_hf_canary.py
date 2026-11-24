#!/usr/bin/env python3
"""Native HF all-layer derivative/physical-write admission, not quality transfer.

One fixed FIT question and negative-gradient proposals test numerical adapter
semantics. This is explicitly not the TinyLM value-library policy comparison.
"""
from contextlib import contextmanager
import argparse
import gc
import json
import time
import traceback
import torch
import torch.nn.functional as F
from scripts import diag_p106b_external_core6 as external
from scripts import diag_p108b_value_library as library
from scripts import diag_p108b_geometry as atlas
from scripts import interactive_research_infer as manual
from scripts import p108_value_edit as positions
from scripts import p108_weight_space as metrics

BASE=atlas.BASE
OUT=BASE/'hf_canary_v1'
CODE=('scripts/diag_p108b_hf_canary.py','scripts/test_p108b_hf_canary.py',
      'scripts/diag_p106b_external_core6.py')


def modules(body):
    layers=body.model.layers
    result={i:layer.mlp.down_proj for i,layer in enumerate(layers)}
    if not result or any(not isinstance(m,torch.nn.Linear)or m.bias is not None for m in result.values()):
        raise ValueError('native biasless MLP down projections required')
    if len({m.weight.data_ptr()for m in result.values()})!=len(result):raise ValueError('aliased layers need another adapter')
    if any(m.weight.dtype!=torch.float32 for m in result.values()):raise ValueError('explicit float32 required')
    return result


@contextmanager
def edit(module,delta):
    before=module.weight.detach().clone()
    if delta.shape!=before.shape or delta.dtype!=before.dtype or not bool(torch.isfinite(delta).all()):
        raise ValueError('same finite native matrix shape/dtype required')
    try:
        with torch.no_grad():module.weight.copy_(before+delta)
        yield
    finally:
        with torch.no_grad():module.weight.copy_(before)
        if not torch.equal(module.weight,before):raise RuntimeError('native HF weight rollback differs')


def prepare():
    assets=external.asset_identity('gemma270')
    config=external.read_json(assets['files']['config.json']['resolved_path'])
    validate_config(config)
    profile=dict(schema='P108B_HF_NATIVE_CANARY_V1',model='gemma270',assets=assets,
        sources={n:manual.file_sha(atlas.ROOT/n)for n in CODE},max_seconds=1800,
        source_question='What is the capital of Germany? Return only the city name.',expected='Berlin',
        prompt_prefix='Question: ',prompt_suffix='\nAnswer:',answer_prefix=' ',
        scope='ONE_FIXED_FIT_QUESTION_TECHNICAL_ADAPTER_ONLY_NOT_VALUE_POLICY_OR_GENERAL_QUALITY',
        proposal='negative complete parameter gradient; same absolute norm per layer',
        relative_cap=.01,finite_epsilons=[.001,.003],max_new=32,
        body_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0,
        initial_plan_sha256=manual.file_sha(atlas.ROOT/library.PLAN))
    library.write_new(BASE/'hf_canary_profile_v1.json',profile)
    with(BASE/'hf_canary_initial_plan_v1.md').open('xb')as f:f.write((atlas.ROOT/library.PLAN).read_bytes())
    print('[HF_CANARY_PREPARED] existing Gemma18 native numerical admission only; no model/GPU',flush=True)


def validate_config(fields):
    if fields.get('num_hidden_layers')!=18 or fields.get('hidden_activation')!='gelu_pytorch_tanh':
        raise ValueError('actual serialized Gemma GeGLU18 hidden_activation field required')


def verify():
    library.Budget().check();p=json.loads((BASE/'hf_canary_profile_v1.json').read_text(encoding='utf-8'))
    for name,sha in p['sources'].items():
        if manual.file_sha(atlas.ROOT/name)!=sha:raise ValueError('HF admission source changed')
    if external.asset_identity(p['model'])!=p['assets']:raise ValueError('exact external asset bytes changed')
    if manual.file_sha(BASE/'hf_canary_initial_plan_v1.md')!=p['initial_plan_sha256']:raise ValueError('initial HF plan changed')
    return p


def run():
    p=verify();library.resources();budget=library.Budget(p['max_seconds']);torch.set_num_threads(4)
    if OUT.exists():raise FileExistsError('preserve prior HF canary')
    OUT.mkdir(parents=True);started=time.monotonic();body=lm=None;failure=None
    report=dict(schema=p['schema'],status='STARTED',scope=p['scope'],layers=[],external_runtime_proof={},
        source_profile_sha256=manual.file_sha(BASE/'hf_canary_profile_v1.json'),new_training_updates=0,checkpoint_writes=0)
    tf32=(torch.backends.cuda.matmul.allow_tf32,torch.backends.cudnn.allow_tf32,torch.get_float32_matmul_precision())
    try:
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.set_float32_matmul_precision('highest')
        with external.model_runtime(p['model'],torch,p['assets'],proof=report['external_runtime_proof'])as (lm,_):
            body=lm.model;tok=lm.tokenizer;downs=modules(body)
            validate_config(body.config.to_dict())
            if len(downs)!=18:raise ValueError('native18 layer admission differs')
            text=p['prompt_prefix']+p['source_question']+p['prompt_suffix']
            prompt=tok.encode(text,add_special_tokens=True);joint=tok.encode(text+p['answer_prefix']+p['expected'],add_special_tokens=True)
            if joint[:len(prompt)]!=prompt:raise ValueError('native prompt/answer token boundary merges; no silent repair')
            target=joint[len(prompt):]+[tok.eos_token_id]
            if not target or tok.eos_token_id!=body.config.eos_token_id:raise ValueError('explicit native EOS required')
            ids=torch.tensor([prompt+target[:-1]],device='cuda');labels=torch.tensor(target,device='cuda')
            def nll():
                budget.check();logits=body(input_ids=ids,use_cache=False,logits_to_keep=len(target)).logits
                return F.cross_entropy(logits[0].float(),labels)
            def generate():
                budget.check()
                with torch.no_grad():
                    answer=body.generate(torch.tensor([prompt],device='cuda'),attention_mask=torch.ones(1,len(prompt),device='cuda',dtype=torch.long),
                        do_sample=False,max_new_tokens=p['max_new'],use_cache=False,pad_token_id=tok.eos_token_id)
                generated=answer[0,len(prompt):].tolist()
                return dict(answer=tok.decode(generated,skip_special_tokens=True),generated_ids=generated)
            saved={};handles=[]
            for index,module in downs.items():
                def retain(m,args,output,index=index):
                    if index in saved:raise RuntimeError('repeated visit needs another adapter')
                    native=F.linear(args[0],m.weight)
                    if not torch.equal(native,output):raise RuntimeError('native HF full-shape projection replay differs')
                    saved[index]=True
                handles.append(module.register_forward_hook(retain))
            try:
                with torch.no_grad():baseline=float(nll())
            finally:
                for handle in handles:handle.remove()
            if set(saved)!=set(downs):raise ValueError('all18 native projections must be observed')
            report.update(native_projection_zero_max_error=0,baseline_nll=baseline,baseline_answer=generate(),
                parameter_count=sum(x.numel()for x in body.parameters()),native_eos=tok.eos_token_id,prompt_ids=prompt,targets=target)
            loss=nll();gradients=torch.autograd.grad(loss,[m.weight for m in downs.values()]);loss=None
            budget_norm=.01*min(float(m.weight.double().norm())for m in downs.values())
            report['common_absolute_norm']=budget_norm;original=manual.state_fingerprint(body)
            for(index,module),gradient in zip(downs.items(),gradients):
                budget.check();direction=-gradient.detach()*budget_norm/gradient.detach().double().norm().to(gradient)
                predicted=-float((gradient.double()*direction.double()).sum());finite=[]
                for epsilon in p['finite_epsilons']:
                    values=[]
                    for sign in(1,-1):
                        with edit(module,direction*(sign*epsilon)),torch.no_grad():values.append(float(nll()))
                    finite.append(dict(epsilon=epsilon,central_gain=(values[1]-values[0])/(2*epsilon)))
                before=module.weight.detach().cpu().clone()
                with edit(module,direction),torch.no_grad():
                    actual=float(nll());answer=generate();after=module.weight.detach().cpu().clone()
                packet=atlas.write_npz(OUT/f'layer{index:02d}_packet.npz',requested=direction.cpu(),after=after)
                report['layers'].append(dict(layer=index,predicted_gain=predicted,actual_gain=baseline-actual,
                    finite_difference=finite,answer=answer,actual_norm=float((after.double()-before.double()).norm()),
                    before_weight_sha256=metrics.tensor_sha(before),after_weight_sha256=metrics.tensor_sha(after),packet=packet))
                if manual.state_fingerprint(body)!=original:raise RuntimeError('full external core not restored after layer')
                print('[HF_LAYER_CANARY] '+json.dumps({k:report['layers'][-1][k]for k in('layer','predicted_gain','actual_gain','finite_difference')}),flush=True)
            if any(parameter.grad is not None for parameter in body.parameters()):raise RuntimeError('native canary created persistent body gradients')
            report['status']='HF_NATIVE18_TECHNICAL_COMPLETE_NOT_VALUE_POLICY_TRANSFER'
            gradients=gradient=direction=module=downs=body=lm=ids=labels=loss=handles=None
    except BaseException as error:
        failure=error;report.update(status='HF_NATIVE_CANARY_ERROR',error=str(error),traceback=traceback.format_exc())
    finally:
        gradients=gradient=direction=module=downs=body=lm=ids=labels=loss=handles=None
        gc.collect();cleanup_error=library.cleanup(report)
        if failure is None:failure=cleanup_error
        torch.backends.cuda.matmul.allow_tf32,torch.backends.cudnn.allow_tf32=tf32[:2];torch.set_float32_matmul_precision(tf32[2])
        report['wall_seconds']=time.monotonic()-started;library.write_new(OUT/'report.json',report)
        print('[HF_CANARY_END] '+json.dumps({k:report.get(k)for k in('status','wall_seconds','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved HF adapter canary failure')from failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','actual']);a=parser.parse_args()
    if a.phase=='prepare':prepare()
    elif a.phase=='check':verify();print('[HF_CANARY_CHECK] source/native assets only; no model/GPU')
    else:run()


if __name__=='__main__':main()
