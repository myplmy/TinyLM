"""MEMIT-style residual allocation with TinyLM's signed residual gates and one norm budget."""
import math
import torch
from scripts import p108_joint_write as joint


def shared_budget(weights,*,relative_cap=.05):
    if (not isinstance(weights,list)or len(weights)!=2 or type(relative_cap)not in(int,float)
            or not math.isfinite(relative_cap)or not 0<relative_cap<=.05
            or any(not isinstance(w,torch.Tensor)or w.ndim!=2 or w.dtype!=torch.float32
                   or not bool(torch.isfinite(w).all())for w in weights)):
        raise ValueError('two finite original FP32 weights and primary cap at most5percent required')
    norms=[float(w.detach().cpu().double().norm())for w in weights]
    if min(norms)<=0:raise ValueError('nonzero original matrices required')
    absolute=relative_cap*min(norms)
    return dict(absolute_total_cap=absolute,single_layer_cap=absolute,
        distributed_each_cap=absolute/math.sqrt(2),original_weight_norms=norms,relative_cap=relative_cap)


def residual_target(desired,current,*,remaining,gate):
    if (not isinstance(desired,torch.Tensor)or not isinstance(current,torch.Tensor)
            or desired.ndim!=2 or desired.shape!=current.shape
            or any(not bool(torch.isfinite(t).all())for t in (desired,current))
            or type(remaining)is not int or remaining<1 or type(gate)not in(int,float)
            or not math.isfinite(gate)or gate==0):
        raise ValueError('same finite final-block targets and signed nonzero gate/remaining layers required')
    target=(desired.detach().cpu().double()-current.detach().cpu().double())/(remaining*gate)
    if not bool(torch.isfinite(target).all()):raise ValueError('gate-adjusted residual overflow')
    return target


def packet(keys,desired,current,moment,weight,*,remaining,gate,absolute_cap):
    if type(absolute_cap)not in(int,float)or not math.isfinite(absolute_cap)or absolute_cap<=0:
        raise ValueError('explicit finite absolute physical change budget required')
    target=residual_target(desired,current,remaining=remaining,gate=gate)
    norm=float(weight.detach().cpu().double().norm())
    if norm<=0:raise ValueError('nonzero original weight required')
    result=joint.joint_packet(keys,target,moment,weight,relative_cap=absolute_cap/norm)
    result['remaining_layers']=remaining;result['signed_gate']=gate
    result['absolute_cap']=absolute_cap
    result['final_block_residual_before']=float((desired.double()-current.double()).norm())
    return result


def realized_total(weights,deltas,*,absolute_cap):
    if (len(weights)!=len(deltas)or not weights or type(absolute_cap)not in(int,float)
            or not math.isfinite(absolute_cap)or absolute_cap<=0):raise ValueError('same original matrices/deltas and total budget required')
    norms=[];relative=[]
    for w,d in zip(weights,deltas):
        if (not isinstance(w,torch.Tensor)or not isinstance(d,torch.Tensor)or w.ndim!=2 or w.shape!=d.shape
                or w.dtype!=torch.float32 or d.dtype!=torch.float32
                or not bool(torch.isfinite(w).all())or not bool(torch.isfinite(d).all())):
            raise ValueError('finite matching original FP32 matrices required')
        w=w.detach().cpu();d=d.detach().cpu();actual=(w+d).double()-w.double()
        norms.append(float(actual.norm()));relative.append(norms[-1]/max(float(w.double().norm()),1e-300))
    combined=math.sqrt(sum(x*x for x in norms))
    if combined>absolute_cap:raise ValueError('realized combined physical Frobenius budget exceeded')
    return dict(combined_realized_norm=combined,absolute_total_cap=absolute_cap,per_layer_realized_norms=norms,
                per_layer_relative_norms=relative,within_total_budget=True)
