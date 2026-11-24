"""Explicit complete-group loss scaling, without model/data/scheduler ownership.

The whole-group overflow gate extends PyTorch's independent optimizer skips.
CPU tests pin installed2.10 behavior; Native/CUDA integration is separate.
An arbitrary optimizer exception is not rolled back. Discard the failed group
and restore caller-owned model/optimizer state before constructing a fresh one.
"""
from __future__ import annotations

import copy
from dataclasses import asdict,dataclass
import hashlib
import json
import math
import re

import torch

SCHEMA='P107_SCALED_OPTIMIZER_GROUP_V1'
SCOPE='SCALER_AND_GROUP_COUNTERS_ONLY_NOT_MODEL_OPTIMIZER_SOURCE_POLICY_SCHEDULE_OR_RNG'


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def checksum(value):return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest().upper()
def positive(value,label,minimum=2.**-149,maximum=3.4028234663852886e38):
    if type(value)not in(int,float)or not math.isfinite(value)or not minimum<=value<=maximum:
        raise ValueError('scaled group invalid finite positive value: '+label)


@dataclass(frozen=True)
class ScaleConfig:
    init_scale:float=65536.
    growth_factor:float=2.
    backoff_factor:float=.5
    growth_interval:int=2000

    def __post_init__(self):
        positive(self.init_scale,'init_scale')
        positive(self.growth_factor,'growth_factor')
        positive(self.backoff_factor,'backoff_factor')
        if not self.growth_factor>1 or not self.backoff_factor<1:
            raise ValueError('scaled group growth>1 and backoff<1 required')
        if type(self.growth_interval)is not int or not 1<=self.growth_interval<2**31:
            raise ValueError('scaled group positive int32 growth interval required')
        object.__setattr__(self,'init_scale',float(torch.tensor(self.init_scale,dtype=torch.float32,device='cpu')))
        object.__setattr__(self,'growth_factor',float(self.growth_factor))
        object.__setattr__(self,'backoff_factor',float(self.backoff_factor))


