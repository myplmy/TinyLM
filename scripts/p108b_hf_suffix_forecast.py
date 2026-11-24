"""Validated Gemma-style two-RMS residual/head suffix, not a model edit solver."""
import math
import torch
from scripts.p108b_lastlayer_forecast import rms_direction


def cap_logits(logits,cap):
    if cap is None:return logits
    if not isinstance(cap,(float,int)) or not math.isfinite(cap) or cap<=0:
        raise ValueError('positive finite softcap or None required')
    return torch.tanh(logits/cap)*cap


def predict(post_norm,final_norm,head,residual,down_output,change,cap=None):
    if(residual.ndim!=1 or down_output.shape!=residual.shape or change.shape!=residual.shape or
            any(not bool(torch.isfinite(v).all())for v in (residual,down_output,change)) or
            head.bias is not None):
        raise ValueError('same finite last-branch vectors and biasless linear head required')
    for norm in (post_norm,final_norm):
        if norm.weight.shape!=residual.shape or norm.eps<=0:
            raise ValueError('known Gemma1+weight RMS convention required')
    h=residual+post_norm(down_output)
    exact_h=residual+post_norm(down_output+change)
    exact=cap_logits(head(final_norm(exact_h)),cap)
    post_direction=rms_direction(down_output,change,post_norm.eps).to(down_output)*(1+post_norm.weight.float())
    end_direction=rms_direction(h,post_direction,final_norm.eps).to(h)*(1+final_norm.weight.float())
    raw=head(final_norm(h));linear_change=head(end_direction)
    if cap is not None:linear_change=linear_change*(1-torch.tanh(raw/cap).square())
    linear=cap_logits(raw,cap)+linear_change
    return exact,linear
