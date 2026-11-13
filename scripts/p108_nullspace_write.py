"""Empirical protected-key interpolation, inspired by AlphaEdit projection.

This is a finite calibration constraint, not a global language-preservation
theorem or the paper's full dataset/model/protocol reproduction.
"""
import math
import torch


def constrained_factors(target_keys, value_deltas, protected_keys, *, rank_rtol=1e-8):
    if (target_keys.ndim!=2 or value_deltas.ndim!=2 or protected_keys.ndim!=2
            or target_keys.shape[0]!=value_deltas.shape[0] or not target_keys.shape[0]
            or target_keys.shape[1]!=protected_keys.shape[1] or not protected_keys.shape[0]
            or type(rank_rtol) not in (int,float) or not math.isfinite(rank_rtol) or not 0<rank_rtol<1
            or any(not torch.isfinite(x).all() for x in (target_keys,value_deltas,protected_keys))):
        raise ValueError('finite target/value/protected matrix contract required')
    k,v,p=(x.detach().cpu().double() for x in (target_keys,value_deltas,protected_keys))
    if not float(k.norm()) or not float(v.norm()): raise ValueError('nonzero target and value required')
    _,s,vh=torch.linalg.svd(p,full_matrices=False)
    keep=s>s.max()*rank_rtol
    basis=vh[keep]
    projected=k-(k@basis.T)@basis
    projected_relative=float(projected.norm())/float(k.norm())
    if projected_relative<=1e-7:
        raise ValueError('protected span makes target interpolation infeasible at stable precision')
    gram=projected@projected.T
    inverse=torch.linalg.pinv(gram,hermitian=True,rtol=rank_rtol)
    left=v.T@inverse
    right=projected
    desired=left@(right@k.T)
    residual=float((desired-v.T).norm())/max(float(v.norm()),1e-30)
    protection=float((left@(right@p.T)).norm())
    if residual>1e-5:
        raise ValueError('protected span makes target interpolation infeasible')
    if protection/max(float(v.norm()),1e-30)>1e-5:
        raise ValueError('protected span makes stable preservation infeasible')
    stats=dict(target_rows=len(k),protected_rows=len(p),input_dim=k.shape[1],output_dim=v.shape[1],
        protected_rank=int(keep.sum()),nominal_rank=min(len(k),v.shape[1]),rank_rtol=rank_rtol,
        projected_key_relative_norm=projected_relative,
        target_relative_residual=residual,protected_output_l2=protection,
        delta_frobenius=float(torch.linalg.vector_norm(left@right)),
        scope='FINITE_ORIGINAL_CALIBRATION_KEYS_ONLY_NOT_GLOBAL_PRESERVATION')
    return dict(left=left,right=right),stats


def dense_delta(factors):
    left,right=factors['left'],factors['right']
    if left.ndim!=2 or right.ndim!=2 or left.shape[1]!=right.shape[0]:
        raise ValueError('factor dimensions differ')
    result=(left.double()@right.double()).float()
    if not torch.isfinite(result).all():raise ValueError('nonfinite realized update')
    return result
