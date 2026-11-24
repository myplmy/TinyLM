"""Pure target-window intervention, value caps and question-weighted columns."""
from contextlib import contextmanager
import math
import torch

MODES=('SHARED','PER_TARGET')


@contextmanager
def inject_window(module,start,delta,*,capture=None):
    if type(start)is not int or start<0 or delta.ndim!=2 or not len(delta)or not bool(torch.isfinite(delta).all()):
        raise ValueError('finite nonempty target-position matrix and explicit start required')
    applied=False
    def hook(_module,args,output):
        nonlocal applied
        if applied or output.ndim!=3 or output.shape[0]!=1 or output.shape[-1]!=delta.shape[1]or start+len(delta)>output.shape[1]:
            raise ValueError('one complete teacher-forced target window required; no cached decode hook')
        applied=True
        if capture is not None:
            capture['keys']=args[0][0,start:start+len(delta)].detach().cpu().clone()
            capture['values']=output[0,start:start+len(delta)].detach().cpu().clone()
        addition=torch.zeros_like(output);addition[:,start:start+len(delta)]=delta.to(output)[None]
        return output+addition
    handle=module.register_forward_hook(hook)
    try:yield
    finally:handle.remove()


def value_field(parameters,mode,norms):
    if mode not in MODES or parameters.ndim!=2 or norms.ndim!=1 or not len(norms)or not bool(torch.isfinite(norms).all())or bool((norms<=0).any()):
        raise ValueError('declared mode and positive native per-position scales required')
    if parameters.shape[0]!=(1 if mode=='SHARED'else len(norms)):
        raise ValueError('shared versus per-target parameter ownership differs')
    if mode=='SHARED':return(parameters*norms.mean()).expand(len(norms),-1)
    return parameters*norms[:,None]


def limit_parameters(parameters,mode,norms,cap):
    if not isinstance(cap,(float,int))or not math.isfinite(cap)or not 0<cap<=1:
        raise ValueError('declared finite relative value cap required')
    with torch.no_grad():
        current=value_field(parameters,mode,norms).norm(dim=1)
        factors=(norms*cap/current.clamp_min(1e-30)).clamp_max(1)
        if mode=='SHARED':parameters.mul_(factors.min())
        else:parameters.mul_(factors[:,None])


def question_columns(keys,values):
    if(keys.ndim!=2 or values.ndim!=2 or len(keys)!=len(values)or not len(keys)or
        keys.requires_grad or values.requires_grad or keys.device.type!='cpu'or values.device.type!='cpu'or
        not bool(torch.isfinite(keys).all())or not bool(torch.isfinite(values).all())):
        raise ValueError('same nonempty detached native target positions required')
    weight=math.sqrt(1/len(keys))
    return keys.double().T*weight,values.double().T*weight
