"""Native factored student head and full teacher vocabulary, with explicit stop gradients."""
import torch
from torch.nn import functional as F
from scripts import p106b_dskdv2_contract as reference


def factored_logits(hidden,up,embedding):
    if (hidden.ndim!=2 or up.ndim!=2 or embedding.ndim!=2 or hidden.shape[1]!=up.shape[0]
            or up.shape[1]!=embedding.shape[1]):raise ValueError('native factored head dimensions required')
    return F.linear(F.linear(hidden,up.T),embedding)


def teacher_logits(hidden,head,*,indices=None,width=None):
    if hidden.ndim!=2 or head.ndim!=2 or hidden.shape[1]!=head.shape[1]:raise ValueError('full native teacher head dimensions required')
    if width is None:
        if indices is not None:raise ValueError('explicit fixed width is required with original row indices')
        return F.linear(hidden.unsqueeze(0),head)[0]
    if (type(width)is not int or width<hidden.shape[0]or not isinstance(indices,torch.Tensor)
            or indices.dtype!=torch.long or indices.shape!=(len(hidden),)or indices.device!=hidden.device
            or bool(((indices<0)|(indices>=width)).any())or len(torch.unique(indices))!=len(indices)):
        raise ValueError('unique original teacher positions in an explicit fixed head frame required')
    padded=torch.zeros((1,width,hidden.shape[1]),dtype=hidden.dtype,device=hidden.device)
    padded=padded.index_copy(1,indices,hidden.unsqueeze(0))
    return F.linear(padded,head)[0].index_select(0,indices)


def native_sums(student_hidden,teacher_hidden,up,embedding,teacher_head,t2s,s2t,mapped_teacher_argmax,*,teacher_indices=None,teacher_width=None):
    tensors=(student_hidden,teacher_hidden,up,embedding,teacher_head,t2s,s2t)
    if any(not isinstance(t,torch.Tensor)or t.ndim!=2 or t.dtype not in
            (torch.float16,torch.bfloat16,torch.float32,torch.float64)or not bool(torch.isfinite(t).all())for t in tensors):
        raise ValueError('finite native feature/head/projector matrices required')
    n,ds=student_hidden.shape;dt=teacher_hidden.shape[1]
    if (n<1 or teacher_hidden.shape[0]!=n or up.shape[0]!=ds or up.shape[1]!=embedding.shape[1]
            or teacher_head.shape[1]!=dt or t2s.shape!=(dt,ds)or s2t.shape!=(ds,dt)
            or min(len(embedding),len(teacher_head))<2 or len({t.device for t in tensors})!=1
            or not isinstance(mapped_teacher_argmax,torch.Tensor)or mapped_teacher_argmax.dtype!=torch.long
            or mapped_teacher_argmax.shape!=(n,)or mapped_teacher_argmax.device!=student_hidden.device
            or bool(((mapped_teacher_argmax<0)|(mapped_teacher_argmax>=len(embedding))).any())):
        raise ValueError('same aligned native positions, full vocabularies and complete mapped top1 required')
    dtype=torch.float64 if all(t.dtype==torch.float64 for t in tensors)else torch.float32
    hs=student_hidden.to(dtype);ht=teacher_hidden.detach().to(dtype)
    u=up.to(dtype);e=embedding.to(dtype);wt=teacher_head.detach().to(dtype)
    projected_teacher=factored_logits(ht@t2s.to(dtype),u.detach(),e.detach())
    student=factored_logits(hs,u,e)
    projected_student=teacher_logits(hs@s2t.detach().to(dtype),wt,indices=teacher_indices,width=teacher_width)
    teacher=teacher_logits(ht,wt,indices=teacher_indices,width=teacher_width)
    def forward_kl(student_logits,teacher_logits_):
        p=F.log_softmax(teacher_logits_.detach(),dim=-1);q=F.log_softmax(student_logits,dim=-1)
        return (p.exp()*(p-q)).sum()
    a=forward_kl(student,projected_teacher);b=forward_kl(projected_student,teacher)
    c=F.cross_entropy(projected_teacher,mapped_teacher_argmax,reduction='sum')
    return dict(student_kd_sum=a,teacher_kd_sum=b,projector_ce_sum=c,total_sum=a+b+c,
        positions=n,student_vocab=len(embedding),teacher_vocab=len(teacher_head),temperature=1.)


def initialize_native_bank(model,teacher_head,student_ids,teacher_ids):
    if model.embedding_quantized()is not None or model.emb_up is None:raise ValueError('same unexported native factored student required')
    up=model._emb_up_w().detach();embedding=model._emb_w().detach()
    if up.shape!=(768,256)or embedding.shape!=(32768,256)or teacher_head.shape!=(248320,1024):
        raise ValueError('inspected original full native head shapes required')
    if len(student_ids)!=23302 or len(teacher_ids)!=23302:raise ValueError('original exact ordinary23302 column pairs required')
    s=up.double()@embedding.index_select(0,torch.tensor(student_ids,dtype=torch.long)).double().T
    t=teacher_head.index_select(0,torch.tensor(teacher_ids,dtype=torch.long)).double().T
    result=reference.initialize_projectors(s,t,rtol=1e-8)
    return dict(t2s=result['t2s'].float(),s2t=result['s2t'].float(),stats=result['stats'])
