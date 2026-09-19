#!/usr/bin/env python3
"""CPU-only contracts for P076 parent-group aggregation."""
from __future__ import annotations

import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tinylm.train.init_utils import _aggregate_group_tensors


def main() -> int:
    values = [
        torch.tensor([[1.0, 2.0], [3.0, 4.0]]),
        torch.tensor([[2.0, 0.0], [4.0, 2.0]]),
        torch.tensor([[5.0, 1.0], [0.0, 3.0]]),
        torch.tensor([[4.0, 3.0], [2.0, 1.0]]),
    ]
    legacy = sum(values) / len(values)
    actual_mean = _aggregate_group_tensors(values, "mean")
    assert torch.equal(actual_mean, legacy), "default mean must preserve legacy arithmetic"
    assert _aggregate_group_tensors(values, "middle") is values[2]

    restored = _aggregate_group_tensors(values, "norm_mean")
    target = sum(float(value.norm()) for value in values) / len(values)
    assert abs(float(restored.norm()) - target) < 1e-5
    cosine = torch.nn.functional.cosine_similarity(
        restored.flatten(), legacy.flatten(), dim=0
    )
    assert float(cosine) > 0.999999

    try:
        _aggregate_group_tensors([torch.ones(2), -torch.ones(2)], "norm_mean")
    except RuntimeError as exc:
        assert "exactly cancelled" in str(exc)
    else:
        raise AssertionError("exact cancellation was silently accepted")
    try:
        _aggregate_group_tensors(values, "unknown")
    except ValueError as exc:
        assert "unsupported group_init" in str(exc)
    else:
        raise AssertionError("unknown group_init was accepted")

    print("[PASS] P076 group init: legacy mean, middle, norm restoration, fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
