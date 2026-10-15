"""Training-only fact selection on exact fictional producers, never truth grading."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import math


def new_head(dim,device='cpu',rank=64):
    import torch
    with torch.random.fork_rng(devices=[]):
        head=torch.nn.ModuleDict({name:torch.nn.Linear(dim,rank,bias=False) for name in ('q','k')})
    generator=torch.Generator(device='cpu').manual_seed(20261016)
    with torch.no_grad():
        for p in head.parameters():p.normal_(mean=0.,std=1/math.sqrt(dim),generator=generator)
    return head.to(device)


def auxiliary_sum(head,hidden,y,segments,labels):
    import torch
    if len(labels)!=len(hidden) or y.shape!=segments.shape or tuple(y.shape)!=tuple(hidden.shape[:2]):raise ValueError('aligned batch/tokens required')
    total=hidden.sum()*0+sum(p.sum()*0 for p in head.parameters());row_indices=[];positions=[];groups=[];plans=[];group_count=0
    for row,label in enumerate(labels):
        if label is None:continue
        spans=label['spans'];queries=label['queries']
        if not spans or not queries:raise ValueError('known source facts and supervised queries required')
        owners=segments[row].gt(0).nonzero().flatten()
        if not len(owners):raise ValueError('assistant segment missing')
        first_assistant=int(owners[0])
        for fact,span in enumerate(spans):
            if not span or span!=sorted(set(span)) or min(span)<0 or max(span)>=first_assistant:
                raise ValueError('fact keys must be in user source before ANY assistant body')
            row_indices.extend([row]*len(span));positions.extend(span);groups.extend([group_count+fact]*len(span))
        for query in queries:
            q=query['position'];turn=query['turn'];target=query['label']
            allowed=(y[row].ne(-100)&segments[row].eq(turn)).nonzero().flatten()
            if not len(allowed) or q!=int(allowed[0]):raise ValueError('query must be first supervised answer predictor, not answer hidden')
            if not 0<=target<len(spans):raise ValueError('known target fact index')
        plans.append((row,group_count,len(spans),queries));group_count+=len(spans)
    if not plans:return total,0,0,0
    rr=torch.tensor(row_indices,device=hidden.device);pp=torch.tensor(positions,device=hidden.device);gg=torch.tensor(groups,device=hidden.device)
    gathered=hidden[rr,pp,:]
    pooled=hidden.new_zeros((group_count,hidden.shape[-1])).index_add(0,gg,gathered)
    sizes=torch.bincount(gg,minlength=group_count).to(pooled.dtype)
    pooled=pooled/sizes[:,None];keys=head['k'](pooled)
    correct=count=0
    for row,start,n,queries in plans:
        qp=torch.tensor([q['position'] for q in queries],device=hidden.device)
        projected=head['q'](hidden[row,qp,:]);logits=(projected.float()@keys[start:start+n].float().T)/math.sqrt(head['q'].out_features)
        target=torch.tensor([q['label'] for q in queries],device=hidden.device)
        total=total+torch.nn.functional.cross_entropy(logits,target,reduction='mean')
        count+=len(queries);correct+=int(logits.argmax(-1).eq(target).sum())
    return total,len(plans),count,correct
