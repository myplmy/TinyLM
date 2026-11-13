"""Opt-in finite-logit ALM tail, with the same real Bernoulli objective.

The product ALM boundary guard is untouched. No probability clipping is used.
FP64 is restricted to head reductions and small log-probability vectors.
"""
import math
import torch
import torch.nn.functional as F
from tinylm.train import alm


def log_softplus(value):
    if not value.is_floating_point() or not bool(torch.isfinite(value).all()):
        raise ValueError('finite floating point value required')
    x=value.double();small=x.lt(-40);result=torch.empty_like(x)
    result[small]=x[small]
    result[~small]=torch.log(torch.logaddexp(torch.zeros_like(x[~small]),x[~small]))
    return result


def log_nll_from_logits(logits,targets):
    if (logits.ndim!=2 or logits.shape[1]<2 or targets.shape!=(logits.shape[0],)
            or targets.dtype!=torch.long or targets.device!=logits.device
            or not logits.is_floating_point() or not bool(torch.isfinite(logits).all())):
        raise ValueError('finite logits with at least2 classes and matching targets required')
    if not bool((targets.ge(0)&targets.lt(logits.shape[1])).all()):raise ValueError('target outside vocabulary')
    z=logits.double();target=z.gather(1,targets[:,None])[:,0]
    other=z.scatter(1,targets[:,None],-torch.inf)
    return log_softplus(torch.logsumexp(other,dim=-1)-target)


def student_log_pair(log_a):
    if not log_a.is_floating_point() or not bool(torch.isfinite(log_a).all()):
        raise ValueError('finite log NLL sum/temperature required')
    x=log_a.double()
    if bool(x.gt(math.log(torch.finfo(torch.float64).max)-1).any()):
        raise FloatingPointError('NLL outside finite FP64 probability representation')
    small=x.lt(-40);log_tail=torch.empty_like(x)
    log_tail[small]=x[small]
    log_tail[~small]=alm.log1mexp(-torch.exp(x[~small]))
    return -torch.exp(x),log_tail


def binary_kl_logpair(log_q_student,log_tail_student,log_q_teacher):
    if (log_q_student.shape!=log_tail_student.shape or log_q_teacher.shape!=log_q_student.shape
            or len({x.device for x in (log_q_student,log_tail_student,log_q_teacher)})!=1):
        raise ValueError('aligned probability pairs required')
    s,b,t=log_q_student.double(),log_tail_student.double(),log_q_teacher.detach().double()
    if any(not bool(torch.isfinite(x).all()) or bool(x.gt(0).any()) for x in (s,b,t)):
        raise ValueError('finite nonpositive probability logs required')
    if bool(torch.logaddexp(s,b).detach().abs().gt(2e-12).any()):
        raise ValueError('student probability pair does not normalize')
    active=t.ne(0);negative=torch.zeros_like(s)
    negative[active]=(-torch.expm1(t[active]))*(alm.log1mexp(t[active])-b[active])
    result=torch.exp(t)*(t-s)+negative
    if not bool(torch.isfinite(result).all()):raise FloatingPointError('nonfinite exact-form ALM tail')
    return result


def target_dual(model,hidden,targets,*,chunk=64,checkpoint_head=True):
    if (hidden.ndim!=3 or tuple(hidden.shape[:2])!=tuple(targets.shape) or targets.dtype!=torch.long
            or targets.device!=hidden.device or type(chunk) is not int or chunk<1):
        raise ValueError('aligned already shifted hidden/target and positive chunk required')
    valid=targets.ne(alm.IGNORE);positions=valid.reshape(-1).nonzero(as_tuple=True)[0]
    flat=hidden[...,0].reshape(-1).float()*0.;flat_log=flat.double()
    if not positions.numel():return flat.reshape_as(targets),flat_log.reshape_as(targets),valid
    features=hidden.reshape(-1,hidden.shape[-1]).index_select(0,positions)
    labels=targets.reshape(-1).index_select(0,positions)
    def head(h,y):
        logits=model._head_logits(h.unsqueeze(0))[0].float()
        return F.cross_entropy(logits,y,reduction='none'),log_nll_from_logits(logits,y)
    ordinary=[];logs=[]
    for start in range(0,positions.numel(),chunk):
        h,y=features[start:start+chunk],labels[start:start+chunk]
        if checkpoint_head and torch.is_grad_enabled() and h.requires_grad:
            from torch.utils.checkpoint import checkpoint
            ce,logn=checkpoint(head,h,y,use_reentrant=False,preserve_rng_state=False)
        else:ce,logn=head(h,y)
        ordinary.append(ce);logs.append(logn)
    return (flat.scatter(0,positions,torch.cat(ordinary)).reshape_as(targets),
            flat_log.scatter(0,positions,torch.cat(logs)).reshape_as(targets),valid)


def chunk_kl(nll,log_nll,supervised,chunks,*,temperature=100.):
    if log_nll.shape!=nll.shape or log_nll.device!=nll.device:
        raise ValueError('aligned ordinary/log NLL required')
    # Reuse the original complete teacher/index/mask/overlap validation. Positive
    # proxy NLL avoids invoking the original rounded-q1 branch during validation.
    alm.chunk_kl(torch.ones_like(nll.detach()),supervised,chunks,temperature=temperature)
    if not chunks:return log_nll.sum()*0.,0,dict(ordinary_zero_positions=0,old_boundary_chunks=0)
    logs=[];teachers=[];old=[]
    for item in chunks:
        row,pos=item['row'],item['positions']
        logs.append(torch.logsumexp(log_nll[row,pos],dim=0)-math.log(temperature))
        old.append(-nll[row,pos].double().sum()/temperature)
        teachers.append(float(item['teacher_logprob'])/temperature)
    s,b=student_log_pair(torch.stack(logs));t=log_nll.new_tensor(teachers,dtype=torch.float64)
    loss=binary_kl_logpair(s,b,t).sum()
    boundary=torch.stack(old).eq(0)&t.ne(0)
    stats=dict(ordinary_zero_positions=int((nll[supervised]==0).sum()),old_boundary_chunks=int(boundary.sum()),
               min_log_nll=float(log_nll[supervised].detach().min()))
    return loss,len(chunks),stats
