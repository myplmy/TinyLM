"""Opt-in author-aligned AdaMuon BF16 arithmetic and bounded transport.

Source: Chongjie-Si/AdaMuon@9c1ba5be86ebd7dd7464a0bc43b28daccf40279e,
adamuon.py blob dd194bdb7fccf6bab5b5cfed3b3cba0df059c2af (Apache-2.0).
https://github.com/Chongjie-Si/AdaMuon/blob/9c1ba5be86ebd7dd7464a0bc43b28daccf40279e/adamuon.py

FP32 master/momentum; author NS association and BF16 flat V/normalization.
Explicit adaptations: stable size groups, collective validation before writes,
CPU/device-derived buffers, world1 BF16 copy, scratch-free resume schema.
This is not an exact port of every upstream shape, backend or failure behavior.
"""
from __future__ import annotations
import copy,hashlib,json,math
from numbers import Real
import torch
import torch.distributed as dist

SCHEMA='TINYLM_ADAMUON_AUTHOR_BF16_TRANSPORT_V1'

def _number(value,name,*,positive=False,upper=None):
    if (isinstance(value,bool) or not isinstance(value,Real) or not math.isfinite(value)
            or value<0 or (positive and value==0) or (upper is not None and value>=upper)):
        raise ValueError('AdaMuon author invalid '+name)

def _settings(group):
    for key in ('lr','weight_decay'):_number(group[key],key)
    _number(group['momentum'],'momentum',upper=1)
    _number(group['eps'],'eps',positive=True)
    if float(torch.tensor(group['eps'],dtype=torch.bfloat16))<=0:
        raise ValueError('AdaMuon author eps must remain positive BF16')
    if type(group['nesterov'])is not bool or type(group['ns_steps'])is not int or group['ns_steps']<1:
        raise ValueError('AdaMuon author explicit Nesterov/positive NS steps required')

def _parameter(p):
    if (not isinstance(p,torch.Tensor) or p.dtype!=torch.float32 or p.ndim not in (2,4)
            or not p.numel() or p.layout!=torch.strided):
        raise ValueError('AdaMuon author requires nonempty dense FP32 master 2D/4D tensors')

def _state(p,state,*,device=True):
    if not state:return
    if set(state)!={'momentum_buffer','v_buffer'}:
        raise ValueError('AdaMuon author exact momentum and flat V state required')
    for key,shape,dtype in (('momentum_buffer',p.shape,torch.float32),
                            ('v_buffer',(p.numel(),),torch.bfloat16)):
        tensor=state[key]
        if (not isinstance(tensor,torch.Tensor) or tensor.shape!=shape or tensor.dtype!=dtype
                or tensor.layout!=torch.strided or (device and tensor.device!=p.device)
                or not bool(torch.isfinite(tensor).all())):
            raise ValueError('AdaMuon author state shape/dtype/device/finite differs: '+key)
    if bool((state['v_buffer']<0).any()):raise ValueError('AdaMuon author V cannot be negative')

def _orthogonal(direction,steps):
    x=direction.bfloat16()
    transpose=x.size(-2)>x.size(-1)
    if transpose:x=x.mT
    x=x/(x.norm(dim=(-2,-1),keepdim=True)+1e-7)
    for _ in range(steps):
        gram=x@x.mT
        # Match the author's left association: (coefficient * gram) @ gram.
        polynomial=-4.7750*gram+(2.0315*gram)@gram
        x=3.4445*x+polynomial@x
    return x.mT if transpose else x

