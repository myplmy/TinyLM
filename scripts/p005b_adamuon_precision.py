"""Model-free 2D local arithmetic factors; not the distributed author optimizer.

Independent arithmetic study of Chongjie-Si/AdaMuon revision
9c1ba5be86ebd7dd7464a0bc43b28daccf40279e (Apache-2.0).
No upstream source is imported. Existing TinyLM FP32-V optimizer is unchanged.
"""
from __future__ import annotations
import math
import torch
from tinylm.train.muon import _newton_schulz

NS_ORDERS=('LOCAL_GRAM_SQUARE_THEN_COEFFICIENT','AUTHOR_COEFFICIENT_THEN_GRAM_PRODUCT')
TAILS=('FP32_V_AND_NORMALIZATION','BF16_V_AND_NORMALIZATION')

def _finite(value):
    return bool(torch.isfinite(value).all())

@torch.no_grad()
def local_step(weight,gradient,momentum,variance,*,ns_order,tail,beta=.95,lr=.01,
               nesterov=True,weight_decay=.1,ns_steps=5,eps=1e-8):
    if ns_order not in NS_ORDERS or tail not in TAILS:
        raise ValueError('explicit NS order/tail factors required')
    for value in(weight,gradient,momentum):
        if (not isinstance(value,torch.Tensor) or value.device.type!='cpu' or value.ndim!=2
                or not value.numel() or value.shape!=weight.shape or value.dtype!=torch.float32
                or value.layout!=torch.strided or not _finite(value)):
            raise ValueError('same finite nonempty dense CPU FP32 matrices required')
    dtype=torch.float32 if tail==TAILS[0] else torch.bfloat16
    if (not isinstance(variance,torch.Tensor) or variance.device!=weight.device
            or variance.shape!=weight.shape or variance.dtype!=dtype
            or variance.layout!=torch.strided or not _finite(variance) or bool((variance<0).any())):
        raise ValueError('explicit complete nonnegative V dtype/shape required')
    if (type(nesterov)is not bool or type(ns_steps)is not int or ns_steps<1
            or not all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
                       for x in(beta,lr,weight_decay,eps))
            or not 0<=beta<1 or lr<0 or weight_decay<0 or eps<=0):
        raise ValueError('finite explicit scalar controls required')
    # Own copies make one diagnostic step observational for caller buffers.
    moment=momentum.clone().mul_(beta).add_(gradient)
    direction=gradient.add(moment,alpha=beta) if nesterov else moment
    signed=direction.sign()
    if ns_order==NS_ORDERS[0]:
        orthogonal=_newton_schulz(signed,steps=ns_steps).to(dtype)
    else:
        x=signed.bfloat16()
        transposed=x.shape[0]>x.shape[1]
        if transposed:x=x.T
        x=x/(x.norm(dim=(-2,-1),keepdim=True)+1e-7)
        for _ in range(ns_steps):
            gram=x@x.T
            # Python @ and * associate left: scaling precedes second product.
            cubic=(2.0315*gram)@gram
            x=3.4445*x+(-4.7750*gram+cubic)@x
        if transposed:x=x.T
        orthogonal=x.to(dtype)
    variance_next=variance.clone().mul_(beta).addcmul_(orthogonal,orthogonal,value=1-beta)
    denominator=variance_next.sqrt().add_(eps)
    update=orthogonal.div(denominator)
    update.mul_(.2*math.sqrt(weight.numel())/(update.norm()+eps))
    result=weight.clone()
    if weight_decay:result.mul_(1-lr*weight_decay)
    result.add_(update,alpha=-lr)
    if not all(_finite(value)for value in(result,moment,variance_next,update)):
        raise ArithmeticError('local AdaMuon factor produced nonfinite output')
    return dict(weight=result,momentum=moment,variance=variance_next,update=update,
                state_bytes=sum(v.numel()*v.element_size()for v in(moment,variance_next)))
