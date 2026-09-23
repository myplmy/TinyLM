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
