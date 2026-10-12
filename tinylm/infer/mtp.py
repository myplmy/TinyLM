"""Opt-in bounded greedy self-speculation with main-model verification.

Not the complete FastMTP self-distillation method. Independent trained horizons
2/3/4 propose future tokens; only main-model choices are committed. A rejected
suffix discards its KV and rebuilds the actual prefix. Sampling is deliberately
unsupported until a correct acceptance/residual-distribution path is tested.
GPU floating-point batching parity must be measured, not presumed from CPU.
"""
from __future__ import annotations
import time
import torch


@torch.no_grad()
def sample_verified(model,cfg,tok,prompt,*,max_new=100,temperature=0.,top_k=0,
                    device=None,use_cache=True,stop_at_eos=True,eos_id=None,
                    return_metadata=False,stop_token_sequences=None,mtp_tokens=2):
    if type(mtp_tokens) is not int or mtp_tokens not in (2,3,4) or temperature!=0:
        raise ValueError('verified MTP currently supports greedy total tokens2/3/4 only')
    if model.training or max_new<0:
        raise ValueError('MTP decode needs eval model and nonnegative generation length')
    needed=set(range(2,mtp_tokens+1))
    if not getattr(cfg,'mtp_aux',False) or not needed.issubset(cfg.mtp_horizons):
        raise ValueError('requested contiguous horizons were not trained/attached')
    device=device or next(model.parameters()).device
    dev_type=device if isinstance(device,str) else device.type
    requested=bool(stop_at_eos)
    if eos_id is None:
        eos_id=tok.token_to_id('<eos>')
        if eos_id is None:eos_id,stop_at_eos=-1,False
    available=eos_id>=0
    initial=tok.encode(prompt).ids
    if not initial:raise ValueError('MTP prompt must contain at least one token')
    stops=tuple(tuple(s) for s in (stop_token_sequences or ()))
    if any(not s or any(type(t) is not int or t<0 for t in s) for s in stops):
        raise ValueError('invalid stop sequence')
    x=torch.tensor([initial],dtype=torch.long,device=device)
    if len(initial)+max_new>cfg.max_seq_len:
        from .generate import sample
        result=sample(model,cfg,tok,prompt,max_new=max_new,temperature=0.,top_k=top_k,
            device=device,use_cache=use_cache,stop_at_eos=stop_at_eos,eos_id=eos_id,
            return_metadata=return_metadata,stop_token_sequences=stops,mtp_tokens=1)
        if return_metadata:result[1]['mtp']={'active':False,'fallback_reason':'CONTEXT_ROLLOVER',
            'total_prediction_tokens':mtp_tokens,'head_tensor_bytes':model.mtp_head_bytes()}
        return result
    generated=[];past=None;matched=None;ended=False
    stats=dict(total_prediction_tokens=mtp_tokens,primary_calls=0,verification_calls=0,
        proposed_aux_tokens=0,verified_aux_tokens=0,accepted_aux_tokens=0,cache_rebuilds=0,
        head_tensor_bytes=model.mtp_head_bytes(),distribution_scope='GREEDY_MAIN_VERIFICATION',
        gpu_backend_parity='REQUIRES_RUNTIME_GATE')
    start=time.perf_counter()
    def emit(tokens):
        nonlocal x,ended,matched
        for token in tokens:
            if len(generated)>=max_new:break
            generated.append(token)
            x=torch.cat((x,torch.tensor([[token]],device=device,dtype=torch.long)),dim=1)
            if stop_at_eos and token==eos_id:
                ended=True;break
            matched=next((s for s in stops if len(generated)>=len(s)
                and tuple(generated[-len(s):])==s),None)
            if matched is not None:break
    # Bootstrap one main token. Keep the hidden that predicted it, then reuse
    # verification hidden; do not pay a second full primary call every block.
    hidden=None
    if max_new:
        with torch.autocast(dev_type,dtype=torch.bfloat16,enabled=dev_type=='cuda'):
            if use_cache:
                logits,hidden,past=model(x,use_cache=True,logits_last_only=True,return_mtp_hidden=True)
            else:
                logits,hidden=model(x,logits_last_only=True,return_mtp_hidden=True)
        stats['primary_calls']+=1
        emit([int(logits[:,-1].float().argmax(-1).item())])
    while len(generated)<max_new and not ended and matched is None:
        if hidden is None:
            # A rejection discards speculative suffix cache. Rebuild the exact
            # accepted prefix excluding its already-emitted final pending token.
            with torch.autocast(dev_type,dtype=torch.bfloat16,enabled=dev_type=='cuda'):
                if use_cache:
                    _,hidden,past=model(x[:,:-1],use_cache=True,logits_last_only=True,return_mtp_hidden=True)
                else:
                    _,hidden=model(x[:,:-1],logits_last_only=True,return_mtp_hidden=True)
            stats['primary_calls']+=1;stats['cache_rebuilds']+=1
        gamma=min(mtp_tokens-1,max_new-len(generated))
        proposals=[]
        for h in range(2,gamma+2):
            with torch.autocast(dev_type,dtype=torch.bfloat16,enabled=dev_type=='cuda'):
                value=model.mtp_aux_logits(hidden[:,-1:,:],h)
            proposals.append(int(value[:,-1].float().argmax(-1).item()))
        stats['proposed_aux_tokens']+=gamma
        draft=torch.tensor([proposals],dtype=torch.long,device=device)
        with torch.autocast(dev_type,dtype=torch.bfloat16,enabled=dev_type=='cuda'):
            if use_cache:
                values,new_hidden,new_past=model(torch.cat((x[:,-1:],draft),dim=1),
                    past_kv=past,use_cache=True,return_mtp_hidden=True)
            else:
                full_hidden=model(torch.cat((x,draft),dim=1),return_hidden=True)
                new_hidden=full_hidden[:,-(gamma+1):,:]
                values=model._head_logits(new_hidden);new_past=None
        stats['verification_calls']+=1
        choices=values.float().argmax(-1)[0].tolist()
        committed=[];rejected=False
        for i,candidate in enumerate(proposals):
            selected=choices[i];committed.append(selected)
            stats['verified_aux_tokens']+=1
            if selected!=candidate:rejected=True;break
            stats['accepted_aux_tokens']+=1
            if stop_at_eos and selected==eos_id:break
        if not rejected and len(committed)==gamma and not (stop_at_eos and committed[-1]==eos_id):
            committed.append(choices[-1])  # target-model bonus, never an unverified draft
        emit(committed)
        if rejected:
            hidden=None;past=None
        else:
            hidden=new_hidden[:,-1:,:];past=new_past
    text=tok.decode(x[0].tolist())
    stats.update(wall_sec=time.perf_counter()-start,generated_tokens=len(generated),
        draft_acceptance=(stats['accepted_aux_tokens']/stats['proposed_aux_tokens']
            if stats['proposed_aux_tokens'] else None))
    reason=('EOS' if ended else 'STOP_SEQUENCE' if matched is not None else
        'EOS_UNAVAILABLE' if requested and not available else 'MAX_NEW_EOS_DISABLED' if not requested else 'MAX_NEW')
    metadata=dict(finish_reason=reason,generated_tokens=len(generated),max_new=max_new,
        eos_token_available=available,stop_at_eos_requested=requested,
        stop_at_eos_effective=bool(stop_at_eos and available),mtp=stats)
    if stops:metadata.update(stop_token_sequences=[list(s) for s in stops],
        matched_stop_sequence=list(matched) if matched else None)
    return (text,metadata) if return_metadata else text
