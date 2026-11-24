"""Detached CPU edit proposals with support and original-centred norm bounds.

The objective for an increment E is ||E K-R||^2+tr(E C E.T). The constraint
is on the resulting Q=D+E, not on E alone. D is the current displacement
from the original matrix. These are local algebraic proposals, never truth
or global quality guarantees. No model loading, I/O, defaults, or optimizer.
"""
from __future__ import annotations

import math
import torch


def _finite(value, ndim):
    if (not isinstance(value, torch.Tensor) or value.ndim != ndim or
            not value.is_floating_point() or value.requires_grad or
            not bool(torch.isfinite(value).all())):
        raise ValueError('detached finite floating tensor required')
    return value.detach().cpu().double()


def remaining_layer_budget(total, other_displacements):
    if type(total) not in (int, float) or not math.isfinite(total) or total <= 0:
        raise ValueError('positive finite original-centred budget required')
    energy = sum(float(_finite(v, 2).square().sum()) for v in other_displacements)
    if energy >= total**2:
        raise ValueError('no budget remains outside the current unique parameter')
    return math.sqrt(total**2-energy)


def select_support(proposal, *, denominator=1, score=None, seed=None):
    """Equal row counts; stable column ties or declared matched random seed."""
    p = _finite(proposal, 2)
    if type(denominator) is not int or denominator < 1 or p.shape[1] % denominator:
        raise ValueError('support denominator must divide the input width')
    count = p.shape[1] // denominator
    if seed is not None:
        if type(seed) is not int or score is not None:
            raise ValueError('random support must have only an explicit integer seed')
        generator = torch.Generator(device='cpu').manual_seed(seed)
        indices = torch.stack([torch.randperm(p.shape[1], generator=generator)[:count]
                               for _ in range(p.shape[0])])
    else:
        s = p.abs() if score is None else _finite(score, 2)
        if s.shape != p.shape:
            raise ValueError('support score and proposal shapes differ')
        indices = torch.argsort(s, dim=1, descending=True, stable=True)[:, :count]
    mask = torch.zeros_like(p, dtype=torch.bool)
    mask.scatter_(1, indices, True)
    return mask


