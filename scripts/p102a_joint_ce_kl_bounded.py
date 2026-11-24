"""Experimental CE/KL backward with a bounded position buffer."""

import torch
import torch.nn.functional as F
from torch.autograd.function import once_differentiable

from scripts.p102a_joint_ce_kl import _JointHead, _ce_logp, _kl


VJP_ROWS = 512


class BoundedJointHead(_JointHead):
    """Keep the established loss and restrict the logits-gradient workspace.

    The table gradient's reduction over positions is grouped differently.
    Preserve FP32 accumulation and the original final autocast rounding.
    """

    @staticmethod
    @once_differentiable
    def backward(ctx, grad_ce, grad_kl):
        projected, table, labels, teacher = ctx.saved_tensors
        rows, temperature = ctx.rows, ctx.temperature
        # Align workspace boundaries with the existing loss tiles.
        window = max(1, VJP_ROWS // rows) * rows
        delta = projected.new_empty((min(window, len(labels)), len(table)))
        grad_hidden = torch.empty_like(projected) if ctx.needs_input_grad[0] else None
        table_accum = torch.zeros_like(table, dtype=torch.float32) if ctx.needs_input_grad[1] else None
        with torch.autocast(projected.device.type, enabled=False):
            for start in range(0, len(labels), window):
                stop = min(start + window, len(labels))
                for lo in range(start, stop, rows):
                    hi = min(lo + rows, stop)
                    part = slice(lo, hi)
                    block = F.linear(projected[part], table)
                    with torch.enable_grad():
                        block = block.detach().requires_grad_()
                        ce = F.nll_loss(_ce_logp(block, ctx.fp32_ce), labels[part], reduction="sum") / ctx.ce_denom
                        t = teacher[part].to(projected.device, non_blocking=ctx.async_copy)
                        kl = (_kl(block, t, temperature, "sum") / len(labels)) * (temperature * temperature)
                        local = torch.autograd.grad((ce, kl), block, (grad_ce, grad_kl))[0]
                    delta[lo-start:hi-start].copy_(local)
                    del block, ce, kl, t, local
                block_delta = delta[:stop-start]
                block_projection = projected[start:stop]
                if grad_hidden is not None:
                    grad_hidden[start:stop].copy_(block_delta @ table)
                if table_accum is not None:
                    if projected.is_cuda and projected.dtype == torch.bfloat16:
                        table_accum.add_(torch.mm(block_delta.T, block_projection, out_dtype=torch.float32))
                    else:
                        table_accum.addmm_(block_delta.T.float(), block_projection.float())
        table_grad = table_accum.to(projected.dtype).to(ctx.table_dtype) if table_accum is not None else None
        return grad_hidden, table_grad, None, None, None, None, None, None
