#!/usr/bin/env python3
"""CPU-only decision regressions for P025B/P060B diagnostic gates."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch

from scripts.diag_sdpa_wsl_gqa import (
    _captured_call,
    _eligible,
    _grouped_broadcast_inputs,
    _unique_storage_mib,
)
from scripts.diag_fp8_scaling_overhead import _gate_decision
from scripts.diag_fp8_path_attribution import _fp8_tensor_ledger
from scripts.diag_sharing_parent_approx import _approximation_gate
from scripts.diag_depth_init import _group_gate_exit
from scripts.diag_sparse24_inference_attribution import _agreement_ok, _error_stats
from scripts.diag_sparse24_path_attribution import _parse_layouts, _parse_signed_csv
from scripts._gpu_bench_attribution import median_mad, parse_int_csv


def main() -> int:
    import warnings

    q = torch.randn(2, 12, 7, 8)
    k = torch.randn(2, 3, 7, 8)
    v = torch.randn(2, 3, 7, 8)
    qg, kg, vg = _grouped_broadcast_inputs(q, k, v)
    assert qg.ndim == kg.ndim == vg.ndim == 4
    assert qg.shape == kg.shape == vg.shape == (6, 4, 7, 8)
    assert kg.stride(1) == 0 and vg.stride(1) == 0
    grouped = torch.nn.functional.scaled_dot_product_attention(
        qg, kg, vg, is_causal=True
    ).reshape_as(q)
    repeated = torch.nn.functional.scaled_dot_product_attention(
        q, k.repeat_interleave(4, 1), v.repeat_interleave(4, 1), is_causal=True
    )
    torch.testing.assert_close(grouped, repeated)
    assert _unique_storage_mib(qg, kg, vg) < _unique_storage_mib(
        q, k.repeat_interleave(4, 1), v.repeat_interleave(4, 1)
    )

    assert parse_int_csv("1,8,8,128") == [1, 8, 128]
    assert _parse_signed_csv("-1,0,1,-1") == [-1, 0, 1]
    assert _parse_layouts("inference,training,inference") == ["inference", "training"]
    assert median_mad([1.0, 2.0, 100.0]) == (2.0, 1.0)
    ledger = _fp8_tensor_ledger(8, 4, 6)
    assert ledger["B_prepared_fp8"]["persistent"] > ledger["C_weight_cached"]["persistent"]
    assert ledger["C_weight_cached"]["per_call_temporaries"] < ledger["D_delayed"]["per_call_temporaries"]

    def warning_probe():
        warnings.warn("backend marker", UserWarning)
        return 7

    value, diagnostics, error = _captured_call(warning_probe)
    assert value == 7 and diagnostics == ["backend marker"] and error is None

    assert _group_gate_exit([], []) == 0
    assert _group_gate_exit(["exception"], []) == 1
    assert _group_gate_exit(["contract"], ["band"]) == 1
    assert _group_gate_exit([], ["band"]) == 8
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

    fp8_rows = [
        {"speedup": value, "nrms": 0.0377, "cosine": 0.99929,
         "k": 768, "n": 2048, "name": name, "peak_mib": 39.5}
        for name, value in (("current", 0.816), ("delayed", 1.015))
    ]
    code, reason, numeric, candidates = _gate_decision(
        fp8_rows, min_speedup=1.10, max_nrms=0.03, min_cosine=0.999,
    )
    assert code == 8 and reason == "no speed candidate" and numeric and not candidates

    approx = [(0, 0.865, 0.9814), (4, 0.857, 0.9791),
              (8, 0.851, 0.9774), (16, 0.840, 0.9740)]
    monotonic_w, monotonic_y, improvement, viable = _approximation_gate(
        approx, max_output_nrms=0.90, min_output_improvement=0.10,
    )
    assert monotonic_w and monotonic_y and improvement < 0.01 and not viable
    print("[PASS] backend gates: GQA grouped broadcast/warnings, sparse agreement, "
          "FP8/P093 scientific negatives, P076 exit separation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
