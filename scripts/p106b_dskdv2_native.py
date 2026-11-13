"""Observe the unchanged fixed-shape teacher head, without changing its call."""
import torch


def capture_native(model,inputs,*,fixed_call,width,vocab,hidden_width,pad_id,check=lambda:None,stats=None):
    if (model.training or inputs.ndim!=2 or inputs.shape[0]!=1 or inputs.dtype!=torch.long
            or not 0<inputs.shape[1]<=width or min(width,vocab,hidden_width)<1):
        raise ValueError('eval batch-one unchanged native token prefix required')
    head=model.get_output_embeddings();captured={};handles=[]
    def before(_module,args):
        if 'hidden'in captured:raise RuntimeError('exactly one full-width native head invocation required')
        h=args[0]
        if h.shape!=(1,width,hidden_width) or h.dtype!=torch.float32 or not bool(torch.isfinite(h).all()):
            raise ValueError('full-width normalized native FP32 head input required')
        captured['hidden']=h.detach().cpu().clone()
    def after(_module,_args,output):
        if 'logits'in captured or output.shape!=(1,width,vocab) or output.dtype!=torch.float32:
            raise ValueError('exact original full-vocabulary native FP32 head output required')
        captured['logits']=output.detach()
    try:
        handles.append(head.register_forward_pre_hook(before));handles.append(head.register_forward_hook(after))
        logits=fixed_call(model,inputs,width=width,pad_id=pad_id,vocab=vocab,check=check,stats=stats)
        if set(captured)!={'hidden','logits'} or not torch.equal(logits,captured['logits'][:,:inputs.shape[1],:]):
            raise RuntimeError('qualified fixed logits must exactly equal the observed native head prefix')
        features=captured['hidden'][0,:inputs.shape[1]].contiguous().clone()
        proof=dict(native_head_calls=1,actual_body_width=width,actual_vocab=vocab,actual_hidden_width=hidden_width,
                   prefix_tokens=inputs.shape[1],head_output_matches_qualified_logits_exact=True,
                   normalized_hidden_shape=list(features.shape),normalized_hidden_dtype=str(features.dtype))
        return logits,features,proof
    finally:
        for handle in reversed(handles):handle.remove()
        captured.clear();head=None
