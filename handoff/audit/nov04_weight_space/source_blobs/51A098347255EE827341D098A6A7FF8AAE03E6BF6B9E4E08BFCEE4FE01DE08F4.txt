"""Local logit-margin targets and bounded low-rank ridge weight corrections.

This is supervised calibration inspired by linear model-editing concepts. It
is not a ROME/MEMIT implementation, an optimizer, or a generic truth detector.
"""
import math
import torch


def margin_targets(gradients,margins,*,target_margin=1.,max_gap=10.):
    if (gradients.ndim!=2 or margins.ndim!=1 or gradients.shape[0]!=margins.numel()
            or not torch.isfinite(gradients).all() or not torch.isfinite(margins).all()
            or not 0<target_margin<=max_gap or not math.isfinite(max_gap)):
        raise ValueError('invalid local margin/gradient contract')
    norm2=gradients.double().square().sum(1)
    gap=(target_margin-margins.double()).clamp(min=0,max=max_gap)
    valid=norm2>1e-12
    multiplier=torch.where(valid,gap/norm2.clamp_min(1e-12),torch.zeros_like(gap))
    values=gradients.double()*multiplier[:,None]
    return values,dict(rows=margins.numel(),already_at_margin=int((gap==0).sum()),
                       zero_gradient=int((~valid).sum()),clipped_gaps=int(((target_margin-margins)>max_gap).sum()))


def ridge_factors(keys,values,*,ridge=.01,rank=16):
    if (keys.ndim!=2 or values.ndim!=2 or keys.shape[0]!=values.shape[0] or not keys.shape[0]
            or not torch.isfinite(keys).all() or not torch.isfinite(values).all()
            or type(rank) is not int or not 1<=rank<=min(keys.shape[1],values.shape[1])
            or type(ridge) not in (int,float) or not math.isfinite(ridge) or ridge<=0):
        raise ValueError('finite paired keys/values, positive ridge and rank required')
    k,v=keys.detach().cpu().double(),values.detach().cpu().double()
    norms=k.norm(dim=1)
    if bool((norms<=1e-12).any()):raise ValueError('zero key cannot be calibrated')
    k,v=k/norms[:,None],v/norms[:,None]
    gram=k@k.T
    system=gram+float(ridge)*torch.eye(k.shape[0],dtype=k.dtype)
    coefficients=torch.linalg.solve(system,v)
    full=coefficients.T@k
    u,s,vh=torch.linalg.svd(full,full_matrices=False)
    left=(u[:,:rank]*s[:rank]).float()
    right=vh[:rank].float()
    delta=left.double()@right.double()
    if not torch.isfinite(delta).all():raise ValueError('nonfinite fitted update')
    gradient=(full@k.T-v.T)@k+float(ridge)*full
    return dict(left=left,right=right),dict(keys=int(keys.shape[0]),input_dim=keys.shape[1],
        output_dim=values.shape[1],nominal_rank=rank,ridge=float(ridge),
        normalized_target_sq=float(v.square().sum()),
        untruncated_residual_sq=float((k@full.T-v).square().sum()),
        rank_residual_sq=float((k@delta.T-v).square().sum()),
        normal_equation_max_abs=float(gradient.abs().max()),
        dense_delta_frobenius=float(delta.norm()),
        factor_bytes=left.numel()*left.element_size()+right.numel()*right.element_size())


def bounded_delta(factors,weight,relative_cap):
    if (type(relative_cap) not in (int,float) or not math.isfinite(relative_cap)
            or not 0<relative_cap<=.1):raise ValueError('positive relative cap up to .1 required')
    left,right=factors['left'].to(weight),factors['right'].to(weight)
    if left.ndim!=2 or right.ndim!=2 or left.shape[1]!=right.shape[0]:
        raise ValueError('factor dimensions differ')
    delta=left@right
    if delta.shape!=weight.shape or not torch.isfinite(delta).all():
        raise ValueError('factor and weight contract differs')
    norm=float(delta.norm());base=float(weight.norm())
    scale=min(1.,relative_cap*base/max(norm,1e-30))
    result=delta*scale
    return result,dict(relative_cap=float(relative_cap),scale=scale,raw_norm=norm,
                       effective_requested_norm=float(result.norm()),weight_norm=base,
                       actual_relative_norm=float(result.norm())/max(base,1e-30))
