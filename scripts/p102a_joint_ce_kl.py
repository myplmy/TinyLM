"""Compute CE and full-distribution KL without materializing all student logits."""

import math

import torch
import torch.nn.functional as F
from torch.autograd.function import once_differentiable

from scripts.p102a_full_kl_recompute import _kl


def _ce_logp(block, fp32=False):
    # The admitted CUDA CE rounds log probabilities to BF16 before FP32 NLL.
    operands = block if not fp32 and block.is_cuda and block.dtype == torch.bfloat16 else block.float()
    return F.log_softmax(operands, dim=1).float()


class _JointHead(torch.autograd.Function):
    @staticmethod
    def forward(ctx, projected, table, labels, teacher, temperature, rows, full_sum, fp32_ce):
        device = projected.device.type
        e = table.to(projected.dtype)
        valid = labels.ne(-100)
        safe = labels.masked_fill(~valid, 0)
        selected = projected.new_empty((len(labels), 1), dtype=torch.float32)
        full_terms = projected.new_empty(teacher.shape, dtype=torch.float32) if full_sum else None
        async_copy = teacher.device.type == 'cpu' and teacher.is_pinned()
        kl_sum = None
        with torch.autocast(device, enabled=False):
            for start in range(0, len(labels), rows):
                part = slice(start, start + rows)
                block = F.linear(projected[part], e)
                selected[part] = _ce_logp(block, fp32_ce).gather(1, safe[part, None])
                teacher_block = teacher[part].to(projected.device, non_blocking=async_copy)
                if full_sum:
                    full_terms[part] = _kl(block, teacher_block, temperature, 'none')
                else:
                    partial_sum = _kl(block, teacher_block, temperature, 'sum')
                    kl_sum = partial_sum if kl_sum is None else kl_sum + partial_sum
                del teacher_block
            ce = F.nll_loss(selected, torch.where(valid, 0, -100), reduction='mean')
            if full_sum:
                kl_sum = full_terms.sum()
        ctx.save_for_backward(projected, e, labels, teacher)
        ctx.temperature, ctx.rows, ctx.table_dtype = temperature, rows, table.dtype
        ctx.async_copy = async_copy
        ctx.ce_denom = max(1, int(valid.sum()))
        ctx.fp32_ce = fp32_ce
        return ce, (kl_sum / len(labels)) * (temperature * temperature)

    @staticmethod
    @once_differentiable
    def backward(ctx, grad_ce, grad_kl):
        projected, table, labels, teacher = ctx.saved_tensors
        delta = projected.new_empty((len(labels), len(table)))
        temperature = ctx.temperature
        with torch.autocast(projected.device.type, enabled=False):
            for start in range(0, len(labels), ctx.rows):
                part = slice(start, start + ctx.rows)
                block = F.linear(projected[part], table)
                with torch.enable_grad():
                    block = block.detach().requires_grad_()
                    ce = F.nll_loss(_ce_logp(block, ctx.fp32_ce), labels[part], reduction='sum') / ctx.ce_denom
                    teacher_block = teacher[part].to(projected.device, non_blocking=ctx.async_copy)
                    kl = (_kl(block, teacher_block, temperature, 'sum') / len(labels)) * (temperature * temperature)
                    # Leave both FP32 losses' backward casts and their BF16 merge to autograd.
                    delta[part] = torch.autograd.grad((ce, kl), block, (grad_ce, grad_kl))[0]
                    del teacher_block
            # Preserve the shape and summation of the native tied-head linear backward.
            grad_hidden = delta @ table if ctx.needs_input_grad[0] else None
            grad_table = (delta.T @ projected).to(ctx.table_dtype) if ctx.needs_input_grad[1] else None
        return grad_hidden, grad_table, None, None, None, None, None, None


def joint_ce_kl(model, hidden, labels, teacher, *, temperature, rows, full_sum,
                assigned_rows=None, fp32_ce=False):
    """Compute CE/KL with frozen teacher rows on the compute device or on CPU."""
    if (hidden.ndim != 3 or hidden.shape[:2] != labels.shape or not labels.numel()
            or labels.dtype != torch.long or hidden.device != labels.device
            or type(rows) is not int or rows < 1 or type(full_sum) is not bool or type(fp32_ce) is not bool
            or not math.isfinite(temperature) or temperature <= 0 or getattr(model, '_emb_fmt', None) is not None):
        raise ValueError('unpacked head, shifted BT targets and positive rows/temperature required')
    table = model._emb_w()
    if assigned_rows is not None:
        if type(assigned_rows) is not int or not 0 < assigned_rows <= len(table):
            raise ValueError('assigned output rows must fit within the shared embedding')
        table = table[:assigned_rows]
    host_teacher = hidden.is_cuda and teacher.device.type == 'cpu'
    if (teacher.shape != (labels.numel(), len(table)) or teacher.dtype not in (torch.float32, torch.bfloat16)
            or (teacher.device != hidden.device and not host_teacher) or teacher.requires_grad):
        raise ValueError('aligned detached 2D FP32/BF16 teacher logits required')
    projected = F.linear(hidden, model._emb_up_w().t()) if model.emb_up is not None else hidden
    device = projected.device.type
    amp = torch.is_autocast_enabled(device)
    dtype = torch.get_autocast_dtype(device) if amp else projected.dtype
    if dtype not in (torch.float32, torch.bfloat16) or (not amp and dtype != table.dtype):
        raise ValueError('FP32 or BF16 native head computation required')
    return _JointHead.apply(projected.flatten(0, 1).to(dtype), table, labels.reshape(-1), teacher,
                            temperature, rows, full_sum, fp32_ce)
