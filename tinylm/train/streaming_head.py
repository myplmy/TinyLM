"""Opt-in vocabulary-tiled target NLL; a PyTorch prototype, not a fused kernel.

No default trainer or model route changes. The caller owns next-token shift,
assistant masks and whole-update normalization. First derivatives only.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F
from torch.autograd.function import once_differentiable


class _VocabNLL(torch.autograd.Function):
    @staticmethod
    def forward(ctx, projected, table, labels, tile):
        if (projected.ndim != 2 or table.ndim != 2
                or projected.shape[1] != table.shape[1] or table.shape[0] < 1
                or labels.ndim != 1 or labels.shape[0] != projected.shape[0]
                or labels.dtype != torch.long or type(tile) is not int or tile < 1
                or projected.device != table.device or projected.device != labels.device
                or projected.dtype not in (torch.float32, torch.float64, torch.bfloat16)
                or table.dtype not in (torch.float32, torch.float64, torch.bfloat16)):
            raise ValueError("aligned matrices, valid labels and positive integer tile required")
        if labels.numel() and (int(labels.min()) < 0 or int(labels.max()) >= table.shape[0]):
            raise ValueError("valid vocabulary labels required; masking belongs to caller")
        device = projected.device.type
        enabled = torch.is_autocast_enabled(device)
        compute_dtype = torch.get_autocast_dtype(device) if enabled else projected.dtype
        if not enabled and projected.dtype != table.dtype:
            raise ValueError("without autocast both matrix dtypes must match")
        if compute_dtype not in (torch.float32, torch.float64, torch.bfloat16):
            raise ValueError("only FP32/FP64/BF16 calculation is registered")
        # Match the original matmul's operand casts. Accumulate log probabilities
        # in FP32 (FP64 only for the explicitly FP64 CPU mathematical fixture).
        p, e = projected.to(compute_dtype), table.to(compute_dtype)
        loss_dtype = torch.float64 if compute_dtype == torch.float64 else torch.float32
        maximum = torch.full((p.shape[0],), -torch.inf, device=p.device, dtype=loss_dtype)
        partition = torch.zeros_like(maximum)
        chosen = torch.zeros_like(maximum)
        with torch.autocast(device_type=device, enabled=False):
            for start in range(0, e.shape[0], tile):
                end = min(start + tile, e.shape[0])
                logits = F.linear(p, e[start:end]).to(loss_dtype)
                next_max = torch.maximum(maximum, logits.max(dim=-1).values)
                partition = partition * torch.exp(maximum-next_max) + torch.exp(logits-next_max[:,None]).sum(dim=-1)
                maximum = next_max
                indices = (labels >= start) & (labels < end)
                if bool(indices.any()):
                    chosen[indices] = logits[indices, labels[indices] - start]
        ctx.save_for_backward(projected, table, labels, maximum, partition)
        ctx.tile, ctx.compute_dtype, ctx.loss_dtype = tile, compute_dtype, loss_dtype
        # Avoid subtracting two huge rounded absolute LSE/target values.
        return (maximum-chosen) + torch.log(partition)

    @staticmethod
    @once_differentiable
    def backward(ctx, outer):
        projected, table, labels, maximum, partition = ctx.saved_tensors
        device = projected.device.type
        p, e = projected.to(ctx.compute_dtype), table.to(ctx.compute_dtype)
        # A single final cast, rather than rounded partial BF16 sums, preserves
        # the intended full-vocabulary reduction as closely as tiled GEMMs allow.
        dp = torch.zeros_like(p, dtype=ctx.loss_dtype) if ctx.needs_input_grad[0] else None
        de = torch.zeros_like(table) if ctx.needs_input_grad[1] else None
        with torch.autocast(device_type=device, enabled=False):
            for start in range(0, e.shape[0], ctx.tile):
                end = min(start + ctx.tile, e.shape[0])
                part = e[start:end]
                logits = F.linear(p, part).to(ctx.loss_dtype)
                delta = (torch.exp(logits-maximum[:,None]) / partition[:,None]) * outer.to(ctx.loss_dtype)[:,None]
                indices = (labels >= start) & (labels < end)
                if bool(indices.any()):
                    delta[indices, labels[indices] - start] -= outer.to(ctx.loss_dtype)[indices]
                # Native linear backward first receives the logits-dtype gradient.
                delta = delta.to(ctx.compute_dtype)
                if dp is not None:
                    dp.add_(delta.to(ctx.loss_dtype) @ part.to(ctx.loss_dtype))
                if de is not None:
                    de[start:end] = (delta.T @ p).to(table.dtype)
        return (None if dp is None else dp.to(projected.dtype)), de, None, None


def vocab_nll(projected, table, labels, *, tile=4096):
    """Per-target NLL with arbitrary signed upstream derivatives; no reduction."""
    return _VocabNLL.apply(projected, table, labels, tile)


def target_nll(model, hidden, targets, *, chunk=64, tile=4096):
    """Match ALM's valid-position/zero-mask contract for an FP32 tied table.

    This path deliberately refuses storage-quantized embeddings and auxiliary
    heads; existing accessors own the tied input/output table and projection.
    """
    if (hidden.ndim != 3 or tuple(hidden.shape[:2]) != tuple(targets.shape)
            or targets.dtype != torch.long or hidden.device != targets.device
            or type(chunk) is not int or chunk < 1 or type(tile) is not int or tile < 1):
        raise ValueError("hidden BTD, shifted long BT targets and positive chunks required")
    if getattr(model, "_emb_fmt", None) is not None:
        raise ValueError("storage-quantized table is outside the registered prototype")
    table = model._emb_w()
    if table.dtype != torch.float32:
        raise ValueError("registered model path requires the original FP32 tied table")
    valid = targets.ne(-100)
    positions = valid.reshape(-1).nonzero(as_tuple=True)[0]
    flat = hidden[..., 0].reshape(-1).float() * 0.
    if positions.numel() == 0:
        return flat.reshape_as(targets), valid
    features = hidden.reshape(-1, hidden.shape[-1]).index_select(0, positions)
    labels = targets.reshape(-1).index_select(0, positions)
    blocks = []
    for start in range(0, positions.numel(), chunk):
        h = features[start:start + chunk]
        projected = F.linear(h, model._emb_up_w().t()) if model.emb_up is not None else h
        blocks.append(vocab_nll(projected, table, labels[start:start + chunk], tile=tile))
    return flat.scatter(0, positions, torch.cat(blocks)).reshape_as(targets), valid
