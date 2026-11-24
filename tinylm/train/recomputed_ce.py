"""Position-blocked NLL with the native full-shape linear backward."""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch.autograd.function import once_differentiable


IGNORE_INDEX = -100


class _RecomputedNLL(torch.autograd.Function):
    @staticmethod
    def forward(ctx, projected, table, targets, rows):
        device = projected.device.type
        e = table.to(projected.dtype)
        valid = targets.ne(IGNORE_INDEX)
        labels = targets.masked_fill(~valid, 0)
        nll = projected.new_empty((len(labels),), dtype=torch.float32)
        with torch.autocast(device, enabled=False):
            for start in range(0, len(labels), rows):
                part = slice(start, start + rows)
                logp = F.log_softmax(F.linear(projected[part], e), dim=1)
                nll[part] = -logp.gather(1, labels[part, None]).flatten().float()
        ctx.save_for_backward(projected, e, labels, valid)
        ctx.rows, ctx.table_dtype = rows, table.dtype
        return nll.masked_fill_(~valid, 0)

    @staticmethod
    @once_differentiable
    def backward(ctx, upstream):
        projected, table, labels, valid = ctx.saved_tensors
        delta = projected.new_empty((len(labels), len(table)))
        upstream = upstream.to(projected.dtype).masked_fill(~valid, 0)
        with torch.autocast(projected.device.type, enabled=False):
            for start in range(0, len(labels), ctx.rows):
                part = slice(start, start + ctx.rows)
                logp = F.log_softmax(F.linear(projected[part], table), dim=1)
                dlogp = torch.zeros_like(logp)
                dlogp.scatter_(1, labels[part, None], -upstream[part, None])
                block = torch.ops.aten._log_softmax_backward_data.default(dlogp, logp, 1, logp.dtype)
                delta[part].copy_(block.masked_fill_(~valid[part, None], 0))
            # Retain masked rows so both GEMMs have the original shape and reduction.
            dp = delta @ table if ctx.needs_input_grad[0] else None
            de = (delta.T @ projected).to(ctx.table_dtype) if ctx.needs_input_grad[1] else None
        return dp, de, None, None


def target_nll(model, hidden, targets, *, rows):
    """Return differentiable per-position NLL and the mask for shifted targets."""
    if (hidden.ndim != 3 or tuple(hidden.shape[:2]) != tuple(targets.shape)
            or targets.dtype != torch.long or hidden.device != targets.device
            or type(rows) is not int or rows < 1):
        raise ValueError("recomputed CE requires hidden BTD, shifted long BT targets and positive rows")
    if getattr(model, "_emb_fmt", None) is not None:
        raise ValueError("recomputed CE requires the original training embedding table")
    table = model._emb_w()
    projected = F.linear(hidden, model._emb_up_w().t()) if model.emb_up is not None else hidden
    device = projected.device.type
    amp = torch.is_autocast_enabled(device)
    dtype = torch.get_autocast_dtype(device) if amp else projected.dtype
    if dtype not in (torch.bfloat16, torch.float32) or (not amp and dtype != table.dtype):
        raise ValueError("recomputed CE requires matching FP32 operands or BF16 autocast")
    flat = projected.flatten(0, 1).to(dtype)
    nll = _RecomputedNLL.apply(flat, table, targets.reshape(-1), rows)
    return nll.reshape_as(targets), targets.ne(IGNORE_INDEX)
