"""Diagnostic BF16 tied head that reuses one row-logit buffer for its VJP."""

import torch
from torch.autograd.function import once_differentiable
from torch.nn import functional as F
import triton
import triton.language as tl

from tinylm.train.recomputed_ce import IGNORE_INDEX


@triton.jit
def log_nll(buffer, labels, out, vocab: tl.constexpr, width: tl.constexpr, preserve: tl.constexpr):
    row = tl.program_id(0)
    col = tl.arange(0, width)
    index = row * vocab + col
    target = tl.load(labels + row)
    logits = tl.load(buffer + index, col < vocab, other=float("-inf")).to(tl.float32)
    shift = logits - tl.max(logits, 0)
    logp = (shift - tl.log(tl.sum(tl.exp(shift), 0))).to(buffer.dtype.element_ty)
    loss = -tl.sum(tl.where(col == target, logp.to(tl.float32), 0.0), 0)
    tl.store(out + row, loss)
    if preserve:
        tl.store(buffer + index, logp, col < vocab)


@triton.jit
def log_nll_vjp(buffer, labels, upstream, vocab: tl.constexpr, width: tl.constexpr, recompute: tl.constexpr):
    row = tl.program_id(0)
    col = tl.arange(0, width)
    index = row * vocab + col
    target = tl.load(labels + row)
    scale = tl.load(upstream + row).to(buffer.dtype.element_ty).to(tl.float32)
    values = tl.load(buffer + index, col < vocab, other=float("-inf")).to(tl.float32)
    if recompute:
        shift = values - tl.max(values, 0)
        values = (shift - tl.log(tl.sum(tl.exp(shift), 0))).to(buffer.dtype.element_ty).to(tl.float32)
    gradient = tl.where(target < 0, 0.0, (tl.exp(values) - (col == target).to(tl.float32)) * scale)
    tl.store(buffer + index, gradient, col < vocab)


class RowLoss(torch.autograd.Function):
    @staticmethod
    def forward(ctx, projected, table, labels, retain):
        logits = F.linear(projected, table)
        losses = projected.new_empty(len(labels), dtype=torch.float32)
        vocab = len(table)
        log_nll[(len(labels),)](logits, labels, losses, vocab, triton.next_power_of_2(vocab), retain,
                                 num_warps=16, enable_fp_fusion=False)
        ctx.save_for_backward(projected, table, labels, logits if retain else None)
        ctx.consumed = False
        return losses

    @staticmethod
    @once_differentiable
    def backward(ctx, upstream):
        if ctx.consumed:
            raise RuntimeError("the diagnostic head buffer has already been consumed")
        ctx.consumed = True
        projected, table, labels, logp = ctx.saved_tensors
        vocab = len(table)
        with torch.autocast("cuda", enabled=False):
            delta = F.linear(projected, table) if logp is None else logp
            log_nll_vjp[(len(labels),)](delta, labels, upstream.contiguous(), vocab,
                                       triton.next_power_of_2(vocab), logp is None,
                                       num_warps=16, enable_fp_fusion=False)
            dp = delta @ table if ctx.needs_input_grad[0] else None
            de = delta.T @ projected if ctx.needs_input_grad[1] else None
        return dp, de, None, None


def target_nll(model, hidden, targets, *, retain=True):
    """Project GPT's tied table, then compute per-position BF16 NLL and mask."""
    if (hidden.device.type != "cuda" or not torch.is_autocast_enabled("cuda")
            or torch.get_autocast_dtype("cuda") != torch.bfloat16
            or targets.shape != hidden.shape[:2] or targets.dtype != torch.long
            or targets.device != hidden.device or getattr(model, "_emb_fmt", None) is not None):
        raise ValueError("the diagnostic head requires original tied weights under CUDA BF16 autocast")
    hidden = F.linear(hidden, model._emb_up_w().t()) if model.emb_up is not None else hidden
    table = model._emb_w().to(torch.bfloat16)
    flat = hidden.flatten(0, 1).to(torch.bfloat16)
    with torch.autocast("cuda", enabled=False):
        values = RowLoss.apply(flat, table, targets.reshape(-1), retain)
    return values.reshape_as(targets), targets.ne(IGNORE_INDEX)
