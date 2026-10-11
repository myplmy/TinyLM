"""Output-equivalent nullspace reflection for final residual cosine controls."""
from __future__ import annotations
import torch


def head_basis(weight, scale):
    if weight.ndim!=2 or not 0<weight.shape[1]<weight.shape[0]:
        raise ValueError("factorized final readout required")
    s=torch.as_tensor(scale).detach().double().cpu()
    if s.numel() not in (1,weight.shape[0]):
        raise ValueError("scalar or per-channel final scale required")
    effective=weight.detach().double().cpu()*s.reshape(-1,1)
    if not torch.isfinite(effective).all(): raise ValueError("finite readout required")
    q=torch.linalg.qr(effective,mode="reduced")[0]
    residual=effective-q@(q.T@effective)
    relative=float(residual.norm()/effective.norm().clamp_min(1e-30))
    if relative>1e-10: raise ValueError("readout range basis mismatch")
    return q,relative


def reflect(x,basis):
    v=x.detach().double().cpu()
    if v.ndim!=1 or basis.shape[0]!=v.numel() or not torch.isfinite(v).all():
        raise ValueError("finite aligned residual required")
    visible=basis@(basis.T@v)
    null=v-visible
    y=visible-null
    return y.float(),{"null_energy_fraction":float(null.square().sum()/v.square().sum().clamp_min(1e-30)),
        "norm_relative_difference_fp64":float((y.norm()-v.norm()).abs()/v.norm().clamp_min(1e-30)),
        "visible_projection_max_difference_fp64":float((basis.T@y-basis.T@v).abs().max())}


def cosine(a,b):
    a,b=a.detach().double().cpu(),b.detach().double().cpu()
    if a.shape!=b.shape or a.norm()==0 or b.norm()==0:raise ValueError("aligned nonzero cosine vectors required")
    return float(torch.dot(a,b)/(a.norm()*b.norm()))
