"""Bound the existing finite-key interpolation; do not duplicate its solver."""
import math
import torch
from scripts import p108_nullspace_write as existing

def candidate(keys,values,protected,budget,*,protect,rank_rtol=1e-8):
    if (type(protect)is not bool or not isinstance(budget,(float,int))or
        not math.isfinite(budget)or budget<=0 or keys.ndim!=2 or values.ndim!=2 or
        protected.ndim!=2 or keys.shape[1]!=values.shape[1]or protected.shape[1]!=keys.shape[0]):
        raise ValueError('explicit protection, positive norm and native column layout required')
    selected=protected if protect else torch.zeros(1,keys.shape[0],dtype=torch.float64)
    factors,stats=existing.constrained_factors(keys.T,values.T,selected,rank_rtol=rank_rtol)
    full=factors['left']@factors['right'];norm=float(full.norm())
    if not math.isfinite(norm)or norm<=0:raise ValueError('nonzero finite interpolation required')
    scale=budget*(1-1e-6)/norm
    requested=(full*scale).float()
    stats.update(normalization_scale=scale,requested_norm=float(requested.double().norm()),
        target_signal_fraction_before_fp32=scale,protection_used=protect,
        nominal_protected_positions=len(protected),
        normalized_protection_residual=float((requested.double()@protected.double().T).norm())/
            max(float(requested.double().norm())*float(protected.double().norm()),1e-30))
    return requested,stats
