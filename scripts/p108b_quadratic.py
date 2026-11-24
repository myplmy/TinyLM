"""Trust-region quadratic step with explicit incremental/total preservation.

Orthogonality allows norm searches in the eigenbasis without rematerializing
the dense matrix on every bisection. Existing validation/accounting is reused.
"""
import math
import torch
from scripts import p108b_solver as original

physical_change=original.physical_change
predicted_gain=original.predicted_gain
remaining_layer_budget=original.remaining_layer_budget
select_support=original.select_support


def solve_increment(keys,residual,moment,displacement,budget,*,support=None,rounding_margin=1e-6,total_preservation=True):
    k,r,c,d=(original._finite(x,2)for x in(keys,residual,moment,displacement))
    out,width=d.shape
    if (min(out,width,k.shape[1])<1 or k.shape[0]!=width or r.shape!=(out,k.shape[1])or c.shape!=(width,width)or
            not math.isfinite(budget)or budget<=0 or not 0<=rounding_margin<.001):
        raise ValueError('compatible finite quadratic shapes and positive budget required')
    if not torch.allclose(c,c.T,rtol=1e-10,atol=1e-10)or int(torch.linalg.cholesky_ex(c).info):
        raise ValueError('symmetric positive preservation moment required')
    h=k@k.T+c;g=r@k.T;dc=d@c if total_preservation else torch.zeros_like(d)
    dense=support is None
    if not dense:
        if support.dtype!=torch.bool or support.shape!=d.shape or support.device.type!='cpu':raise ValueError('CPU equal-row boolean support required')
        counts=support.sum(1)
        if int(counts[0])<1 or not bool((counts==counts[0]).all()):raise ValueError('equal positive row support required')
        dense=bool(support.all())
    fixed_energy=0.
    if dense:
        eigen,vectors=torch.linalg.eigh(h)
        transformed=(g+d@h-dc)@vectors
    else:
        indices=support.nonzero(as_tuple=False)[:,1].reshape(out,-1)
        hs=h[indices[:,:,None],indices[:,None,:]]
        eigen,vectors=torch.linalg.eigh(hs);ds=d.gather(1,indices)
        rhs=g.gather(1,indices)+torch.bmm(ds[:,None,:],hs).squeeze(1)-dc.gather(1,indices)
        transformed=torch.bmm(rhs[:,None,:],vectors).squeeze(1)
        fixed_energy=float(d[~support].square().sum())
    target=budget*(1-rounding_margin)
    if fixed_energy>=target**2:raise ValueError('fixed outside-support displacement exceeds the budget')
    def energy(mu):return float((transformed/(eigen+mu)).square().sum())+fixed_energy
    unconstrained=energy(0.);mu=0.
    if unconstrained>target**2:
        lo,hi=0.,max(1.,float(eigen.max()))
        for _ in range(200):
            if energy(hi)<=target**2:break
            hi*=2
        else:raise RuntimeError('finite multiplier unavailable')
        for _ in range(72):
            mid=(lo+hi)/2
            if energy(mid)>target**2:lo=mid
            else:hi=mid
        mu=hi
    projected=transformed/(eigen+mu)
    if dense:
        q=projected@vectors.T;increment=q-d
    else:
        qs=torch.bmm(projected[:,None,:],vectors.transpose(1,2)).squeeze(1)
        increment=torch.zeros_like(d);increment.scatter_(1,indices,qs-d.gather(1,indices));q=d+increment
    derivative=increment@h-g+dc+mu*q
    if not dense:derivative=derivative[support]
    actual_norm=float(q.norm())
    if not bool(torch.isfinite(increment).all())or actual_norm>budget:raise RuntimeError('physical trust region not satisfied')
    protected=q if total_preservation else increment
    preserve=float(((protected@c)*protected).sum());error=increment@k-r
    return increment.float(),dict(budget=budget,requested_final_norm=actual_norm,increment_norm=float(increment.norm()),
        previous_norm=float(d.norm()),cross_term=2*float((d*increment).sum()),multiplier=mu,
        unconstrained_final_norm=math.sqrt(unconstrained),rounding_margin=rounding_margin,
        allowed_entries=increment.numel()if dense else int(support.sum()),
        kkt_relative_residual=float(derivative.norm())/max(float(g.norm()+dc.norm()),1e-30),
        local_target_residual=float(error.norm()),preservation_energy=preserve,
        objective=float(error.square().sum())+preserve,
        regularizer_origin='ORIGINAL_CUMULATIVE_DISPLACEMENT'if total_preservation else'CURRENT_INCREMENT',
        multiplier_energy_basis='ORTHONORMAL_EIGEN_COORDINATES')