class AdaMuonAuthor(torch.optim.Optimizer):
    """Source-aligned BF16 optimizer; None gradients are errors on all ranks.

    More than one rank requires an existing process group. All ranks must call
    construction/step/load in the same order and begin with the same weights.
    Workspaces are scratch; optimizer state is local to its owning rank.
    Arithmetic errors can leave earlier parameters/moments updated. Stop all
    ranks and restore a valid checkpoint; no transactional rollback is claimed.
    """
    def __init__(self,params,lr=.02,weight_decay=.01,momentum=.95,nesterov=True,
                 ns_steps=5,eps=1e-8,*,rank=0,world_size=1,process_group=None):
        if (type(rank)is not int or type(world_size)is not int
                or world_size<1 or not 0<=rank<world_size):
            raise ValueError('AdaMuon author explicit valid rank/world_size required')
        if isinstance(params,set):raise ValueError('AdaMuon author stable parameter order required')
        params=list(params)
        if not params or len({id(p)for p in params})!=len(params):
            raise ValueError('AdaMuon author nonempty unique parameters required')
        for p in params:_parameter(p)
        if len({p.device for p in params})!=1:raise ValueError('one device per rank required')
        self.rank,self.world_size,self.process_group=rank,world_size,process_group
        if world_size>1 and (not dist.is_initialized() or dist.get_rank(process_group)!=rank
                or dist.get_world_size(process_group)!=world_size):
            raise ValueError('matching existing process group required')
        defaults=dict(lr=lr,weight_decay=weight_decay,momentum=momentum,
            nesterov=nesterov,ns_steps=ns_steps,eps=eps)
        _settings(defaults)
        buckets={}
        for p in params:buckets.setdefault(p.numel(),[]).append(p)
        self._building=True
        super().__init__([dict(params=values)for values in buckets.values()],defaults)
        self._building=False
        topology=[[(list(p.shape),str(p.dtype))for p in group['params']]for group in self.param_groups]
        self.topology_sha256=hashlib.sha256(json.dumps(topology,separators=(',',':')).encode()).hexdigest()
        self._collective_check(None,topology=True)
        self._workspaces=[torch.empty((world_size,group['params'][0].numel()),
            dtype=torch.bfloat16,device=group['params'][0].device)for group in self.param_groups]

    def add_param_group(self,group):
        if not getattr(self,'_building',False):
            raise ValueError('AdaMuon author parameter topology is fixed')
        super().add_param_group(group)

    def _collective_check(self,error,*,topology=False):
        if self.world_size==1:
            if error:raise ValueError(error)
            return
        payload=(error,self.topology_sha256 if topology else None)
        results=[None]*self.world_size
        dist.all_gather_object(results,payload,group=self.process_group)
        errors=[value[0]for value in results if value[0]]
        if errors:raise ValueError('AdaMuon author collective preflight: '+'; '.join(errors))
        if topology and len({value[1]for value in results})!=1:
            raise ValueError('AdaMuon author rank parameter topology differs')

    def _validate(self,*,gradients):
        try:
            for group in self.param_groups:
                _settings(group)
                for p in group['params']:
                    _parameter(p);_state(p,self.state.get(p,{}))
                    if not bool(torch.isfinite(p).all()):raise ValueError('nonfinite master weight')
                    if not gradients:continue
                    g=p.grad
                    if g is None:raise ValueError('None gradient is forbidden by the author contract')
                    if (g.shape!=p.shape or g.dtype!=p.dtype or g.device!=p.device
                            or g.layout!=torch.strided or not bool(torch.isfinite(g).all())):
                        raise ValueError('gradient shape/dtype/device/finite differs')
            error=None
        except (ValueError,KeyError) as exc:error=str(exc)
        self._collective_check(error)

    def _local_update(self,p,group):
        state=self.state[p]
        if not state:
            state['momentum_buffer']=torch.zeros_like(p)
            state['v_buffer']=torch.zeros(p.numel(),dtype=torch.bfloat16,device=p.device)
        moment=state['momentum_buffer']
        moment.mul_(group['momentum']).add_(p.grad)
        if not bool(torch.isfinite(moment).all()):raise ArithmeticError('nonfinite author momentum')
        direction=p.grad.add(moment,alpha=group['momentum']) if group['nesterov'] else moment
        if direction.ndim==4:direction=direction.view(len(direction),-1)
        update=_orthogonal(direction.sign(),group['ns_steps']).flatten()
        variance=state['v_buffer']
        variance.mul_(group['momentum']).addcmul_(update,update,value=1-group['momentum'])
        update=update.div(variance.sqrt().add(group['eps']))
        # Preserve the upstream 4D scale convention as well as its 2D equation.
        update.mul_(.2*(min(p.shape)*max(p.shape))**.5/(update.norm()+group['eps']))
        if not bool(torch.isfinite(update).all()):raise ArithmeticError('nonfinite author update')
        return update

    @torch.no_grad()
    def step(self,closure=None):
        loss=None
        if closure is not None:
            with torch.enable_grad():loss=closure()
        self._validate(gradients=True)
        for group,workspace in zip(self.param_groups,self._workspaces):
            params=group['params'];pending=None
            def finish():
                handle,previous=pending
                if handle is not None:handle.wait()
                for slot,p in enumerate(previous):
                    p.mul_(1-group['lr']*group['weight_decay'])
                    p.add_(workspace[slot].view_as(p),alpha=-group['lr'])
            for base in range(0,len(params),self.world_size):
                index=base+self.rank
                try:
                    update=(self._local_update(params[index],group)if index<len(params)
                        else torch.zeros(workspace.shape[1],dtype=workspace.dtype,device=workspace.device))
                    error=None
                except (ArithmeticError,RuntimeError,ValueError) as exc:
                    update=None;error=str(exc)
                if pending is not None:finish()
                self._collective_check(error)
                if self.world_size==1:
                    workspace[0].copy_(update);handle=None
                else:
                    handle=dist.all_gather_into_tensor(workspace.view(-1),update.contiguous(),
                        group=self.process_group,async_op=True)
                pending=(handle,params[base:base+self.world_size])
            if pending is not None:finish()
        self._validate(gradients=False)
        return loss

    @property
    def scratch_bytes(self):
        return sum(p.untyped_storage().nbytes()for p in self._workspaces)

    def state_dict(self):
        result=super().state_dict()
        result['author_contract']=dict(schema=SCHEMA,rank=self.rank,world_size=self.world_size,
            topology_sha256=self.topology_sha256,scratch_serialized=False)
        return result

    def load_state_dict(self,state_dict):
        expected=dict(schema=SCHEMA,rank=self.rank,world_size=self.world_size,
            topology_sha256=self.topology_sha256,scratch_serialized=False)
        if state_dict.get('author_contract')!=expected:
            raise ValueError('AdaMuon author resume method/rank/world/topology differs')
        groups=state_dict['param_groups']
        if len(groups)!=len(self.param_groups) or any(len(a['params'])!=len(b['params'])
                for a,b in zip(groups,self.param_groups)):
            raise ValueError('AdaMuon author resume group topology differs')
        ids=[key for group in groups for key in group['params']]
        if len(ids)!=len(set(ids)) or any(type(key)is not int or key<0 for key in ids):
            raise ValueError('AdaMuon author unique saved parameter IDs required')
        owned={key for group in groups for index,key in enumerate(group['params'])
            if index%self.world_size==self.rank}
        if not set(state_dict['state'])<=owned:raise ValueError('AdaMuon author orphan/nonowner state')
        for saved,current in zip(groups,self.param_groups):
            _settings(saved)
            for key,p in zip(saved['params'],current['params']):
                _state(p,state_dict['state'].get(key,{}),device=False)
        payload={key:value for key,value in state_dict.items()if key!='author_contract'}
        super().load_state_dict(copy.deepcopy(payload))
        # Optimizer.load_state_dict casts floating state to the FP32 parameter.
        # Restore the independently validated author BF16 flat V explicitly.
        for saved,current in zip(groups,self.param_groups):
            for key,p in zip(saved['params'],current['params']):
                if key in state_dict['state']:
                    self.state[p]['v_buffer']=state_dict['state'][key]['v_buffer'].detach().to(
                        device=p.device,dtype=torch.bfloat16).clone()
        self._validate(gradients=False)

