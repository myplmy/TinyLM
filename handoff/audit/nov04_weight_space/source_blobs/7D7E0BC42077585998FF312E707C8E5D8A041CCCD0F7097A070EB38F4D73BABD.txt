"""Explicit full-window attention visibility; the default model path is unchanged."""
from __future__ import annotations

import torch


def validate_visibility(mask, *, batch, length, device, require_nonempty=True):
    """SDPA boolean semantics: True permits a query to read a key."""
    if not isinstance(mask, torch.Tensor) or mask.dtype is not torch.bool:
        raise ValueError("attention_mask must be a boolean tensor (True=allowed)")
    if batch < 1 or length < 1 or tuple(mask.shape) != (batch, 1, length, length):
        raise ValueError("attention_mask requires exact positive [B,1,T,T] shape")
    if mask.device != device:
        raise ValueError("attention_mask and input must use the same device")
    if require_nonempty and not bool(mask.any(dim=-1).all()):
        raise ValueError("every attention query must have at least one allowed key")


def prepare_visibility(mask, tokens, cfg, schedule, *, mode_override=None,
                       return_aux=False, past_kv=None, use_cache=False,
                       logits_last_only=False, return_hidden=False,
                       return_mtp_hidden=False):
    """Validate and snapshot once; checkpoint recomputation cannot see caller edits.

    Opt-in is intentionally limited to fresh softmax-CLA sequential R1 forwards.
    It is not a cache, recursive scheduling, MTP, or production trainer feature.
    """
    if (getattr(cfg, "attn_kind", "softmax_cla") != "softmax_cla"
            or getattr(cfg, "n_modes", 1) != 1 or mode_override is not None
            or getattr(cfg, "mtp_aux", False)
            or getattr(cfg, "return_probs", False)
            or getattr(cfg, "reuse_attn_on_dup", False)
            or getattr(cfg, "repeat_embed_reinject", False)
            or list(schedule) != list(range(cfg.n_layers))):
        raise ValueError("explicit attention visibility requires softmax_cla, sequential R1, one mode, no MTP/probs/reuse")
    if (past_kv is not None or use_cache or logits_last_only or return_aux
            or return_hidden or return_mtp_hidden):
        raise ValueError("explicit attention visibility requires a fresh full logits forward without cache/aux/hidden")
    batch, length = tokens.shape
    validate_visibility(mask, batch=batch, length=length, device=tokens.device)
    return mask.detach().clone()
