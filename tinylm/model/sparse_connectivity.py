"""Experimental primitives shared by P025B and P092 (not wired into TLinear yet)."""
from __future__ import annotations

import torch


class _ConnectivityMaskSTE(torch.autograd.Function):
    """Masked forward with a dense latent-gradient proxy for regrowth scoring."""

    @staticmethod
    def forward(ctx, weight, mask):
        if weight.shape != mask.shape:
            raise ValueError(f"weight/mask shape mismatch: {weight.shape} != {mask.shape}")
        return weight * mask.to(dtype=weight.dtype)

    @staticmethod
    def backward(ctx, grad_output):
        return grad_output, None


def connectivity_weight(weight, mask, *, dense_regrowth_gradient: bool = False):
    """Apply a structural mask, optionally retaining inactive gradient scores."""
    if dense_regrowth_gradient:
        return _ConnectivityMaskSTE.apply(weight, mask)
    return weight * mask.to(dtype=weight.dtype)


def exact_nm_mask(weight, *, n: int = 2, m: int = 4):
    """Return a deterministic magnitude top-N mask over last-dimension M blocks."""
    if not (0 < n < m):
        raise ValueError(f"N:M requires 0 < N < M, got {n}:{m}")
    if weight.ndim != 2 or weight.shape[1] % m:
        raise ValueError(f"weight must be [O,I] with I divisible by {m}, got {tuple(weight.shape)}")
    groups = weight.detach().abs().reshape(weight.shape[0], -1, m)
    indices = groups.topk(n, dim=-1, largest=True, sorted=False).indices
    mask = torch.zeros_like(groups, dtype=torch.bool)
    mask.scatter_(-1, indices, True)
    return mask.reshape_as(weight)
