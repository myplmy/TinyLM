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


def _fixed_g4_r2(cfg, schedule):
    if ((cfg.n_prelude, cfg.n_middle, cfg.n_coda, cfg.mlp_group, cfg.cla_group) != (2, 12, 2, 4, 2)
            or not cfg.tie_mlp or cfg.mlp_split or cfg.train_repeat != 2.0 or cfg.infer_repeat != 1.0
            or cfg.repeat_mode != "uniform" or cfg.repeat_kv_reuse):
        return False
    middle = list(range(2, 14))
    return schedule == [0, 1, *middle, *middle, 14, 15]


def prepare_visibility(mask, tokens, cfg, schedule, *, mode_override=None,
                       return_aux=False, past_kv=None, use_cache=False,
                       logits_last_only=False, return_hidden=False,
                       return_mtp_hidden=False, allow_fixed_g4_r2=False):
    """Validate and snapshot once; checkpoint recomputation cannot see caller edits.

    Fresh softmax-CLA forwards support sequential R1. The document trainer can
    explicitly admit the fixed G4 R2 route.
    """
    if type(allow_fixed_g4_r2) is not bool:
        raise ValueError("allow_fixed_g4_r2 must be boolean")
    visits = list(schedule)
    supported = visits == list(range(cfg.n_layers)) or (allow_fixed_g4_r2 and _fixed_g4_r2(cfg, visits))
    if (getattr(cfg, "attn_kind", "softmax_cla") != "softmax_cla"
            or getattr(cfg, "n_modes", 1) != 1 or mode_override is not None
            or getattr(cfg, "mtp_aux", False)
            or getattr(cfg, "return_probs", False)
            or getattr(cfg, "reuse_attn_on_dup", False)
            or getattr(cfg, "repeat_embed_reinject", False) or not supported):
        raise ValueError("explicit attention visibility requires softmax_cla, a supported visit route, "
                         "one mode and no MTP/probs/reuse")
    if (past_kv is not None or use_cache or logits_last_only or return_aux
            or return_hidden or return_mtp_hidden):
        raise ValueError("explicit attention visibility requires a fresh full logits forward without cache/aux/hidden")
    batch, length = tokens.shape
    validate_visibility(mask, batch=batch, length=length, device=tokens.device)
    return mask.detach().clone()
