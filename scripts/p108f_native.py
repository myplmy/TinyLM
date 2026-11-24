"""Temporary native FP32 Linear after-state and the verified Gemma head path."""
from contextlib import contextmanager
import numpy as np
import torch
from scripts import diag_p108b_hf_canary as owner
from scripts import p108_weight_space as identity
from scripts import p108b_hf_suffix_forecast as suffix
from scripts.p108b_lastlayer_forecast import rms_direction


@contextmanager
def temporary_after(module,after):
    if(not isinstance(module,torch.nn.Linear)or module.bias is not None
       or module.weight.dtype!=torch.float32 or hasattr(module,"_wq")
       or after.dtype!=np.float32 or tuple(after.shape)!=tuple(module.weight.shape)
       or not np.isfinite(after).all()):
        raise ValueError("native biasless FP32 Linear without quantization cache required")
    before_sha=identity.tensor_sha(module.weight)
    target=torch.from_numpy(after).to(module.weight)
    try:
        with owner.edit(module,torch.zeros_like(module.weight)):
            with torch.no_grad():module.weight.copy_(target)
            if identity.tensor_sha(module.weight)!=identity.tensor_sha(torch.from_numpy(after)):
                raise RuntimeError("native exact after bits differ")
            yield dict(before_sha256=before_sha,after_sha256=identity.tensor_sha(module.weight))
    finally:
        target=None
        if identity.tensor_sha(module.weight)!=before_sha:raise RuntimeError("native original bits not restored")


def gemma_head(body,residual):
    device=body.lm_head.weight.device
    x=torch.as_tensor(residual,dtype=torch.float32,device=device)
    raw=body.lm_head(body.model.norm(x[None,None]))[0,0]
    return suffix.cap_logits(raw,body.config.final_logit_softcapping)


def gemma_linear_head(body,residual,direction):
    device=body.lm_head.weight.device
    x=torch.as_tensor(residual,dtype=torch.float32,device=device)
    d=torch.as_tensor(direction,dtype=torch.float32,device=device)
    raw=body.lm_head(body.model.norm(x[None,None]))[0,0]
    normalized_direction=rms_direction(x,d,body.model.norm.eps).to(x)*(1+body.model.norm.weight.float())
    change=body.lm_head(normalized_direction[None,None])[0,0]
    cap=body.config.final_logit_softcapping
    if cap is not None:change=change*(1-torch.tanh(raw/cap).square())
    return suffix.cap_logits(raw,cap)+change
