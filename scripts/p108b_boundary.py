"""Opt-in persistent edits at an existing full-state trainer boundary.

Reuse AdaptiveMNTPTrainer state/restore, including optimizer/source/RNG/policy.
Validation is observational: its RNG, source and temporary state never leak
into the next training batch. Accepted FP32 matrices persist explicitly.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import torch
from tinylm.train.adaptive_training import cpu_copy
from scripts import interactive_research_infer as manual


class BoundaryEditError(RuntimeError):
    def __init__(self,message,receipt):super().__init__(message);self.receipt=receipt


def require_finite(value):
    if isinstance(value,torch.Tensor):
        if not bool(torch.isfinite(value).all()):raise ValueError('nonfinite validation measurement')
    elif isinstance(value,(float,int)):
        if not math.isfinite(value):raise ValueError('nonfinite validation measurement')
    elif isinstance(value,dict):
        for child in value.values():require_finite(child)
    elif isinstance(value,(list,tuple)):
        for child in value:require_finite(child)


def physical_mask(before,after):
    if before.dtype!=torch.float32 or before.shape!=after.shape or after.dtype!=before.dtype:
        raise ValueError('same native FP32 master layout required')
    return (before.contiguous().view(torch.uint8).reshape(-1,4)!=
            after.contiguous().view(torch.uint8).reshape(-1,4)).any(-1).reshape(before.shape)


def candidate_values(snapshot,parameters,edits):
    if not edits or set(edits)-set(parameters):raise ValueError('nonempty unique registered parameter names required')
    result={};masks={}
    for name,value in edits.items():
        before=snapshot['model'][name]
        if not isinstance(value,torch.Tensor)or before.dtype!=torch.float32 or value.dtype!=before.dtype or value.shape!=before.shape:
            raise ValueError('same-shape FP32 delta required')
        requested=value.detach().cpu()
        if not bool(torch.isfinite(requested).all()):raise ValueError('nonfinite edit rejected before writing')
        after=before.clone();support=requested.ne(0)
        after[support]=before[support]+requested[support]
        if not bool(torch.isfinite(after).all()):raise ValueError('nonfinite edited value rejected before writing')
        result[name]=after;masks[name]=physical_mask(before,after)
    return result,masks


def changed_moments(snapshot,optimizers,parameters,masks):
    packed=list(snapshot['optimizers']);by_id={id(v):k for k,v in parameters.items()};cleared=[]
    for i,optimizer in enumerate(optimizers):
        modified=None
        for live,stored in zip(optimizer.param_groups,snapshot['optimizers'][i]['param_groups']):
            for parameter,key in zip(live['params'],stored['params']):
                name=by_id[id(parameter)]
                if name not in masks or key not in snapshot['optimizers'][i]['state']:continue
                if modified is None:
                    modified=dict(snapshot['optimizers'][i]);modified['state']=dict(modified['state']);packed[i]=modified
                state=dict(modified['state'][key]);modified['state'][key]=state
                for field,value in state.items():
                    if not isinstance(value,torch.Tensor)or value.ndim==0:continue
                    if value.shape!=parameter.shape:raise ValueError('factored/non-coordinate optimizer state needs another adapter')
                    state[field]=value.clone();state[field][masks[name]]=0
                    cleared.append(dict(optimizer=i,parameter=name,state_field=field,entries=int(masks[name].sum())))
    return packed,cleared


class BoundaryController:
    """Caller invokes try_edit only after a complete gradient-free update.

    Product TinyLM training/cache admission remains separate from CPU protocol
    verification. A mandatory refresh callback owns the actual weight route.
    """
    SCHEMA='P108B_PERSISTENT_BOUNDARY_EDIT_V1'

    def __init__(self,trainer,*,refresh):
        if not callable(refresh):raise ValueError('explicit cache/weight-route refresh callback required')
        self.trainer,self.refresh,self.history=trainer,refresh,[]

    def update(self):return self.trainer.update()

    def state_dict(self):
        return dict(schema=self.SCHEMA,trainer=self.trainer.state_dict(),history=copy.deepcopy(self.history))

    def load_state_dict(self,state):
        if state.get('schema')!=self.SCHEMA or not isinstance(state.get('history'),list):raise ValueError('exact boundary schema/history required')
        self.trainer.load_state_dict(state['trainer']);self.refresh(self.trainer.model)
        self.trainer._restore_rng(state['trainer']['rng'])
        self.history=copy.deepcopy(state['history'])

    def try_edit(self,edits,*,validate,recipe,moment_policy):
        if moment_policy not in('keep','reset_changed')or not callable(validate):raise ValueError('explicit validation and moment policy required')
        if not isinstance(recipe,dict)or recipe.get('source_role')not in('TRAIN_CORRECTION','CORRECTION_DEV')or not recipe.get('id'):
            raise ValueError('named correction TRAIN/dev recipe required; FINAL/official test forbidden')
        trainer=self.trainer;snapshot=trainer.state_dict();parameters=dict(trainer.model.named_parameters())
        identifiers={name:id(value)for name,value in parameters.items()}
        gradient_flags={name:value.requires_grad for name,value in parameters.items()}
        after,masks=candidate_values(snapshot,parameters,edits)
        prepared=dict(snapshot,model=dict(snapshot['model']))
        prepared['model'].update(after);cleared=[]
        if moment_policy=='reset_changed':prepared['optimizers'],cleared=changed_moments(snapshot,trainer.optimizers,parameters,masks)
        receipt=dict(schema=self.SCHEMA,boundary_cursor=snapshot['cursor'],recipe=copy.deepcopy(recipe),
            recipe_sha256=hashlib.sha256(json.dumps(recipe,sort_keys=True).encode()).hexdigest().upper(),
            moment_policy=moment_policy,status='PROPOSED',original_core_sha256=manual.state_fingerprint(trainer.model),
            changed_entries=sum(int(mask.sum())for mask in masks.values()),changed_parameters=sorted(after),
            actual_net_norm=math.sqrt(sum(float((after[n].double()-snapshot['model'][n].double()).square().sum())for n in after)),
            validation_state_discarded=True,additional_training_updates=0,checkpoint_writes=0)
        failure=None;approved=False
        try:
            trainer.load_state_dict(prepared);trainer.model.eval();self.refresh(trainer.model)
            outcome=validate(trainer.model)
            if not isinstance(outcome,dict)or type(outcome.get('accept'))is not bool or not isinstance(outcome.get('measurements'),dict):
                raise ValueError('explicit acceptance and measurements required')
            if identifiers!={n:id(p)for n,p in trainer.model.named_parameters()}:raise ValueError('validation changed parameter identities')
            if gradient_flags!={n:p.requires_grad for n,p in trainer.model.named_parameters()}:raise ValueError('validation changed gradient flags')
            require_finite(outcome['measurements'])
            current=trainer.model.state_dict()
            for name,before in prepared['model'].items():
                if not torch.equal(current[name].detach().cpu(),before):raise ValueError('validation modified model state: '+name)
            if any(p.grad is not None for p in trainer.model.parameters()):raise ValueError('validation created persistent gradients')
            receipt['validation']=cpu_copy(outcome);approved=outcome['accept']
        except BaseException as error:failure=error
        finally:
            try:
                for name,parameter in trainer.model.named_parameters():
                    if name in identifiers and id(parameter)==identifiers[name]:parameter.requires_grad_(gradient_flags[name])
                trainer.load_state_dict(snapshot);self.refresh(trainer.model);trainer._restore_rng(snapshot['rng'])
                if identifiers!={n:id(p)for n,p in trainer.model.named_parameters()}:
                    trainer.dirty=True
                    raise ValueError('parameter-object graph was replaced; automatic continuation forbidden')
                receipt['full_boundary_restored_before_commit']=True
            except BaseException as rollback_error:
                receipt.update(status='ROLLBACK_ERROR',rollback_error=str(rollback_error),original_error=str(failure))
                raise BoundaryEditError('full training rollback failed; trainer must not continue',receipt)from rollback_error
        if failure is not None:
            receipt.update(status='REJECTED_VALIDATION_ERROR',error=str(failure));self.history.append(receipt)
            raise BoundaryEditError('validation error; original full boundary restored',receipt)from failure
        if approved:
            try:
                trainer.load_state_dict(prepared);self.refresh(trainer.model);trainer._restore_rng(snapshot['rng'])
                if identifiers!={n:id(p)for n,p in trainer.model.named_parameters()}:raise ValueError('commit changed parameter identity')
                receipt.update(status='ACCEPTED_PERSISTENT',cleared_optimizer_coordinates=cleared)
            except BaseException as error:
                trainer.load_state_dict(snapshot);self.refresh(trainer.model);trainer._restore_rng(snapshot['rng'])
                receipt.update(status='REJECTED_COMMIT_ERROR',error=str(error));self.history.append(receipt)
                raise BoundaryEditError('commit error; original full boundary restored',receipt)from error
        else:receipt['status']='REJECTED_METRICS'
        receipt['final_core_sha256']=manual.state_fingerprint(trainer.model)
        self.history.append(receipt);return receipt
