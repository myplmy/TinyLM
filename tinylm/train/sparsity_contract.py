"""Shared, framework-free accounting for P025B/P092 sparsity experiments.

The contract deliberately separates structural mask sparsity, ternary zeros
inside active connections, and effective zeros.  It is safe to import from
static tests without importing torch or loading a model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class SparsitySnapshot:
    total: int
    active: int
    active_nonzero: int

    @property
    def mask_sparsity(self) -> float:
        return 1.0 - self.active / self.total

    @property
    def ternary_zero_rate(self) -> float:
        return 0.0 if self.active == 0 else 1.0 - self.active_nonzero / self.active

    @property
    def effective_sparsity(self) -> float:
        return 1.0 - self.active_nonzero / self.total


@dataclass(frozen=True)
class TopologyTransition:
    total: int
    births: int
    deaths: int
    stayed_active: int

    @property
    def turnover(self) -> float:
        return (self.births + self.deaths) / self.total

    @property
    def conserves_active_count(self) -> bool:
        return self.births == self.deaths


def _bits(values: Iterable[object], *, name: str) -> tuple[bool, ...]:
    out = tuple(bool(value) for value in values)
    if not out:
        raise ValueError(f"{name} must not be empty")
    return out


def sparsity_snapshot(mask: Iterable[object], ternary_codes: Iterable[object]) -> SparsitySnapshot:
    """Measure mask, active-code zeros, and effective sparsity separately."""
    mask_bits = _bits(mask, name="mask")
    codes = tuple(ternary_codes)
    if len(mask_bits) != len(codes):
        raise ValueError(f"mask/code length mismatch: {len(mask_bits)} != {len(codes)}")
    active = sum(mask_bits)
    active_nonzero = sum(1 for keep, code in zip(mask_bits, codes) if keep and code != 0)
    return SparsitySnapshot(len(mask_bits), active, active_nonzero)


def topology_transition(previous: Iterable[object], current: Iterable[object]) -> TopologyTransition:
    """Count births/deaths without conflating them with ternary sign changes."""
    before = _bits(previous, name="previous mask")
    after = _bits(current, name="current mask")
    if len(before) != len(after):
        raise ValueError(f"mask length mismatch: {len(before)} != {len(after)}")
    births = sum((not old) and new for old, new in zip(before, after))
    deaths = sum(old and (not new) for old, new in zip(before, after))
    stayed = sum(old and new for old, new in zip(before, after))
    return TopologyTransition(len(before), births, deaths, stayed)


def validate_nm(mask: Sequence[object], n: int, m: int) -> None:
    """Raise unless every consecutive block of ``m`` contains exactly ``n`` active entries."""
    if not (0 < n < m):
        raise ValueError(f"N:M requires 0 < N < M, got {n}:{m}")
    if not mask or len(mask) % m:
        raise ValueError(f"mask length {len(mask)} is not a positive multiple of M={m}")
    for offset in range(0, len(mask), m):
        count = sum(bool(value) for value in mask[offset:offset + m])
        if count != n:
            raise ValueError(f"block {offset // m} violates {n}:{m}: active={count}")
