"""P102A S1/S2/S3 reference math; no default trainer integration."""
from __future__ import annotations

import torch
import torch.nn.functional as F


def factorized_ce_chunks(hidden, up, emb, targets, chunk):
    """Reference CE sum without constructing one full [tokens,vocab] logits tensor."""
    if hidden.ndim != 2 or up.ndim != 2 or emb.ndim != 2:
        raise ValueError("matrix shapes are required")
    if hidden.shape[1] != up.shape[0] or up.shape[1] != emb.shape[1]:
        raise ValueError("factorized dimensions mismatch")
    if targets.numel() != hidden.shape[0] or chunk < 1:
        raise ValueError("targets/chunk mismatch")
    total = None
    for start in range(0, hidden.shape[0], chunk):
        projected = hidden[start:start + chunk] @ up
        logits = projected @ emb.T
        part = F.cross_entropy(logits.float(), targets[start:start + chunk],
                               ignore_index=-100, reduction="sum")
        total = part if total is None else total + part
    return total


class _LossFirstCE(torch.autograd.Function):
    """Recompute row chunks in backward; never retain full-vocabulary logits."""

    @staticmethod
    def forward(ctx, hidden, up, emb, targets, chunk):
        if (hidden.ndim != 2 or up.ndim != 2 or emb.ndim != 2
                or hidden.shape[1] != up.shape[0] or up.shape[1] != emb.shape[1]
                or targets.ndim != 1 or targets.numel() != hidden.shape[0]
                or targets.dtype != torch.long or int(chunk) < 1):
            raise ValueError("invalid loss-first factorized CE shapes or targets")
        if any(value.dtype != torch.float32 for value in (hidden, up, emb)):
            raise ValueError("P102A loss-first prototype requires FP32 tensors")
        ctx.save_for_backward(hidden, up, emb, targets)
        ctx.chunk = int(chunk)
        total = hidden.new_zeros(())
        with torch.no_grad(), torch.autocast(device_type=hidden.device.type, enabled=False):
            for start in range(0, hidden.shape[0], ctx.chunk):
                end = min(start + ctx.chunk, hidden.shape[0])
                logits = (hidden[start:end] @ up) @ emb.T
                total += F.cross_entropy(logits, targets[start:end],
                                         ignore_index=-100, reduction="sum")
        return total

    @staticmethod
    def backward(ctx, grad_output):
        hidden, up, emb, targets = ctx.saved_tensors
        dh = torch.zeros_like(hidden) if ctx.needs_input_grad[0] else None
        du = torch.zeros_like(up) if ctx.needs_input_grad[1] else None
        de = torch.zeros_like(emb) if ctx.needs_input_grad[2] else None
        for start in range(0, hidden.shape[0], ctx.chunk):
            end = min(start + ctx.chunk, hidden.shape[0])
            with torch.enable_grad(), torch.autocast(device_type=hidden.device.type, enabled=False):
                h = hidden[start:end].detach().requires_grad_()
                u = up.detach().requires_grad_()
                e = emb.detach().requires_grad_()
                part = F.cross_entropy((h @ u) @ e.T, targets[start:end],
                                       ignore_index=-100, reduction="sum")
                gh, gu, ge = torch.autograd.grad(part, (h, u, e))
            if dh is not None:
                dh[start:end] = gh * grad_output
            if du is not None:
                du.add_(gu * grad_output)
            if de is not None:
                de.add_(ge * grad_output)
        return dh, du, de, None, None


def factorized_ce_loss_first(hidden, up, emb, targets, chunk):
    """FP32 S1 loss sum with recomputed backward, for opt-in correctness gates."""
    return _LossFirstCE.apply(hidden, up, emb, targets, chunk)


def update_local_vjp(surrogate, weight, accumulated_gradient):
    """Apply a fixed surrogate's VJP once after micro-batch output gradients sum."""
    if surrogate.shape != accumulated_gradient.shape or not surrogate.requires_grad:
        raise ValueError("surrogate/gradient mismatch")
    return torch.autograd.grad(surrogate, weight, grad_outputs=accumulated_gradient,
                               retain_graph=False)[0]


def sampled_mtp_loss(loss_sums, valid_counts, selected, *, probability):
    """Horvitz-Thompson estimator with the all-microbatch valid-token denominator."""
    if not (len(loss_sums) == len(valid_counts) == len(selected)) or not 0 < probability <= 1:
        raise ValueError("invalid MTP sampling arguments")
    denominator = sum(valid_counts)
    if denominator < 1:
        return None
    picked = [loss_sums[j] / probability for j, flag in enumerate(selected) if flag]
    if not picked:
        raise ValueError("no selected micro-batch for nonempty MTP target")
    return sum(picked) / denominator
