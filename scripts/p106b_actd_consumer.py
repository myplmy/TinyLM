"""One existing student head, original assistant CE, and verified ACTD positions."""
import math
import torch
from scripts.p106b_actd_anchor import actd_sums


def components(model,hidden,y,segments,positions,*,ce_denominator,actd_denominator,
               enable_actd,residual_weight=1.,chunk=64,checkpoint_heads=True):
    if (hidden.ndim!=3 or y.ndim!=2 or y.shape!=segments.shape or hidden.shape[:2]!=y.shape
            or y.dtype!=torch.long or segments.dtype!=torch.long
            or type(ce_denominator)is not int or ce_denominator<1
            or type(actd_denominator)is not int or actd_denominator<1
            or type(chunk)is not int or chunk<1 or type(enable_actd)is not bool):
        raise ValueError('matching native hidden/one-shift labels/owners and global integer denominators required')
    locations=torch.nonzero(y.ne(-100),as_tuple=False)
    keys=[tuple(x) for x in locations.cpu().tolist()];selected={};seen=set()
    for p in positions:
        key=(p['batch_row'],p['student_prefix_raw_index'])
        if key in seen or key not in keys:raise ValueError('unique ACTD position must be an original CE target')
        b,t=key
        if (int(y[b,t])!=p['student_target_id'] or int(segments[b,t])!=p['owner'] or p['owner']<1
                or p['student_target_raw_index']!=t+1 or not p['distribution']['accepted']):
            raise ValueError('ACTD shifted target identity/owner/acceptance differs')
        seen.add(key);selected[key]=p['distribution']
    zero=hidden.sum()*0.;ce=zero;anchor=zero;residual=zero;actd_count=0
    for start in range(0,len(keys),chunk):
        part=keys[start:start+chunk];loc=locations[start:start+chunk]
        features=hidden[loc[:,0],loc[:,1]].unsqueeze(0)
        labels=y[loc[:,0],loc[:,1]]
        included=[(i,selected[key]) for i,key in enumerate(part) if key in selected] if enable_actd else []
        indices=torch.tensor([i for i,_ in included],dtype=torch.long,device=hidden.device)
        anchors=torch.tensor([d['anchor_ids'] for _,d in included],dtype=torch.long,device=hidden.device)
        teacher_dtype=torch.float64 if hidden.dtype==torch.float64 else torch.float32
        scores=torch.tensor([d['native_logits'] for _,d in included],dtype=teacher_dtype,device=hidden.device)
        if not included:
            anchors=torch.empty((0,128),dtype=torch.long,device=hidden.device)
            scores=torch.empty((0,128),dtype=teacher_dtype,device=hidden.device)
        def head(features,labels,indices,anchors,scores):
            logits=model._head_logits(features).squeeze(0)
            if not bool(torch.isfinite(logits).all()):raise ValueError('nonfinite native head')
            ce=torch.nn.functional.cross_entropy(logits.float() if logits.dtype!=torch.float64 else logits,labels,reduction='sum')
            if indices.numel():
                terms=actd_sums(logits.index_select(0,indices),anchors,scores.detach(),residual_weight=residual_weight)
                return ce,terms['anchor_sum'],terms['residual_sum']
            zero=logits.sum()*0.;return ce,zero,zero
        if checkpoint_heads and torch.is_grad_enabled() and features.requires_grad:
            from torch.utils.checkpoint import checkpoint
            a,b,c=checkpoint(head,features,labels,indices,anchors,scores,use_reentrant=False,preserve_rng_state=False)
        else:a,b,c=head(features,labels,indices,anchors,scores)
        ce=ce+a;anchor=anchor+b;residual=residual+c;actd_count+=len(included)
    loss=ce/ce_denominator
    if enable_actd:loss=loss+(anchor+residual_weight*residual)/actd_denominator
    return dict(loss=loss,ce_sum=ce,anchor_sum=anchor,residual_sum=residual,
        ce_targets=len(keys),actd_positions=actd_count,original_target_positions=keys)
