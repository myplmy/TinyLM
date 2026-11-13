"""Instance-scoped, stateless fixed-width FP32 calls; no library mutation."""
from contextlib import contextmanager
from types import MethodType
import torch


def padded_inputs(inputs, *, width, pad_id, vocab):
    if (type(width)is not int or width<1 or type(vocab)is not int or vocab<2
            or not isinstance(inputs,torch.Tensor) or inputs.dtype!=torch.long or inputs.ndim!=2
            or not inputs.shape[0] or not 1<=inputs.shape[1]<=width
            or type(pad_id)is not int or not 0<=pad_id<vocab
            or bool((inputs<0).any()) or bool((inputs>=vocab).any())):
        raise ValueError('bounded batch/time vocabulary token IDs required')
    padded=inputs.new_full((inputs.shape[0],width),pad_id)
    mask=inputs.new_zeros((inputs.shape[0],width))
    padded[:,:inputs.shape[1]]=inputs;mask[:,:inputs.shape[1]]=1
    return padded,mask


def logits(model, inputs, *, width, pad_id, vocab, check=lambda:None, stats=None):
    """Each row uses identical B1*Twidth body AND full vocabulary head shapes."""
    padded,mask=padded_inputs(inputs,width=width,pad_id=pad_id,vocab=vocab)
    outputs=[]
    for index in range(inputs.shape[0]):
        check()
        with torch.no_grad(),torch.autocast(device_type=inputs.device.type,enabled=False):
            output=model(input_ids=padded[index:index+1],attention_mask=mask[index:index+1],
                         use_cache=False,past_key_values=None,logits_to_keep=0)
        if (output.past_key_values is not None or output.logits.dtype!=torch.float32
                or tuple(output.logits.shape)!=(1,width,vocab) or not bool(torch.isfinite(output.logits).all())):
            raise ValueError('stateless finite full FP32 body/head output required')
        prefix=output.logits[:,:inputs.shape[1],:]
        # A contiguous view still retains the width-sized storage: clone short prefixes.
        outputs.append(prefix.clone() if inputs.shape[1]<width else prefix)
        del prefix,output
        if stats is not None:
            stats['serial_batch1_calls']=stats.get('serial_batch1_calls',0)+1
            stats['real_input_slots']=stats.get('real_input_slots',0)+inputs.shape[1]
            stats['fixed_input_slots']=stats.get('fixed_input_slots',0)+width
        check()
    return outputs[0] if len(outputs)==1 else torch.cat(outputs,dim=0)


@contextmanager
def fixed_calls(lm, *, width=1024, pad_id=248044, check=lambda:None, stats=None):
    previous=lm.__dict__.get('_model_call');had_instance='_model_call' in lm.__dict__
    def call(owner,inps,attn_mask=None,labels=None):
        if attn_mask is not None or labels is not None:
            raise ValueError('same causal likelihood-only public call contract required')
        return logits(owner.model,inps,width=width,pad_id=pad_id,
                      vocab=owner.model.config.vocab_size,check=check,stats=stats)
    lm._model_call=MethodType(call,lm)
    try:yield
    finally:
        if had_instance:lm._model_call=previous
        else:del lm._model_call


def compare_prefix(reference, observed, *, atol, rtol, chunk_positions=16):
    if (reference.ndim!=3 or observed.ndim!=3 or reference.shape[0]!=1
            or observed.shape[0]!=1 or reference.shape[2]!=observed.shape[2]
            or reference.shape[1]>observed.shape[1] or reference.shape[1]<1
            or type(chunk_positions)is not int or chunk_positions<1):
        raise ValueError('matching nonempty prefix/vocabulary required')
    count=0;maximum=0.;argmax=True;finite=True
    for start in range(0,reference.shape[1],chunk_positions):
        end=min(start+chunk_positions,reference.shape[1]);a=reference[:,start:end,:];b=observed[:,start:end,:]
        finite=finite and bool(torch.isfinite(a).all()) and bool(torch.isfinite(b).all())
        maximum=max(maximum,float((a-b).abs().max()))
        count+=int((~torch.isclose(a,b,atol=atol,rtol=rtol)).sum())
        argmax=argmax and bool(torch.equal(a.argmax(-1),b.argmax(-1)))
    return dict(close=finite and count==0,finite=finite,max_abs=maximum,outside_tolerance=count,
                prefix_positions=reference.shape[1],vocabulary=reference.shape[2],argmax_equal=argmax,
                atol=atol,rtol=rtol)
