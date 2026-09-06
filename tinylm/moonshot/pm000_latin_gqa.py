"""PM000 pass-dependent Latin GQA core.

This module is deliberately torch-free and owns the complete experimental
algorithm: schedule construction, configuration validation, per-layer pass
tracking, and K/V shift selection.  The surrounding model files
contain only narrow integration hooks, which makes a later evidence-reviewed
transplant or full removal mechanical.

The default ``fixed`` path returns ``None`` as its runtime order so callers can
skip even the rotation helper and preserve the pre-PM tensor path.
"""
from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any


GQA_PASS_SCHEDULES = ("fixed", "latin", "random")
_U64_MASK = (1 << 64) - 1


def _mix_u64(value: int) -> int:
    """SplitMix64 finalizer used only as PM000's deterministic sort key."""
    z = (int(value) + 0x9E3779B97F4A7C15) & _U64_MASK
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _U64_MASK
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _U64_MASK
    return (z ^ (z >> 31)) & _U64_MASK


def gqa_pass_order(schedule: str, n_kv_heads: int, seed: int = 0) -> tuple[int, ...]:
    """Return one cycle of KV-head shifts without touching global RNG state.

    ``fixed`` has the identity-only cycle ``(0,)``.  Both non-fixed schedules
    are complete permutations that start at zero, preserving exact R1 identity.
    """
    if schedule not in GQA_PASS_SCHEDULES:
        raise ValueError(
            f"gqa_pass_schedule 은 {'|'.join(GQA_PASS_SCHEDULES)} — 받은 값: {schedule}"
        )
    n = int(n_kv_heads)
    if n < 1:
        raise ValueError(f"n_kv_heads 는 1 이상이어야 한다 — 받은 값: {n}")
    if schedule == "fixed":
        return (0,)
    if schedule == "latin":
        return tuple(range(n))

    seed64 = int(seed) & _U64_MASK
    tail = sorted(
        range(1, n),
        key=lambda shift: (
            _mix_u64(seed64 ^ ((shift * 0xD6E8FEB86659FD93) & _U64_MASK)),
            shift,
        ),
    )
    return (0, *tail)


def gqa_pass_validation_error(
    *,
    schedule: str,
    seed: int,
    n_q_heads: int,
    n_kv_heads: int,
    repeat_mode: str,
    reuse_attn_on_dup: bool,
) -> str | None:
    """Return a user-facing configuration error, or ``None`` when valid."""
    if schedule not in GQA_PASS_SCHEDULES:
        return f"gqa_pass_schedule 은 {'|'.join(GQA_PASS_SCHEDULES)} — 받은 값: {schedule}"
    if schedule != "random" and int(seed) != 0:
        return "gqa_pass_seed 는 random schedule 에서만 의미가 있다"
    if schedule == "fixed":
        return None
    if not (int(n_kv_heads) > 1 and int(n_q_heads) > int(n_kv_heads)):
        return "non-fixed gqa_pass_schedule 은 실제 GQA(n_q_heads > n_kv_heads > 1)에서만 쓴다"
    if repeat_mode != "uniform":
        return "PM000 non-fixed GQA pass schedule 은 repeat_mode=uniform 에서만 검증한다"
    if reuse_attn_on_dup:
        return "non-fixed GQA pass schedule 과 reuse_attn_on_dup 은 병용할 수 없다"
    return None


def gqa_pass_order_for_config(cfg: Any) -> tuple[int, ...] | None:
    """Build the runtime order; ``None`` is the exact fixed-path sentinel."""
    schedule = str(getattr(cfg, "gqa_pass_schedule", "fixed"))
    if schedule == "fixed":
        return None
    return gqa_pass_order(
        schedule,
        int(cfg.n_kv_heads),
        int(getattr(cfg, "gqa_pass_seed", 0)),
    )


def next_layer_pass_id(
    visits: MutableMapping[int, int] | None,
    layer_index: int,
) -> int:
    """Return and increment the actual layer's visit count.

    The mapping is intentionally keyed by the visited layer, never by its CLA
    KV owner.  ``None`` is the fixed-path sentinel and always returns zero.
    """
    if visits is None:
        return 0
    pass_id = visits.get(layer_index, 0)
    visits[layer_index] = pass_id + 1
    return pass_id


def gqa_pass_shift(order: tuple[int, ...], pass_id: int) -> int:
    """Select the KV-head shift for an actual layer visit."""
    return order[int(pass_id) % len(order)]


__all__ = [
    "GQA_PASS_SCHEDULES",
    "gqa_pass_order",
    "gqa_pass_order_for_config",
    "gqa_pass_shift",
    "gqa_pass_validation_error",
    "next_layer_pass_id",
]
