"""Recompute ALM and ACTD reductions without changing the native head GEMMs."""

import torch
from torch.autograd.function import once_differentiable

from scripts.p106b_actd_anchor import actd_sums as original_actd_sums
from scripts.p106b_alm_logtail import log_nll_from_logits as original_log_nll


class _LogTail(torch.autograd.Function):
    @staticmethod
    def forward(ctx, logits, labels, rows):
        ctx.save_for_backward(logits, labels)
        ctx.rows = rows
        return torch.cat([original_log_nll(z, y)
                          for z, y in zip(logits.split(rows), labels.split(rows), strict=True)])

    @staticmethod
    @once_differentiable
    def backward(ctx, upstream):
        logits, labels = ctx.saved_tensors
        gradient = torch.empty_like(logits)
        for start in range(0, len(logits), ctx.rows):
            part = slice(start, start + ctx.rows)
            with torch.enable_grad():
                z = logits[part].detach().requires_grad_()
                value = original_log_nll(z, labels[part])
                gradient[part] = torch.autograd.grad(value, z, upstream[part])[0]
        return gradient, None, None


def log_nll_from_logits(logits, labels, *, rows):
    """The same FP64 stable position-wise log NLL with a bounded scratch block."""
    if len(logits) <= rows:
        return original_log_nll(logits, labels)
    return _LogTail.apply(logits, labels, rows)


def _actd_position_losses(logits, anchors, scores, residual_weight):
    terms = original_actd_sums(logits, anchors, scores, residual_weight=residual_weight)
    probs = terms['anchor_probabilities']
    teacher = scores.to(probs).softmax(dim=-1)
    return (teacher - probs).abs().sum(dim=-1), terms['residual_probabilities']


class _AnchorResidual(torch.autograd.Function):
    @staticmethod
    def forward(ctx, logits, anchors, scores, residual_weight, rows):
        ctx.save_for_backward(logits, anchors, scores)
        ctx.residual_weight, ctx.rows = residual_weight, rows
        parts = [_actd_position_losses(z, a, s, residual_weight)
                 for z, a, s in zip(logits.split(rows), anchors.split(rows), scores.split(rows), strict=True)]
        # Reduce in the native full position order after limiting the vocabulary scratch space.
        anchor, residual = zip(*parts, strict=True)
        return torch.cat(anchor).sum(), torch.cat(residual).sum()

    @staticmethod
    @once_differentiable
    def backward(ctx, anchor_grad, residual_grad):
        logits, anchors, scores = ctx.saved_tensors
        gradient = torch.empty_like(logits)
        for start in range(0, len(logits), ctx.rows):
            part = slice(start, start + ctx.rows)
            with torch.enable_grad():
                z = logits[part].detach().requires_grad_()
                a, r = _actd_position_losses(z, anchors[part], scores[part], ctx.residual_weight)
                gradient[part] = torch.autograd.grad((a.sum(), r.sum()), z, (anchor_grad, residual_grad))[0]
        return gradient, None, None, None, None


def actd_components(logits, anchors, scores, *, residual_weight, rows):
    """Compute the two ACTD sums consumed by the existing assistant loss."""
    if len(logits) <= rows:
        return original_actd_sums(logits, anchors, scores, residual_weight=residual_weight)
    anchor, residual = _AnchorResidual.apply(logits, anchors, scores, residual_weight, rows)
    return dict(anchor_sum=anchor, residual_sum=residual)
