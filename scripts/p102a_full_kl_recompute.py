"""Replay the native FP32 KL derivatives with bounded normalization buffers."""

import math

import torch
import torch.nn.functional as F
from torch.autograd.function import once_differentiable


def _kl(student, teacher, temperature, reduction):
    log_student = F.log_softmax(student.float() / temperature, dim=-1)
    prob_teacher = F.softmax(teacher.float() / temperature, dim=-1)
    return F.kl_div(log_student, prob_teacher, reduction=reduction)


class _RecomputeKL(torch.autograd.Function):
    @staticmethod
    def forward(ctx, student, teacher, temperature, rows):
        ctx.save_for_backward(student, teacher)
        ctx.temperature, ctx.rows = temperature, rows
        # Match the native batchmean's single reduction over the full FP32 layout.
        terms = student.new_empty(student.shape, dtype=torch.float32)
        with torch.autocast(student.device.type, enabled=False):
            for start in range(0, len(student), rows):
                part = slice(start, start + rows)
                terms[part] = _kl(student[part], teacher[part], temperature, 'none')
        return (terms.sum() / len(student)) * (temperature * temperature)

    @staticmethod
    @once_differentiable
    def backward(ctx, upstream):
        student, teacher = ctx.saved_tensors
        gradient = torch.empty_like(student)
        temperature = ctx.temperature
        with torch.enable_grad(), torch.autocast(student.device.type, enabled=False):
            for start in range(0, len(student), ctx.rows):
                part = slice(start, start + ctx.rows)
                block = student[part].detach().requires_grad_()
                value = (_kl(block, teacher[part], temperature, 'sum') / len(student)) * (
                    temperature * temperature)
                gradient[part] = torch.autograd.grad(value, block, upstream)[0]
        return gradient, None, None, None


def full_kl(student, teacher, *, temperature, rows):
    """Native batchmean KL with FP32 normalization and a fixed teacher."""
    if (student.ndim != 2 or student.shape != teacher.shape or min(student.shape) < 1
            or student.device != teacher.device or student.dtype not in (torch.float32, torch.bfloat16)
            or teacher.dtype not in (torch.float32, torch.bfloat16) or teacher.requires_grad
            or not math.isfinite(temperature) or temperature <= 0 or type(rows) is not int or rows < 1):
        raise ValueError('aligned 2D FP32/BF16 logits, frozen teacher and positive temperature/rows required')
    return _RecomputeKL.apply(student, teacher, temperature, rows)
