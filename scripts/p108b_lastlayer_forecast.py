"""Analytic RMSNorm differential, with exact same-prefix error measures."""
import math
import torch


def rms_direction(x,direction,eps):
    if (x.ndim!=1 or x.shape!=direction.shape or not x.numel() or
            not isinstance(eps,(int,float)) or not math.isfinite(eps) or eps<=0 or
            any(not bool(torch.isfinite(v).all()) for v in (x,direction))):
        raise ValueError('same finite residual/direction vectors and positive epsilon required')
    h,d=x.double(),direction.double();energy=h.square().mean()+eps
    return (d-h*(h*d).mean()/energy)*energy.rsqrt()


def compare(before,observed,predicted):
    if (before.ndim!=1 or observed.shape!=before.shape or predicted.shape!=before.shape or
            any(not bool(torch.isfinite(v).all()) for v in (before,observed,predicted))):
        raise ValueError('same complete finite vocabulary required')
    error=predicted.double()-observed.double();actual=observed.double()-before.double()
    return dict(logit_rmse=float(error.square().mean().sqrt()),max_absolute_logit_error=float(error.abs().max()),
        response_relative_error=float(error.norm())/max(float(actual.norm()),1e-30),
        predicted_argmax=int(predicted.argmax()),actual_argmax=int(observed.argmax()),
        exact_argmax=bool(predicted.argmax()==observed.argmax()))