def solve_increment(keys, residual, moment, displacement, budget, *, support=None,
                    rounding_margin=1e-6):
    """Solve a common-multiplier trust region, including repeat cross terms.

    Only equal per-row support sizes are currently supported explicitly. Dense
    support reuses one eigensystem; sparse rows use their principal systems.
    Unsupported layouts fail rather than silently being changed to dense.
    """
    k, r, c, d = (_finite(x, 2) for x in (keys, residual, moment, displacement))
    out, width = d.shape
    if (k.shape[0] != width or r.shape != (out, k.shape[1]) or
            c.shape != (width, width) or k.shape[1] < 1 or
            type(budget) not in (int, float) or not math.isfinite(budget) or budget <= 0 or
            not 0 <= rounding_margin < .001):
        raise ValueError('compatible shapes and fixed positive budget required')
    if not torch.allclose(c, c.T, atol=1e-10, rtol=1e-10):
        raise ValueError('symmetric preservation moment required')
    c = (c+c.T)/2
    if int(torch.linalg.cholesky_ex(c).info) != 0:
        raise ValueError('positive definite preservation moment required')
    h, g = k@k.T+c, r@k.T
    dense = support is None
    if not dense:
        if (not isinstance(support, torch.Tensor) or support.shape != d.shape or
                support.dtype != torch.bool or support.device.type != 'cpu'):
            raise ValueError('explicit CPU boolean support required')
        sizes = support.sum(1)
        if not bool((sizes == sizes[0]).all()) or int(sizes[0]) < 1:
            raise ValueError('same nonzero number of allowed entries in each row required')
        dense = bool(support.all())
    if dense:
        eigen, vectors = torch.linalg.eigh(h)
        q_projected = g@vectors+(d@vectors)*eigen
        fixed_energy = 0.

        def candidate(mu):
            q = (q_projected/(eigen+mu))@vectors.T
            return q, float(q.square().sum())
    else:
        indices = support.nonzero(as_tuple=False)[:, 1].reshape(out, -1)
        h_sub = h[indices[:, :, None], indices[:, None, :]]
        eigen, vectors = torch.linalg.eigh(h_sub)
        d_sub, g_sub = d.gather(1, indices), g.gather(1, indices)
        d_rotated = torch.einsum('oi,oij->oj', d_sub, vectors)
        q_projected = torch.einsum('oi,oij->oj', g_sub, vectors)+d_rotated*eigen
        fixed_energy = max(0., float(d.square().sum()-d_sub.square().sum()))

        def candidate(mu):
            q_sub = torch.einsum('oj,oij->oi', q_projected/(eigen+mu), vectors)
            return q_sub, float(q_sub.square().sum())+fixed_energy
    if not bool((eigen > 0).all()) or not bool(torch.isfinite(eigen).all()):
        raise RuntimeError('positive finite local eigensystem required')
    target = budget*(1-rounding_margin)
    if fixed_energy >= target**2:
        raise ValueError('INFEASIBLE_FIXED_SUPPORT: untouched old displacement exceeds the budget')
    q, energy = candidate(0.)
    unconstrained = math.sqrt(energy)
    mu = 0.
    if energy > target**2:
        low, high = 0., max(1., float(eigen.max()))
        for _ in range(200):
            if candidate(high)[1] <= target**2:
                break
            high *= 2
        else:
            raise RuntimeError('finite trust-region multiplier unavailable')
        for _ in range(72):
            middle = (low+high)/2
            if candidate(middle)[1] > target**2:
                low = middle
            else:
                high = middle
        mu = high
        q, energy = candidate(mu)
    if dense:
        increment = q-d
    else:
        increment = torch.zeros_like(d)
        increment.scatter_(1, indices, q-d_sub)
    final = d+increment
    derivative = increment@h-g+mu*final
    if not dense:
        derivative = derivative[support]
    denominator = max(float(g.norm()), 1e-30)
    errors = increment@k-r
    stats = dict(budget=budget, requested_final_norm=float(final.norm()),
        increment_norm=float(increment.norm()), previous_norm=float(d.norm()),
        cross_term=2*float((d*increment).sum()), multiplier=mu,
        unconstrained_final_norm=unconstrained, rounding_margin=rounding_margin,
        allowed_entries=increment.numel() if dense else int(support.sum()),
        kkt_relative_residual=float(derivative.norm())/denominator,
        local_target_residual=float(errors.norm()),
        preservation_energy=float(((increment@c)*increment).sum()),
        objective=float(errors.square().sum()+((increment@c)*increment).sum()))
    if not bool(torch.isfinite(increment).all()) or float(final.norm()) > budget:
        raise RuntimeError('local proposal violates its original-centred trust region')
    return increment.float(), stats


def physical_change(original, current, requested):
    """One actual FP32 addition and its net/path deltas in exact double reads."""
    for tensor in (original, current, requested):
        _finite(tensor, 2)
    if (original.dtype != torch.float32 or current.dtype != torch.float32 or
            requested.dtype != torch.float32 or original.shape != current.shape or
            original.shape != requested.shape):
        raise ValueError('same FP32 physical matrix layout required')
    after = current+requested
    net = after.double()-original.double()
    step = after.double()-current.double()
    if bool((step.ne(0) & ~requested.ne(0)).any()):
        raise RuntimeError('FP32 update changed values outside its requested support')
    return after, dict(net_norm=float(net.norm()), step_norm=float(step.norm()),
        requested_norm=float(requested.double().norm()), changed_entries=int(net.ne(0).sum()),
        touched_entries=int(step.ne(0).sum()), requested_physical_max_error=float((step-requested.double()).abs().max()))


def predicted_gain(gradient, actual_increment):
    g, d = _finite(gradient, 2), _finite(actual_increment, 2)
    if g.shape != d.shape:
        raise ValueError('gradient and actual increment shapes differ')
    return -float((g*d).sum())
