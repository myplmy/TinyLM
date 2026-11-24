"""A row-recomputed FP32 sum CE with the original prediction IDs and GEMMs."""

import torch
import torch.nn.functional as F
from torch.autograd.function import once_differentiable


class _TargetHead(torch.autograd.Function):
    @staticmethod
    def forward(ctx, projected, table, labels, rows, collect_ids):
        e = table.to(projected.dtype)
        valid = labels.ne(-100)
        safe = labels.masked_fill(~valid, 0)
        selected = projected.new_empty((len(labels), 1), dtype=torch.float32)
        predictions = labels.new_empty((len(labels) if collect_ids else 0,))
        with torch.autocast(projected.device.type, enabled=False):
            for start in range(0, len(labels), rows):
                part = slice(start, start + rows)
                logits = F.linear(projected[part], e)
                if collect_ids:
                    predictions[part] = logits.argmax(1)
                logp = F.log_softmax(logits.float(), dim=1)
                selected[part] = logp.gather(1, safe[part, None])
            # Keep the native sum-reduction kernel and its row/ignore ordering.
            sum_loss = F.nll_loss(selected, torch.where(valid, 0, -100),
                                  ignore_index=-100, reduction='sum')
        ctx.save_for_backward(projected, e, safe, valid)
        ctx.rows, ctx.table_dtype = rows, table.dtype
        ctx.mark_non_differentiable(predictions)
        return sum_loss, predictions

    @staticmethod
    @once_differentiable
    def backward(ctx, upstream, _prediction_gradient):
        projected, table, safe, valid = ctx.saved_tensors
        delta = projected.new_empty((len(safe), len(table)))
        with torch.autocast(projected.device.type, enabled=False):
            for start in range(0, len(safe), ctx.rows):
                part = slice(start, start + ctx.rows)
                logp = F.log_softmax(F.linear(projected[part], table).float(), dim=1)
                dlogp = torch.zeros_like(logp)
                active = -upstream.float().expand(len(safe[part]), 1)
                dlogp.scatter_(1, safe[part, None], active.masked_fill(~valid[part, None], 0))
                block = torch.ops.aten._log_softmax_backward_data.default(dlogp, logp, 1, torch.float32)
                delta[part].copy_(block)
            dp = delta @ table if ctx.needs_input_grad[0] else None
            de = (delta.T @ projected).to(ctx.table_dtype) if ctx.needs_input_grad[1] else None
        return dp, de, None, None, None


def objective(model, hidden, targets, *, rows, collect_ids=True):
    """Return the P107 mean, exact supervised count, and optional winner IDs."""
    if (hidden.ndim != 3 or hidden.shape[:2] != targets.shape or targets.dtype != torch.long
            or hidden.device != targets.device or type(rows) is not int or rows < 1
            or type(collect_ids) is not bool or getattr(model, '_emb_fmt', None) is not None):
        raise ValueError('unpacked training head, aligned BTD/BT and positive row count required')
    count = int(targets.ne(-100).sum())
    if count == 0:
        raise ValueError('objective has zero supervised targets')
    table = model._emb_w()
    projected = F.linear(hidden, model._emb_up_w().t()) if model.emb_up is not None else hidden
    device = projected.device.type
    amp = torch.is_autocast_enabled(device)
    dtype = torch.get_autocast_dtype(device) if amp else projected.dtype
    if dtype not in (torch.float32, torch.bfloat16) or (not amp and dtype != table.dtype):
        raise ValueError('native FP32 or BF16-autocast operands required')
    total, predictions = _TargetHead.apply(projected.flatten(0, 1).to(dtype), table,
                                           targets.reshape(-1), rows, collect_ids)
    return total / count, count, predictions.reshape_as(targets) if collect_ids else None
