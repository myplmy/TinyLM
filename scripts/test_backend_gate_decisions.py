#!/usr/bin/env python3
"""CPU-only decision regressions for P025B/P060B diagnostic gates."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch

from scripts.diag_sdpa_wsl_gqa import _eligible
from scripts.diag_sparse24_inference_attribution import _agreement_ok, _error_stats


def main() -> int:
    reference = torch.linspace(-50.0, 50.0, 2048).reshape(32, 64)
    # Wide-GEMM-like aggregate agreement: a few near-zero values can violate
    # elementwise atol while normalized RMS remains safely below 1e-3.
    actual = reference.clone()
    actual[15, 63] += 0.03
    metrics = _error_stats(torch, actual, reference)
    assert not metrics["legacy_close"]
    assert _agreement_ok(
        metrics, max_nrms=1e-3, max_abs_ratio=1e-2, min_cosine=0.999999
    )
    bad = reference + 1.0
    assert not _agreement_ok(
        _error_stats(torch, bad, reference), max_nrms=1e-3,
        max_abs_ratio=1e-2, min_cosine=0.999999
    )

    rows = {
        "off_default": (1.0, 100.0, 0.0, 0.0),
        "on_default": (1.003, 62.8, 0.0, 0.0),
        "on_cudnn": (1.079, 62.0, 0.0, 0.0),
    }
    assert [x[0] for x in _eligible(rows, "off_default", ("on_default",), 1.05, 0.10)] == ["on_default"]
    assert not _eligible(rows, "off_default", ("on_cudnn",), 1.05, 0.10)
    print("[PASS] backend gate decisions: scale-aware sparse agreement and default GQA candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
