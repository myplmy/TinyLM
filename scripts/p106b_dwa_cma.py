"""DWA CMA for explicit supervised views, microbatch1 and raw update sums.

The author source was reviewed at8396502. This is an independent implementation
with explicit supervised gathering and strict zero-mass/std HOLD, not a vendored
author environment or a quality result. Existing DWA/DP modules are unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


class AdmissionHold(ValueError):
    pass


@dataclass
class NativeView:
    input_embeddings: object
    target_embeddings: object
    hidden: object
    targets: object
    prediction_positions: tuple
    target_positions: tuple

    @property
    def count(self):
        return len(self.prediction_positions)


def native_next_view(torch, full_ids, full_supervised, full_hidden, embedding):
    ids, mask = tuple(full_ids), tuple(full_supervised)
    if (len(ids) < 2 or len(ids) != len(mask) or full_hidden.ndim != 2 or len(full_hidden) != len(ids)
            or any(type(i) is not int or i < 0 for i in ids) or any(type(i) is not bool for i in mask)):
        raise AdmissionHold('explicit full native IDs/hidden and original boolean target mask required')
    positions = tuple(i for i in range(len(ids)-1) if mask[i+1])
    if not positions:
        raise AdmissionHold('no original next-target supervision; do not substitute prefix rows')
    targets = tuple(i+1 for i in positions)
    current = torch.tensor([ids[i] for i in positions],dtype=torch.long,device=full_hidden.device)
    following = torch.tensor([ids[i] for i in targets],dtype=torch.long,device=full_hidden.device)
    return NativeView(embedding(current),embedding(following),full_hidden[list(positions)],following,positions,targets)


def scalar_std_normalize(torch, tensor):
    if tensor.numel() < 2 or not bool(torch.isfinite(tensor).all()):
        raise AdmissionHold('finite scalar-std source tensor required')
    scale = tensor.std(unbiased=True)
    if not bool(torch.isfinite(scale)) or float(scale.detach()) <= torch.finfo(tensor.dtype).eps:
        raise AdmissionHold('source scalar std has zero mass; no silent epsilon substitution')
    return tensor/scale


def cross_model_attention(torch, student, teacher, *, query, t2s, s2t,
                          student_head, teacher_head):
    if student.count < 1 or teacher.count < 1:
        raise AdmissionHold('complete nonempty supervised student/teacher views required')
    sx = torch.cat((student.input_embeddings.detach(),student.target_embeddings.detach()),dim=-1)
    tx = torch.cat((teacher.input_embeddings.detach(),teacher.target_embeddings.detach()),dim=-1)
    keys = scalar_std_normalize(torch,tx)
    values = scalar_std_normalize(torch,teacher.hidden.detach()) + scalar_std_normalize(torch,teacher.target_embeddings.detach())
    queries = query(sx)
    scores = (queries @ keys.T)/math.sqrt(keys.shape[-1])
    forward = scores.softmax(-1)
    reverse = scores.T.softmax(-1)
    aligned_teacher = forward @ t2s(values)
    aligned_student = reverse @ s2t(student.hidden)
    to_student = aligned_teacher @ student_head.detach().T
    to_teacher = aligned_student @ teacher_head.detach().T
    if not all(bool(torch.isfinite(value).all()) for value in (scores,to_student,to_teacher)):
        raise AdmissionHold('CMA contains nonfinite native values')
    return dict(attention=forward,reverse_attention=reverse,student_logits=to_student,teacher_logits=to_teacher)


def source_token_weights(torch, student_logits, teacher_logits):
    def entropy(logits):
        probs = logits.softmax(-1)
        return -(probs*(probs+1e-9).log()).sum(-1)
    hs = entropy(student_logits)
    wt = (1-entropy(teacher_logits)/math.log(teacher_logits.shape[-1])).clamp(0,1)
    if (bool((teacher_logits == teacher_logits[:,:1]).all())
            or float(hs.sum().detach()) <= torch.finfo(hs.dtype).eps
            or float(wt.sum().detach()) <= torch.finfo(wt.dtype).eps):
        raise AdmissionHold('source entropy/certainty has zero weight mass')
    return (hs*len(hs)/(hs.sum()+1e-9)).detach(), (wt*len(wt)/(wt.sum()+1e-9)).detach()


def source_band_cost(torch,cost,attention,*,alpha=.7,base=5.,entropy_scale=2.,penalty=1.):
    if (cost.ndim != 2 or attention.shape != cost.shape or min(cost.shape) < 1
            or not 0 <= alpha <= 1 or min(base,entropy_scale,penalty) < 0
            or not all(math.isfinite(value) for value in (alpha,base,entropy_scale,penalty))):
        raise AdmissionHold('explicit finite source band parameters and matching cross attention required')
    a = attention.detach()
    if (not bool(torch.isfinite(a).all()) or bool((a<0).any())
            or not torch.allclose(a.sum(-1),torch.ones_like(a.sum(-1)),atol=1e-6,rtol=1e-6)):
        raise AdmissionHold('row-stochastic source CMA required before band smoothing')
    # Match the reviewed source's smoothing and zero-based coordinate policy.
    smoothed = (a+1e-9)/(a.sum(-1,keepdim=True)+1e-9)
    n,m = cost.shape
    j = torch.arange(m,device=cost.device,dtype=cost.dtype)
    i = torch.arange(n,device=cost.device,dtype=cost.dtype)
    center = alpha*(smoothed*j).sum(-1)+(1-alpha)*i*m/n
    entropy = -(smoothed*smoothed.log()).sum(-1)
    width = base+entropy_scale*entropy
    outside = (j[None,:]-center[:,None]).abs()>width[:,None]
    return cost+penalty*outside.to(cost.dtype)


def directed_alignment(torch,student,teacher,attention,*,dtw,band):
    from torch.nn import functional as F
    if (student.ndim != 2 or teacher.ndim != 2 or student.shape[-1] != teacher.shape[-1]
            or not bool(torch.isfinite(student).all() and torch.isfinite(teacher).all())
            or bool((student.norm(dim=-1)==0).any() or (teacher.norm(dim=-1)==0).any())):
        raise AdmissionHold('finite nonzero same-space full representations required')
    x,y = F.normalize(student,dim=-1),F.normalize(teacher,dim=-1)
    cross = source_band_cost(torch,1-x@y.T,attention,**band)
    # The author uses cross-only banding and two unbanded self terms.
    return dtw(cross)-.5*(dtw(1-x@x.T)+dtw(1-y@y.T))


def loss_components(torch,student,teacher,student_logits,teacher_logits,*,query,t2s,s2t,
                    embedding_t2s,student_head,teacher_head,kd_gate_scale,dtw=None,band=None):
    from torch.nn import functional as F
    if (not math.isfinite(kd_gate_scale) or not 0 <= kd_gate_scale <= 1
            or student_logits.shape != (student.count,student_head.shape[0])
            or teacher_logits.shape != (teacher.count,teacher_head.shape[0])
            or min(student_logits.shape[-1],teacher_logits.shape[-1]) < 2
            or not bool(torch.isfinite(student_logits).all() and torch.isfinite(teacher_logits).all())):
        raise AdmissionHold('complete native logits and explicit confidence warmup scale required')
    cma = cross_model_attention(torch,student,teacher,query=query,t2s=t2s,s2t=s2t,
        student_head=student_head,teacher_head=teacher_head)
    ws,wt = source_token_weights(torch,student_logits,teacher_logits.detach())
    target_s = cma['student_logits'].detach().softmax(-1)
    target_t = teacher_logits.detach().softmax(-1)
    confidence = target_s.amax(-1).detach()*kd_gate_scale
    kls = F.kl_div(student_logits.log_softmax(-1),target_s,reduction='none').sum(-1)
    klt = F.kl_div(cma['teacher_logits'].log_softmax(-1),target_t,reduction='none').sum(-1)
    raw = dict(student_ce=F.cross_entropy(student_logits,student.targets,reduction='sum'),
        projector_ce=F.cross_entropy(cma['student_logits'],student.targets,reduction='sum'),
        student_kd=(ws*confidence*kls).sum(),teacher_kd=(wt*klt).sum())
    if dtw is not None:
        if band is None:
            raise AdmissionHold('explicit directed band/self policy required for both representations')
        raw['dtw_hidden'] = directed_alignment(torch,student.hidden,t2s(teacher.hidden.detach()),
            cma['attention'],dtw=dtw,band=band)
        raw['dtw_embedding'] = directed_alignment(torch,student.target_embeddings,
            embedding_t2s(teacher.target_embeddings.detach()),cma['attention'],dtw=dtw,band=band)
    else:
        raw['dtw_hidden'] = raw['student_ce']*0
        raw['dtw_embedding'] = raw['student_ce']*0
    return dict(raw=raw,student_count=student.count,teacher_count=teacher.count,
        student_entropy_weight=ws,teacher_weight=wt,student_confidence_gate=confidence,cma=cma,
        policy='SOURCE_CMA_MICROBATCH1_SUPERVISED_GATHER_GLOBAL_UPDATE_DENOM',
        source_product_weight_renormalized=False,dtw_run=dtw is not None,quality_claim=False)


def update_loss(packets,*,global_student_targets,ce_rate=1.,kd_rate=1.,dtw_rate=1.):
    if (not packets or type(global_student_targets) is not int or global_student_targets < 1
            or sum(p['student_count'] for p in packets) != global_student_targets
            or any(not math.isfinite(rate) or rate < 0 for rate in (ce_rate,kd_rate,dtw_rate))):
        raise AdmissionHold('complete update target accounting and finite nonnegative coefficients required')
    numerator = sum(ce_rate*p['raw']['student_ce'] + kd_rate*(p['raw']['projector_ce']
        +p['raw']['student_kd']+p['raw']['teacher_kd'])
        +dtw_rate*(p['raw']['dtw_hidden']+p['raw']['dtw_embedding']) for p in packets)
    return numerator/global_student_targets
