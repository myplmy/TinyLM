"""Stage-0 primitives for P091 adaptive late refinement.

These helpers do not alter the trainer or model default path.  They establish
the unique-parameter candidate and foldable latent-expansion contracts that a
later, separately gated controller may use.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, TypeVar

import torch


T = TypeVar("T")


@dataclass(frozen=True)
class LateRefineConfig:
    enabled: bool = False
    rank: int = 128
    scale: float = 0.0


def unique_parameter_blocks(blocks: Iterable[T]) -> list[T]:
    """Deduplicate tied physical uses by module identity, preserving first-use order."""
    seen: set[int] = set()
    unique: list[T] = []
    for block in blocks:
        key = id(block)
        if key not in seen:
            seen.add(key)
            unique.append(block)
    return unique


def expanded_latent_weight(weight, down=None, up=None, *, scale: float = 0.0):
    """Return ``W + scale * (down @ up)`` before ternary quantization."""
    if down is None and up is None:
        return weight
    if down is None or up is None:
        raise ValueError("down and up must be supplied together")
    if down.ndim != 2 or up.ndim != 2 or weight.ndim != 2:
        raise ValueError("weight/down/up must all be matrices")
    if down.shape[0] != weight.shape[0] or up.shape[1] != weight.shape[1]:
        raise ValueError(
            f"expansion outer shape mismatch: W={tuple(weight.shape)} "
            f"down={tuple(down.shape)} up={tuple(up.shape)}"
        )
    if down.shape[1] != up.shape[0]:
        raise ValueError(f"rank mismatch: {down.shape[1]} != {up.shape[0]}")
    return weight + float(scale) * (down @ up)


@torch.no_grad()
def fold_expansion_(weight, down, up, *, scale: float) -> None:
    """Fold the training-only expansion into W so inference shape is unchanged."""
    effective = expanded_latent_weight(weight, down, up, scale=scale)
    weight.copy_(effective)