class ScaledOptimizerGroup:
    """Caller-normalized scalar losses, one complete group and one scale update.

    Supported masters are exclusive dense FP32 leaves on one CPU/CUDA device.
    Fused/capturable/differentiable optimizer contracts are excluded. This class
    never loads or saves model/optimizer/source states or chooses skip semantics
    for a data stream, adaptive policy or LR schedule.
    """
    def __init__(self,parameters,optimizers,*,run_signature,expected_backwards,config=ScaleConfig()):
        if (not isinstance(run_signature,str)or re.fullmatch('[0-9A-F]{64}',run_signature)is None
                or type(expected_backwards)is not int or expected_backwards<1
                or not isinstance(config,ScaleConfig)):
            raise ValueError('scaled group explicit signature/backward count/config required')
        self.parameters=tuple(parameters);self.optimizers=tuple(optimizers)
        if (not self.parameters or not self.optimizers
                or len({id(p)for p in self.parameters})!=len(self.parameters)
                or any(not isinstance(p,torch.Tensor)or p.dtype!=torch.float32 or not p.is_leaf
                    or not p.requires_grad or p.numel()<1 or p.layout!=torch.strided or p.grad is not None
                    or not bool(torch.isfinite(p).all())for p in self.parameters)):
            raise ValueError('scaled group unique finite dense FP32 leaves with empty gradients required')
        devices={p.device for p in self.parameters}
        if len(devices)!=1 or next(iter(devices)).type not in('cpu','cuda'):
            raise ValueError('scaled group one explicit CPU/CUDA parameter device required')
        self.device=next(iter(devices))
        self.config=config;self.run_signature=run_signature;self.expected_backwards=expected_backwards
        self._layout=self._layout_now()
        self._scaler=self._new_scaler()
        self.phase='READY';self._backwards=0;self._current_scale=None;self._versions=None
        self.attempts=self.steps=self.skips=0

    def _layout_now(self):
        indices={id(p):i for i,p in enumerate(self.parameters)}
        assigned=[];groups=[]
        for optimizer in self.optimizers:
            if (not isinstance(optimizer,torch.optim.Optimizer)
                    or getattr(optimizer,'_step_supports_amp_scaling',False)
                    or any(optimizer.defaults.get(name,False)for name in('fused','capturable','differentiable'))):
                raise ValueError('scaled group unsupported optimizer/AMP contract')
            member=[]
            for group in optimizer.param_groups:
                if any(group.get(name,False)for name in('fused','capturable','differentiable')):
                    raise ValueError('scaled group unsupported optimizer group settings')
                if not group['params']:raise ValueError('scaled group empty optimizer group')
                ids=[id(p)for p in group['params']]
                if any(value not in indices for value in ids):
                    raise ValueError('scaled group optimizer owns an undeclared parameter')
                assigned.extend(ids);member.append([indices[value]for value in ids])
            groups.append(dict(optimizer_type=type(optimizer).__module__+'.'+type(optimizer).__qualname__,groups=member))
        if len(set(assigned))!=len(assigned)or set(assigned)!=set(indices):
            raise ValueError('scaled group every trainable parameter needs exactly one optimizer')
        return dict(parameters=[dict(shape=list(p.shape),dtype=str(p.dtype))for p in self.parameters],optimizers=groups)

    def _new_scaler(self):
        c=self.config
        return torch.amp.GradScaler(self.device.type,init_scale=float(c.init_scale),growth_factor=float(c.growth_factor),
            backoff_factor=float(c.backoff_factor),growth_interval=c.growth_interval,enabled=True)

    def _binding(self):
        if self._layout_now()!=self._layout:
            raise ValueError('scaled group optimizer/parameter ownership changed')
        if any(p.device!=self.device or p.dtype!=torch.float32 or not p.is_leaf
               or not p.requires_grad or p.layout!=torch.strided for p in self.parameters):
            raise ValueError('scaled group parameter geometry/device changed')

    def backward(self,loss,*,retain_graph=False):
        if self.phase not in('READY','ACCUMULATING'):
            raise RuntimeError('scaled group failed or already finishing; complete external restore required')
        try:
            self._binding()
            if (not isinstance(loss,torch.Tensor)or loss.ndim!=0 or loss.device!=self.device
                    or not loss.requires_grad or not bool(torch.isfinite(loss))
                    or type(retain_graph)is not bool or self._backwards>=self.expected_backwards):
                raise ValueError('scaled group finite caller-normalized scalar and complete backward count required')
            if self.phase=='READY':
                if any(p.grad is not None for p in self.parameters):
                    raise ValueError('scaled group start requires empty gradients')
                self._current_scale=float(self._scaler.get_scale())
                self._versions=tuple(p._version for p in self.parameters)
                self.phase='ACCUMULATING'
            if (float(self._scaler.get_scale())!=self._current_scale
                    or tuple(p._version for p in self.parameters)!=self._versions):
                raise ValueError('scaled group scale/parameters changed during accumulation')
            self._scaler.scale(loss).backward(retain_graph=retain_graph)
            self._backwards+=1
        except BaseException:
            self.phase='FAILED';raise

    def finish(self,*,clip_norm=1.):
        if self.phase!='ACCUMULATING'or self._backwards!=self.expected_backwards:
            raise RuntimeError('scaled group requires every expected backward before finish')
        try:
            self._binding();positive(clip_norm,'clip_norm')
            if (float(self._scaler.get_scale())!=self._current_scale
                    or tuple(p._version for p in self.parameters)!=self._versions
                    or any(p.grad is None or p.grad.layout!=torch.strided for p in self.parameters)):
                raise ValueError('scaled group fixed accumulation and complete dense gradients required')
            self.phase='UNSCALING'
            for optimizer in self.optimizers:self._scaler.unscale_(optimizer)
            finite=all(bool(torch.isfinite(p.grad).all())for p in self.parameters)
            norm=None;calls=0
            if finite:
                norm=float(torch.nn.utils.clip_grad_norm_(self.parameters,float(clip_norm),error_if_nonfinite=True))
                self.phase='STEPPING'
                for optimizer in self.optimizers:
                    self._scaler.step(optimizer);calls+=1
            # Explicit whole-group extension: on overflow, unscale_ has recorded
            # inf checks for every optimizer, but no optimizer is allowed to step.
            self._scaler.update()
            after=float(self._scaler.get_scale());positive(after,'updated scale')
            if any(not bool(torch.isfinite(p).all())for p in self.parameters):
                raise ValueError('scaled group optimizer produced nonfinite master parameters')
            self.attempts+=1;self.steps+=int(finite);self.skips+=int(not finite)
            for optimizer in self.optimizers:optimizer.zero_grad(set_to_none=True)
            report=dict(status='STEPPED_ALL'if finite else'SKIPPED_ALL_NONFINITE',attempts=self.attempts,
                completed_optimizer_groups=self.steps,skipped_groups=self.skips,optimizer_step_calls=calls,
                backward_calls=self._backwards,scale_before=self._current_scale,scale_after=after,
                pre_clip_gradient_norm=norm,clip_norm=float(clip_norm),
                source_policy_schedule_owned_by_caller=True,full_training_resume=False)
            self.phase='READY';self._backwards=0;self._current_scale=self._versions=None
            return report
        except BaseException:
            self.phase='FAILED';raise

    def state_dict(self):
        if self.phase!='READY'or self._backwards or any(p.grad is not None for p in self.parameters):
            raise RuntimeError('scaled group only a healthy gradient-free complete boundary can be saved')
        self._binding()
        value=dict(schema=SCHEMA,run_signature=self.run_signature,device=str(self.device),config=asdict(self.config),
            expected_backwards=self.expected_backwards,layout=copy.deepcopy(self._layout),
            scaler=copy.deepcopy(self._scaler.state_dict()),attempts=self.attempts,steps=self.steps,skips=self.skips,
            source_scope=SCOPE)
        value['state_sha256']=checksum(value)
        return value

    @property
    def contract(self):
        self._binding()
        return dict(schema=SCHEMA,run_signature=self.run_signature,device=str(self.device),
            config=asdict(self.config),expected_backwards=self.expected_backwards,
            layout=copy.deepcopy(self._layout),source_scope=SCOPE)

    def validate_checkpoint(self,state):
        """Pure scalar/layout validation, also usable after a failed step.

        This copies no parameter, optimizer or live scaler state. Caller still
        owns complete model/optimizer restoration before fresh reconstruction.
        """
        self._binding()
        state=copy.deepcopy(state)
        expected={'schema','run_signature','device','config','expected_backwards','layout','scaler','attempts','steps','skips','source_scope','state_sha256'}
        if not isinstance(state,dict)or set(state)!=expected:
            raise ValueError('scaled group exact checkpoint schema required')
        saved_sha=state.pop('state_sha256')
        if (saved_sha!=checksum(state)or state['schema']!=SCHEMA or state['run_signature']!=self.run_signature
                or state['device']!=str(self.device)or canonical(state['config'])!=canonical(asdict(self.config))
                or type(state['expected_backwards'])is not int or state['expected_backwards']!=self.expected_backwards
                or canonical(state['layout'])!=canonical(self._layout)or state['source_scope']!=SCOPE
                or any(type(state[name])is not int or state[name]<0 for name in('attempts','steps','skips'))
                or state['attempts']!=state['steps']+state['skips']):
            raise ValueError('scaled group checkpoint identity/counters differ')
        value=state['scaler'];keys={'scale','growth_factor','backoff_factor','growth_interval','_growth_tracker'}
        if not isinstance(value,dict)or set(value)!=keys:
            raise ValueError('scaled group exact public scaler fields required')
        positive(value['scale'],'saved scale')
        for name in('growth_factor','backoff_factor','growth_interval'):
            if type(value[name])is not type(getattr(self.config,name))or value[name]!=getattr(self.config,name):
                raise ValueError('scaled group saved growth policy differs')
        if type(value['_growth_tracker'])is not int or not 0<=value['_growth_tracker']<self.config.growth_interval:
            raise ValueError('scaled group public growth tracker is invalid')
        if value['_growth_tracker']>state['steps']:
            raise ValueError('scaled group growth tracker exceeds completed optimizer groups')
        state['state_sha256']=saved_sha
        return state

    def load_state_dict(self,state):
        if self.phase!='READY'or self.attempts or self._backwards or any(p.grad is not None for p in self.parameters):
            raise RuntimeError('scaled group restore requires a fresh clean controller')
        state=self.validate_checkpoint(state)
        value=state['scaler']
        probe=self._new_scaler();probe.load_state_dict(value)
        if canonical(probe.state_dict())!=canonical(value):
            raise ValueError('scaled group public scaler restore differs')
        self._scaler=probe
        self.attempts,self.steps,self.skips=state['attempts'],state['steps'],state['skips']
