"""Assistant-turn-aware MTP sums, independent from pinned legacy M0 training.

Horizons include the existing next-token prediction at1 and optional2/3/4.
No model, tokenizer, checkpoint, data or GPU is opened on import.
"""
from __future__ import annotations
from dataclasses import dataclass
import torch
import torch.nn.functional as F
from tinylm.data.sft import IGNORE, encode_conversation


@dataclass
class Record:
    x: list
    y: list
    segments: list

    @property
    def x_tokens(self): return len(self.x)

    @property
    def targets(self): return sum(v != IGNORE for v in self.y)


def encode_record(row, tok, context=1024):
    """Assign one segment per exact assistant loss span, including turn end."""
    from tinylm.chat.serialize import loss_spans
    for message in row['messages']:
        if message.get('role')=='assistant' and isinstance(message.get('content'),list):
            if any(block.get('type')=='thinking' for block in message['content']):
                raise ValueError('reasoning blocks require a separate training contract')
    ids, labels, text = encode_conversation(row, tok, 'chatml')
    offsets = tok.encode(text).offsets
    if len(ids) != len(offsets) or not 1 < len(ids) <= context+1:
        raise ValueError('SFT row context/token-offset contract')
    spans = loss_spans(row, 'chatml')
    segments=[]
    for label,(start,end) in zip(labels,offsets):
        owners=[i+1 for i,(a,b) in enumerate(spans) if end>start and start>=a and end<=b]
        if label != IGNORE and len(owners)!=1:
            raise ValueError('assistant target lacks exactly one turn owner')
        segments.append(owners[0] if label != IGNORE else 0)
    record=Record(ids[:-1],labels[1:],segments[1:])
    if not record.targets:
        raise ValueError('zero assistant targets')
    return record


def pad_records(records, pad_id, device='cpu', *, fixed_width=None, batch_size=None):
    if not records: raise ValueError('empty microbatch')
    width=max(len(r.x) for r in records) if fixed_width is None else fixed_width
    if width<max(len(r.x) for r in records) or (batch_size is not None and batch_size<len(records)):
        raise ValueError('fixed execution shape cannot truncate real rows')
    xs=[r.x+[pad_id]*(width-len(r.x)) for r in records]
    ys=[r.y+[IGNORE]*(width-len(r.y)) for r in records]
    ss=[r.segments+[0]*(width-len(r.segments)) for r in records]
    for _ in range(max(0,(batch_size or len(records))-len(records))):
        xs.append([pad_id]*width);ys.append([IGNORE]*width);ss.append([0]*width)
    x=torch.tensor(xs,dtype=torch.long,device=device)
    y=torch.tensor(ys,dtype=torch.long,device=device)
    seg=torch.tensor(ss,dtype=torch.long,device=device)
    return x,y,seg


def horizon_targets(y, segments, horizon):
    """At hidden[t], predict raw[t+h], never another role/assistant turn.

    y already carries the one-token shift. Every intervening supervised token
    must belong to the same nonzero assistant turn. The terminal token itself
    remains a legal target; subsequent turns and padding never are.
    """
    if (y.ndim!=2 or segments.shape!=y.shape or type(horizon) is not int
            or horizon not in (1,2,3,4)):
        raise ValueError('aligned SFT targets/turns and horizon1..4 required')
    if horizon>y.shape[1]:
        return y[:,:0],segments[:,:0].bool()
    windows=segments.unfold(1,horizon,1)
    labels=y.unfold(1,horizon,1)
    valid=windows[...,0].gt(0) & windows.eq(windows[...,:1]).all(-1) & labels.ne(IGNORE).all(-1)
    targets=y[:,horizon-1:].masked_fill(~valid,IGNORE)
    return targets,valid


def count_record(record, horizons=(1,2,3,4)):
    """Pure-list denominator: no CUDA synchronization or padded mass inflation."""
    counts={}
    for h in horizons:
        counts[h]=sum(record.segments[i]>0 and
            all(record.segments[j]==record.segments[i] and record.y[j]!=IGNORE
                for j in range(i,i+h)) for i in range(max(0,len(record.y)-h+1)))
    return counts


def coefficients(update, updates, horizons=(2,3,4), total_weight=.3):
    if updates<1 or not 0<=update<updates or not 0<=total_weight<=1:
        raise ValueError('MTP update/schedule weight invalid')
    if len(set(horizons))!=len(horizons) or any(h not in (2,3,4) for h in horizons):
        raise ValueError('MTP horizons differ')
    progress=(update+1)/updates
    scale=min(1.,progress/.05,max(0.,(1-progress)/.2))
    denom=sum(1/h for h in horizons)
    return {h:total_weight*scale*(1/h)/denom for h in horizons} if horizons else {}


def ce_sum(logits, targets, chunk=2048):
    if chunk<1 or logits.shape[:-1]!=targets.shape:
        raise ValueError('logits/target shape or CE chunk differs')
    flat=logits.reshape(-1,logits.shape[-1]);target=targets.reshape(-1)
    total=logits.reshape(-1)[:1].sum()*0.
    for i in range(0,target.numel(),chunk):
        total=total+F.cross_entropy(flat[i:i+chunk].float(),target[i:i+chunk],
            ignore_index=IGNORE,reduction='sum')
    return total


def components(model, hidden, y, segments, horizons=(2,3,4), chunk=2048, checkpoint_heads=True):
    """One forward; bounded positional head/CE chunks for main and auxiliary."""
    sums={};counts={}
    for h in (1,)+tuple(horizons):
        target,valid=horizon_targets(y,segments,h)
        counts[h]=int(valid.sum())
        total=hidden.sum()*0.
        width=target.shape[1]
        position_chunk=max(1,chunk//hidden.shape[0])
        for start in range(0,width,position_chunk):
            end=min(start+position_chunk,width)
            block=target[:,start:end]
            if not bool(block.ne(IGNORE).any()):continue
            keep=block.ne(IGNORE)
            features=hidden[:,start:end][keep].unsqueeze(0)
            block=block[keep].unsqueeze(0)
            def head_ce(features,targets,which=h):
                logits=model._head_logits(features) if which==1 else model.mtp_aux_logits(features,which)
                return ce_sum(logits,targets,chunk)
            if checkpoint_heads and torch.is_grad_enabled() and features.requires_grad:
                from torch.utils.checkpoint import checkpoint
                part=checkpoint(head_ce,features,block,use_reentrant=False,preserve_rng_state=False)
            else:
                part=head_ce(features,block)
            total=total+part
        sums[h]=total
    return sums,counts


def normalized_loss(sums, denominators, weights):
    """The denominator belongs to the whole optimizer update, not each micro."""
    if denominators.get(1,0)<=0:raise ValueError('zero update NTP targets')
    loss=sums[1]/denominators[1]
    for h,weight in weights.items():
        if weight and denominators.get(h,0)>0:
            loss=loss+weight*sums[h]/denominators[h]
    return loss


def projection_memory(dim, emb_rank, total_tokens, bytes_per_parameter=4):
    if total_tokens not in (1,2,3,4) or min(dim,emb_rank,bytes_per_parameter)<=0:
        raise ValueError('memory profile invalid')
    parameters=(total_tokens-1)*dim*emb_rank
    return dict(total_prediction_tokens=total_tokens,auxiliary_heads=total_tokens-1,
        parameters=parameters,tensor_bytes=parameters*bytes_per_parameter,
        tensor_mib=parameters*bytes_per_parameter/2**20,
        scope='projection tensors only; shared vocabulary/KV/logits/optimizer excluded')
