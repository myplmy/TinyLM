"""DSKDv2 dual-space CPU primitives; full vocabulary and exact byte spans.

Not a complete native-model training adapter. Original CE is owned by caller.
No model, tokenizer, file, optimizer or CUDA is opened by this module.
"""
import hashlib
import math
import torch
from torch.nn import functional as F


def exact_pairs(text,student,teacher):
    if not isinstance(text,str) or not text:raise ValueError('one unchanged source text required')
    raw=text.encode('utf-8',errors='strict')
    def validate(rows):
        if not isinstance(rows,list) or not rows:raise ValueError('complete native byte spans required')
        cursor=0
        for index,r in enumerate(rows):
            a,b=r['byte_start'],r['byte_end']
            if (type(a)is not int or type(b)is not int or a!=cursor or not a<b<=len(raw)
                    or r['raw_index']!=index or type(r['token_id'])is not int or r['token_id']<0
                    or type(r['supervised'])is not bool or type(r['turn_id'])is not int
                    or r['turn_id']<0 or (r['supervised'] and r['turn_id']<=0)
                    or r['bytes_sha256'].upper()!=hashlib.sha256(raw[a:b]).hexdigest().upper()):
                raise ValueError('native span/prefix/byte identity or owner changed')
            if r['special_kind']is not None and (not isinstance(r['special_kind'],str)
                    or r['special_kind'].encode('utf-8')!=raw[a:b]):raise ValueError('declared special bytes changed')
            cursor=b
        if cursor!=len(raw):raise ValueError('whole unchanged source coverage required')
    validate(student);validate(teacher)
    lookup={(r['byte_start'],r['byte_end'],r['special_kind'],r['turn_id']):r for r in teacher if r['supervised']}
    pairs=[];holds=[]
    for s in student:
        if not s['supervised']:continue
        key=(s['byte_start'],s['byte_end'],s['special_kind'],s['turn_id']);t=lookup.get(key)
        reason=('NO_PREVIOUS_CAUSAL_PREDICTOR' if s['raw_index']==0 or (t is not None and t['raw_index']==0)
                else 'TOKEN_SPAN_OR_OWNER_NOT_EXACT' if t is None else None)
        if reason:holds.append(dict(student_target_raw_index=s['raw_index'],reason=reason));continue
        pairs.append(dict(student_target_raw_index=s['raw_index'],student_predictor_raw_index=s['raw_index']-1,
            teacher_target_raw_index=t['raw_index'],teacher_predictor_raw_index=t['raw_index']-1,
            student_target_id=s['token_id'],teacher_target_id=t['token_id'],owner=s['turn_id'],
            prefix_bytes=s['byte_start'],token_end_bytes=s['byte_end'],token_bytes_sha256=s['bytes_sha256'],
            prefix_sha256=hashlib.sha256(raw[:s['byte_start']]).hexdigest().upper(),lookahead_bytes=0))
    return pairs,holds


def initialize_projectors(student_overlap,teacher_overlap,*,rtol=1e-8):
    if (not isinstance(student_overlap,torch.Tensor) or not isinstance(teacher_overlap,torch.Tensor)
            or student_overlap.ndim!=2 or teacher_overlap.ndim!=2
            or any(t.dtype not in (torch.float16,torch.bfloat16,torch.float32,torch.float64) for t in (student_overlap,teacher_overlap))
            or min(student_overlap.shape[0],teacher_overlap.shape[0])<1
            or student_overlap.shape[1]!=teacher_overlap.shape[1] or not student_overlap.shape[1]
            or not all(bool(torch.isfinite(t).all()) for t in (student_overlap,teacher_overlap))
            or type(rtol)not in(int,float) or not math.isfinite(rtol) or not 0<rtol<1):
        raise ValueError('finite same ordered overlap columns and explicit rank tolerance required')
    s=student_overlap.detach().cpu().double();t=teacher_overlap.detach().cpu().double()
    t2s=t@torch.linalg.pinv(s,rtol=rtol);s2t=s@torch.linalg.pinv(t,rtol=rtol)
    norm=lambda x:max(float(x.norm()),1e-300)
    return dict(t2s=t2s,s2t=s2t,stats=dict(overlap_columns=s.shape[1],student_hidden=s.shape[0],
        teacher_hidden=t.shape[0],student_overlap_rank=int(torch.linalg.matrix_rank(s,rtol=rtol)),
        teacher_overlap_rank=int(torch.linalg.matrix_rank(t,rtol=rtol)),rtol=rtol,
        t2s_relative_logit_error=float((t2s@s-t).norm())/norm(t),
        s2t_relative_logit_error=float((s2t@t-s).norm())/norm(s)))


def dskd_sums(student_hidden,teacher_hidden,student_head,teacher_head,t2s,s2t,mapped_teacher_argmax):
    tensors=(student_hidden,teacher_hidden,student_head,teacher_head,t2s,s2t)
    if any(not isinstance(t,torch.Tensor) or t.ndim!=2 or t.dtype not in
            (torch.float16,torch.bfloat16,torch.float32,torch.float64) or not bool(torch.isfinite(t).all()) for t in tensors):
        raise ValueError('finite floating full head/hidden/projector matrices required')
    n,d=student_hidden.shape;D=teacher_hidden.shape[1];vs=student_head.shape[1];vt=teacher_head.shape[1]
    if (n<1 or teacher_hidden.shape[0]!=n or student_head.shape[0]!=d or teacher_head.shape[0]!=D
            or t2s.shape!=(D,d) or s2t.shape!=(d,D) or min(vs,vt)<2
            or len({t.device for t in tensors})!=1
            or not isinstance(mapped_teacher_argmax,torch.Tensor)
            or mapped_teacher_argmax.dtype!=torch.long or mapped_teacher_argmax.shape!=(n,)
            or mapped_teacher_argmax.device!=student_hidden.device
            or bool(((mapped_teacher_argmax<0)|(mapped_teacher_argmax>=vs)).any())):
        raise ValueError('aligned native positions, full vocabularies and exact mapped teacher top1 required')
    dtype=torch.float64 if all(t.dtype==torch.float64 for t in tensors) else torch.float32
    hs=student_hidden.to(dtype);ht=teacher_hidden.detach().to(dtype)
    ws=student_head.to(dtype);wt=teacher_head.detach().to(dtype)
    projected_teacher=(ht@t2s.to(dtype))@ws.detach()
    projected_student=(hs@s2t.detach().to(dtype))@wt
    def forward_kl(student_logits,teacher_logits):
        lp=F.log_softmax(teacher_logits.detach(),dim=-1);lq=F.log_softmax(student_logits,dim=-1)
        return (lp.exp()*(lp-lq)).sum()
    stu=forward_kl(hs@ws,projected_teacher)
    tea=forward_kl(projected_student,ht@wt)
    ce=F.cross_entropy(projected_teacher,mapped_teacher_argmax,reduction='sum')
    return dict(student_kd_sum=stu,teacher_kd_sum=tea,projector_ce_sum=ce,total_sum=stu+tea+ce,
                positions=n,student_vocab=vs,teacher_vocab=vt,temperature=1.)


def normalized(parts,*,global_positions):
    if type(global_positions)is not int or global_positions<parts['positions'] or global_positions<1:
        raise ValueError('whole optimizer-group aligned position denominator required')
    return parts['total_sum']/global_positions
