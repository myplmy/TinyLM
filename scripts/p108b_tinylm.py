"""Opt-in completed-TinyLM adapter for full-path edit prediction and replay.

Existing strict loading, shifted targets, float weight intervention and product
generation are delegated to their owners. Only float untied R1 is supported;
other routes require separate adapters rather than relaxed guards.
"""
from __future__ import annotations

from contextlib import contextmanager
import math

import tinylm
import torch
import torch.nn.functional as F
from torch.nn.attention import sdpa_kernel, SDPBackend

from scripts import interactive_research_infer as manual
from scripts import diag_p108_value_edit as loss_owner
from scripts import diag_p108_query_value as query
from scripts import diag_p108_weight_space as prompts
from scripts import p108_value_edit as value
from scripts import p108_wsp_attention as wsp
from scripts import p108_weight_space as metrics
from scripts import p108_joint_write as covariance_owner


class TinyAdapter:
    def __init__(self, active, fits, calibration, *, kl_weight=.0625, budget=None):
        self.active, self.model = active, active['model']
        if active['route'].mode!='float' or self.model.training:
            raise ValueError('strict completed float eval route required')
        self.modules={i:m for key,m in wsp.outputs(self.model).items()
                      if key.startswith('mlp:') for i in [int(key.split(':')[1])]}
        if sorted(self.modules)!=list(range(14)):
            raise ValueError('this adapter requires the complete14 physical layers')
        if len({m.weight.data_ptr() for m in self.modules.values()})!=14:
            raise ValueError('aliased parameters need a different ownership-aware adapter')
        if (len(fits)!=24 or len(calibration)!=128 or
                any(r['split']!='fit' for r in fits) or
                not math.isfinite(kl_weight) or kl_weight<0):
            raise ValueError('sealed24 FIT/128 calibration and finite KL coefficient required')
        self.fits, self.calibration, self.kl_weight = fits, calibration, kl_weight
        self.budget=budget
        self.original={i:m.weight.detach().cpu().clone() for i,m in self.modules.items()}
        self.packeds={r['id']:query.pack(active,r) for r in fits}
        self.counts=dict(model_forwards=0, supervised_target_tokens_gradient=0,
                         objective_calls=0, gradient_calls=0, generated_calls=0,
                         native_projection_replays=0)
        def count(_module,_args):self.counts['model_forwards']+=1
        self.counter=self.model.register_forward_pre_hook(count)
        with torch.no_grad():
            self.references=[self.logp(q).detach().cpu() for q in calibration]

    def check(self):
        if self.budget is not None:self.budget.check()
        self.active['route'].assert_active()

    def logp(self, question):
        self.check()
        return loss_owner.prompt_log_probs(self.active,dict(question=question))

    def current(self):
        return {i:m.weight.detach().cpu().clone() for i,m in self.modules.items()}

    def displacement(self):
        return {i:m.weight.detach().cpu().double()-self.original[i].double()
                for i,m in self.modules.items()}

    def objective(self, *, gradient=False, directions=None):
        """Mean question CE + mean original-prompt KL; no persistent .grad."""
        self.check();self.counts['objective_calls']+=1
        weights=[self.modules[i].weight for i in range(14)]
        accumulated=[torch.zeros_like(w) for w in weights] if gradient else None
        ce=[];kl=[];directional={}
        if directions is not None:
            if not gradient or set(directions)!=set(range(14)):
                raise ValueError('per-case prediction requires all14 frozen directions and gradients')
            directions_gpu={i:directions[i].to(weights[i]) for i in range(14)}
        with torch.set_grad_enabled(gradient), value.freeze_parameters(self.model):
            for row in self.fits:
                self.check()
                if gradient:value.refresh_autograd_views(self.model,self.active['route'])
                loss=loss_owner.target_nll(self.active,self.packeds[row['id']])
                ce.append(float(loss.detach()))
                if gradient:
                    derivatives=torch.autograd.grad(loss/len(self.fits),weights)
                    if directions is not None:
                        directional[row['id']]={i:-float((g*directions_gpu[i]).sum())*len(self.fits)
                                                for i,g in enumerate(derivatives)}
                    for target,g in zip(accumulated,derivatives):target.add_(g)
                    self.counts['supervised_target_tokens_gradient']+=len(self.packeds[row['id']]['targets'])
                    del derivatives
            for question,reference in zip(self.calibration,self.references):
                self.check()
                if gradient:value.refresh_autograd_views(self.model,self.active['route'])
                logp=self.logp(question)
                divergence=F.kl_div(logp,reference.to(logp),log_target=True,reduction='sum')
                kl.append(float(divergence.detach()))
                if gradient and self.kl_weight:
                    derivatives=torch.autograd.grad(divergence*(self.kl_weight/len(self.references)),weights)
                    for target,g in zip(accumulated,derivatives):target.add_(g)
                    del derivatives
        result=dict(fit_ce=sum(ce)/len(ce),preserve_kl=sum(kl)/len(kl),
                    fit_ce_by_id={r['id']:v for r,v in zip(self.fits,ce)},
                    calibration_items=len(kl),kl_weight=self.kl_weight)
        result['J']=result['fit_ce']+self.kl_weight*result['preserve_kl']
        if directions is not None:
            result['predicted_fit_gain_by_id']=directional
        if not all(math.isfinite(result[k]) for k in ('fit_ce','preserve_kl','J')):
            raise RuntimeError('nonfinite common final objective')
        if gradient:
            self.counts['gradient_calls']+=1
            gradients={i:g.detach().cpu().double() for i,g in enumerate(accumulated)}
            if any(not bool(torch.isfinite(g).all()) for g in gradients.values()):
                raise RuntimeError('nonfinite full-path parameter derivative')
            del accumulated
            return result,gradients
        return result

    def capture_fit(self, rows=None, *, keys=True, native_check=True):
        """Native whole-prefix path; shared endpoint is after the true last layer."""
        selected=self.fits if rows is None else rows
        key_parts={i:[] for i in self.modules};value_parts={i:[] for i in self.modules}
        prefix=[];answer=[];forwards=[]
        for row in selected:
            self.check();item=self.packeds.get(row['id'])
            if item is None:item=query.pack(self.active,row)
            saved={};handles=[]
            if keys:
                for index,module in self.modules.items():
                    def retain(module,args,output,index=index):
                        if index in saved:raise RuntimeError('repeated logical visit in R1 adapter')
                        if native_check:
                            with torch.no_grad(),torch.autocast('cuda',enabled=False):
                                replay=F.linear(args[0],module.weight)
                            if not torch.equal(replay,output):
                                raise RuntimeError('same-shape native FP32 projection replay differs')
                            self.counts['native_projection_replays']+=1
                        saved[index]=(args[0][0,item['position']].detach().cpu().clone(),
                                      output[0,item['position']].detach().cpu().clone())
                    handles.append(module.register_forward_hook(retain))
            def endpoint(_module,_args,output):
                if 'endpoint' in saved or not isinstance(output,torch.Tensor):
                    raise RuntimeError('last physical block endpoint contract differs')
                saved['endpoint']=output[0].detach().cpu().clone()
            handles.append(self.model.layers[-1].register_forward_hook(endpoint))
            try:
                with torch.no_grad():ce=loss_owner.target_nll(self.active,item)
            finally:
                for handle in reversed(handles):handle.remove()
            if keys and {i for i in saved if isinstance(i,int)}!=set(range(14)):
                raise RuntimeError('incomplete14-layer capture')
            if keys:
                for i in self.modules:
                    key_parts[i].append(saved[i][0]);value_parts[i].append(saved[i][1])
            prefix.append(saved['endpoint'][:len(item['prompt_ids'])])
            answer.append(saved['endpoint'][item['start']:])
            forwards.append(dict(id=row['id'],target_count=len(item['targets']),ce=float(ce),
                                 prompt_tokens=len(item['prompt_ids'])))
        return dict(keys={i:torch.stack(v,dim=1).double() for i,v in key_parts.items()} if keys else {},
                    values={i:torch.stack(v,dim=1).double() for i,v in value_parts.items()} if keys else {},
                    prefix_endpoint=torch.cat(prefix).double(),answer_endpoint=torch.cat(answer).double(),
                    rows=forwards,endpoint_layer=13)

    def calibration_moments(self, *, return_samples=False):
        parts={i:[] for i in self.modules};handles=[]
        for index,module in self.modules.items():
            def retain(_module,args,_output,index=index):
                parts[index].append(args[0][0,-8:].detach().cpu().clone())
            handles.append(module.register_forward_hook(retain))
        try:
            with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                for question in self.calibration:
                    self.check();ids=prompts.prompt_ids(self.active,question)
                    self.model(torch.tensor([ids],device='cuda'),logits_last_only=True)
        finally:
            for h in reversed(handles):h.remove()
        moments={};stats={};samples={}
        for i,parts_i in parts.items():
            if len(parts_i)!=128:raise RuntimeError('128 calibration prompts required')
            samples[i]=torch.cat(parts_i)
            moments[i],stats[i]=covariance_owner.covariance(samples[i],ridge_ratio=.01)
        if return_samples:return moments,stats,samples
        return moments,stats

    def oracle_geometry(self, layer, values):
        prefixes=[];answers=[]
        module=self.modules[layer]
        for row in self.fits:
            self.check();v=values[(row['fact'],layer)].to(module.weight)
            with query.oracle(self.active,module,row,v):
                captured=self.capture_fit([row],keys=False,native_check=False)
            prefixes.append(captured['prefix_endpoint']);answers.append(captured['answer_endpoint'])
        return dict(prefix_endpoint=torch.cat(prefixes),answer_endpoint=torch.cat(answers),endpoint_layer=13)

    @contextmanager
    def edit(self, layer, requested):
        if type(layer)is not int or layer not in self.modules:
            raise ValueError('physical layer index required')
        delta=requested.to(self.modules[layer].weight)
        with wsp.edit(self.model,self.active['route'],[(f'mlp:{layer}',delta)]) as receipt:
            yield receipt

    def generate(self, row, *, max_new=64, variant='', history=()):
        self.check();self.counts['generated_calls']+=1
        answer,generation=manual.emit(self.active,row['question'],max_new=max_new,history=history)
        tail=len(generation['terminal_ids'])
        ids=generation['generated_ids'][:-tail] if tail else generation['generated_ids']
        return dict(row,variant=variant,answer=answer,generation=generation,
                    exact=None if row.get('expected') is None else metrics.exact_answer(answer,row['expected']),
                    diagnostics=metrics.repetition_metrics(ids,answer,row['question']),actual_history=list(history))

    def close(self):
        self.counter.remove()
        self.references.clear();self.packeds.clear();self.modules.clear();self.original.clear()
        self.active=self.model=None


def endpoint_transfer(baseline,oracle,observed):
    result={}
    for field in ('prefix_endpoint','answer_endpoint'):
        target=oracle[field]-baseline[field];actual=observed[field]-baseline[field]
        energy=float(target.square().sum())
        if energy<=1e-20:
            result[field]=dict(status='ZERO_ORACLE_DIRECTION',actual_norm=float(actual.norm()))
            continue
        projection=float((target*actual).sum())/energy
        result[field]=dict(goal_norm=math.sqrt(energy),actual_norm=float(actual.norm()),
            projection=projection,orthogonal_ratio=float((actual-projection*target).norm())/math.sqrt(energy),
            target_error_ratio=float((target-actual).norm())/math.sqrt(energy))
    return result
