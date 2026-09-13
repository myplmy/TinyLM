"""Pure mapping helpers for parent-to-student parameter transplantation."""
from __future__ import annotations

from collections.abc import Sequence


_KV_PARAMETER_ROOTS = frozenset({"k_proj", "v_proj", "k_norm"})


def teacher_attention_source_index(
    owner: Sequence[int],
    mapped_layer: int,
    parameter_name: str,
) -> int:
    """Return the teacher layer that physically owns an attention parameter.

    Q/O and Q-norm are layer-local. K/V and K-norm follow the teacher CLA owner
    map because reuse layers intentionally do not instantiate those parameters.
    """
    if not 0 <= mapped_layer < len(owner):
        raise IndexError(f"mapped teacher layer {mapped_layer} outside owner map of {len(owner)}")
    root = parameter_name.split(".", 1)[0]
    source = int(owner[mapped_layer]) if root in _KV_PARAMETER_ROOTS else mapped_layer
    if not 0 <= source < len(owner):
        raise IndexError(f"teacher owner {source} outside owner map of {len(owner)}")
    return source
