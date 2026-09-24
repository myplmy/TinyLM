"""P103A X3 restricted frozen-prefix/tail path for fixed causal windows.

This is an opt-in model gate, not a 2M/20M cache builder or a default trainer path.
The caller must pin the checkpoint and freeze every parameter on the lower side.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F


def validate_frozen_split(model, split_layer: int) -> None:
    cfg = model.cfg
    if (not isinstance(split_layer, int) or not 1 <= split_layer < cfg.n_layers
            or cfg.tie_mlp or cfg.n_modes != 1 or cfg.attn_group != 1
            or cfg.grad_checkpoint or cfg.use_ternary_kernel
            or cfg.train_repeat != 1.0 or cfg.infer_repeat != 1.0
            or cfg.repeat_embed_reinject or cfg.reuse_attn_on_dup
            or cfg.mlp_lora_rank or cfg.mlp_film or cfg.mlp_lrm
            or getattr(cfg, "x2_active_tiles", ())
            or getattr(model, "_unpack_cache", False)
            or getattr(model, "_quant_frozen", False)
            or getattr(model, "_arena", None) is not None
            or getattr(model, "_emb_fmt", None) not in (None, "bf16", "fp16")):
        raise ValueError("X3 frozen split requires non-repeating dense causal baseline")
    if model.owner[split_layer] != split_layer or any(
            model.owner[i] < split_layer for i in range(split_layer, cfg.n_layers)):
        raise ValueError("X3 split crosses a CLA owner/consumer group")
    if any(p.requires_grad for p in model.emb.parameters()):
        raise ValueError("X3 shared input/output embedding must be frozen")
    if model.emb_up is not None and any(p.requires_grad for p in model.emb_up.parameters()):
        raise ValueError("X3 shared factorized head must be frozen")
    if any(p.requires_grad for layer in model.layers[:split_layer] for p in layer.parameters()):
        raise ValueError("X3 lower layers must be frozen before caching")


def _visit(model, x, start: int, stop: int, cos, sin):
    kv_bank = {}
    for i in range(start, stop):
        layer = model.layers[i]
        owner = model.owner[i]
        if owner == i:
            kv_bank[owner] = layer.attn_mod.compute_kv(x, cos, sin)
        elif owner not in kv_bank:
            raise RuntimeError("X3 CLA owner is outside this fixed-window segment")
        x = layer(x, kv_bank[owner], cos, sin, None)
    return x


def frozen_prefix_boundary(model, tokens: torch.Tensor, split_layer: int) -> torch.Tensor:
    """Return detached hidden after the complete lower CLA group, position 0..S-1."""
    validate_frozen_split(model, split_layer)
    if tokens.ndim != 2 or tokens.dtype != torch.long or not 1 < tokens.shape[1] <= model.cfg.max_seq_len:
        raise ValueError("X3 requires a full [batch,seq] fixed causal window")
    with torch.no_grad():
        model.refresh_quant()
        x = F.embedding(tokens, model._emb_w())
        if model.emb_up is not None:
            x = F.linear(x, model._emb_up_w())
        cos, sin = model.rope_cos[:tokens.shape[1]], model.rope_sin[:tokens.shape[1]]
        return _visit(model, x, 0, split_layer, cos, sin).detach()


def tail_logits_from_boundary(model, boundary: torch.Tensor, split_layer: int) -> torch.Tensor:
    """Train only the upper complete CLA groups and final norm with frozen head."""
    validate_frozen_split(model, split_layer)
    if (boundary.ndim != 3 or boundary.shape[-1] != model.cfg.dim
            or not 1 < boundary.shape[1] <= model.cfg.max_seq_len
            or boundary.requires_grad):
        raise ValueError("X3 boundary shape or gradient provenance differs")
    model.refresh_quant()
    cos, sin = model.rope_cos[:boundary.shape[1]], model.rope_sin[:boundary.shape[1]]
    x = _visit(model, boundary, split_layer, model.cfg.n_layers, cos, sin)
    x = model.norm_f(x) * model.norm_f_scale
    return model._head_logits(x)
