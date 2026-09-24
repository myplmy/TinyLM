#!/usr/bin/env python3
"""P103A CPU toy gates for X1 prefix VJP, X2 physical FFN slices, X3 INT8 cache."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()
    if args.check_only:
        print("[CHECK_ONLY] P103A X1/X2/X3 tensor contracts; model/GPU/RAM allocation NOT_RUN")
        return 0
    import torch
    import torch.nn.functional as F
    from tinylm.train.p103a_contract import (
        ffn_tiles, quantize_boundary_int8, dequantize_boundary_int8,
        boundary_cache_bytes, BoundaryTable, ffn_tile_accounting,
    )

    torch.manual_seed(103)
    shared = torch.randn(5, 16)
    branch_a, branch_b = torch.randn(3, 16), torch.randn(4, 16)
    weight = torch.randn(16, 16, requires_grad=True)
    a = F.linear(shared, weight)
    b = F.linear(shared, weight)
    independent = (a.mean() + F.linear(branch_a, weight).mean()
                   + b.mean() + F.linear(branch_b, weight).mean())
    grad_independent = torch.autograd.grad(independent, weight)[0]
    cached = F.linear(shared, weight)
    shared_loss = (2 * cached.mean() + F.linear(branch_a, weight).mean()
                   + F.linear(branch_b, weight).mean())
    grad_shared = torch.autograd.grad(shared_loss, weight)[0]
    if not torch.allclose(grad_independent, grad_shared, rtol=1e-6, atol=1e-6):
        raise RuntimeError("X1 toy prefix-gradient restoration differs")

    x = torch.randn(8, 128)
    gate = torch.randn(256, 128, requires_grad=True)
    up = torch.randn(256, 128, requires_grad=True)
    down = torch.randn(128, 256, requires_grad=True)
    full = F.linear(F.silu(F.linear(x, gate)) * F.linear(x, up), down)
    tiled = ffn_tiles(x, gate, up, down, [0, 1, 2, 3], tile_size=64)
    if not torch.allclose(full, tiled, rtol=1e-5, atol=1e-5):
        raise RuntimeError("X2 four-tile full-width output differs")
    one = ffn_tiles(x, gate, up, down, [0], tile_size=64)
    if one.shape != full.shape or not bool(torch.isfinite(one).all()):
        raise RuntimeError("X2 selected tile output invalid")

    boundary = torch.randn(128, 768)
    boundary[0, 0] = 8.0
    codes, scales = quantize_boundary_int8(boundary, group=64)
    restored = dequantize_boundary_int8(codes, scales, group=64)
    nrms = float((restored - boundary).square().mean().sqrt()
                 / boundary.square().mean().sqrt())
    expected = 16_320_000_000
    if boundary_cache_bytes(20_000_000, 768) != expected:
        raise RuntimeError("X3 20M cache byte accounting differs")
    if codes.dtype != torch.int8 or scales.dtype != torch.float32 or nrms > 0.03:
        raise RuntimeError(f"X3 INT8 fixture failed: nrms={nrms}")
    small = boundary[:12, :64]
    for bad, bad_group in ((small, 0), (torch.full_like(small, float("nan")), 64)):
        try:
            BoundaryTable(bad, quantized=False, group=bad_group)
        except ValueError:
            pass
        else:
            raise RuntimeError("X3 invalid boundary cache was accepted")
    exact_table = BoundaryTable(small, quantized=False, group=64)
    int8_table = BoundaryTable(small, quantized=True, group=64)
    indices = torch.tensor([3, 2, 3, 11], dtype=torch.long)
    if exact_table.payload_bytes != 12 * 64 * 4 or int8_table.payload_bytes != 12 * (64 + 4):
        raise RuntimeError("X3 exact/INT8 table payload accounting differs")
    if not torch.equal(exact_table.gather(indices), small.index_select(0, indices)):
        raise RuntimeError("X3 exact boundary cache changed frozen activations")
    tail = torch.randn(8, 64, requires_grad=True)
    reference_loss = F.linear(small.index_select(0, indices), tail).square().mean()
    cached_loss = F.linear(exact_table.gather(indices), tail).square().mean()
    reference_grad = torch.autograd.grad(reference_loss, tail, retain_graph=True)[0]
    cached_grad = torch.autograd.grad(cached_loss, tail)[0]
    if (not torch.allclose(reference_loss, cached_loss, atol=0, rtol=0)
            or not torch.allclose(reference_grad, cached_grad, atol=0, rtol=0)):
        raise RuntimeError("X3 exact frozen boundary changed tail loss or gradient")
    quant_hidden = int8_table.gather(indices)
    if quant_hidden.shape != (4, 64) or not bool(torch.isfinite(quant_hidden).all()):
        raise RuntimeError("X3 INT8 gathered boundary is invalid")
    windows = torch.arange(4 * 6, dtype=torch.long).reshape(4, 6)
    window_hidden = torch.randn(4, 6, 64)
    from tinylm.train.p103a_contract import WindowBoundaryTable
    parent_sha = "A" * 64
    ordered = torch.tensor([2, 0], dtype=torch.long)
    exact_windows = WindowBoundaryTable(windows, window_hidden,
                                         parent_sha256=parent_sha, split_layer=2,
                                         quantized=False)
    picked = exact_windows.gather(ordered, windows.index_select(0, ordered),
                                  parent_sha256=parent_sha, split_layer=2)
    if not torch.equal(picked, window_hidden.index_select(0, ordered)):
        raise RuntimeError("X3 fixed-window exact boundary changed")
    quant_windows = WindowBoundaryTable(windows, window_hidden,
                                         parent_sha256=parent_sha, split_layer=2,
                                         quantized=True)
    if not bool(torch.isfinite(quant_windows.gather(
            ordered, windows.index_select(0, ordered),
            parent_sha256=parent_sha, split_layer=2)).all()):
        raise RuntimeError("X3 fixed-window INT8 boundary is non-finite")
    wrong = windows.index_select(0, ordered).clone()
    wrong[0, 0] += 1
    for supplied, sha in ((wrong, parent_sha),
                          (windows.index_select(0, ordered), "B" * 64)):
        try:
            exact_windows.gather(ordered, supplied, parent_sha256=sha, split_layer=2)
        except ValueError:
            pass
        else:
            raise RuntimeError("X3 changed window context/parent was accepted")
    from tinylm.train.p103a_contract import fixed_window_starts, gather_fixed_window_xy
    stream = torch.arange(13, dtype=torch.long)
    starts = fixed_window_starts(stream.numel(), 4)
    if starts.tolist() != [0, 4, 8]:
        raise RuntimeError("X3 fixed-window start grid differs")
    fx, fy = gather_fixed_window_xy(stream, starts, 4)
    if (fx.tolist() != [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]]
            or fy.tolist() != [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]):
        raise RuntimeError("X3 fixed S+1 windows lost NTP shift")
    try:
        gather_fixed_window_xy(stream, torch.tensor([1]), 4)
    except ValueError:
        pass
    else:
        raise RuntimeError("X3 off-grid random crop was accepted")
    accounting = ffn_tile_accounting(768, 2048, 16, 512, 1)
    if (accounting["full_ffn_weight_elements"] != 75497472
            or accounting["selected_gemm_weight_elements"] != 18874368
            or accounting["selected_operand_fraction"] != 0.25
            or accounting["fp32_master_bytes"] != 301989888
            or accounting["muon_buffer_bytes"] != 301989888
            or accounting["optimizer_shape_fraction"] != 1.0):
        raise RuntimeError("X2 selected GEMM vs full Muon-state accounting differs")
    from tinylm.train.p103a_contract import fixed_window_cache_budget, validate_window_cache_manifest
    budget = fixed_window_cache_budget(2_000_000, 1024, 768)
    if (budget["windows"] != 1953 or budget["boundary_tokens"] != 1_999_872
            or budget["unused_source_tokens"] != 127
            or budget["exact_payload_bytes"] != 6_143_606_784
            or budget["int8_per64_payload_bytes"] != 1_631_895_552):
        raise RuntimeError("X3 2M fixed-window payload accounting differs")
    manifest = {"schema": "P103A_FIXED_WINDOW_CACHE_V1",
                "parent_sha256": "A" * 64, "tokenizer_sha256": "B" * 64,
                "source_cache_meta_sha256": "C" * 64,
                "source_window_sha256": "D" * 64,
                "lower_function_sha256": "E" * 64,
                "context_policy": "fixed_window_causal_start0_v1",
                "tokenizer_lineage": "legacy32", "backend_signature": "cpu_fp32_fixture",
                "split_layer": 12, "precision": "fp32", "source_tokens": 2_000_000,
                "seq": 1024, "dim": 768, "group": 64, "windows": 1953,
                "boundary_tokens": 1_999_872, "payload_bytes": 6_143_606_784}
    validate_window_cache_manifest(manifest)
    validate_window_cache_manifest(dict(manifest, precision="int8_per64",
                                        payload_bytes=1_631_895_552))
    for bad in (dict(manifest, parent_sha256="wrong"),
                dict(manifest, context_policy="random_crop"),
                dict(manifest, payload_bytes=6_143_606_783)):
        try:
            validate_window_cache_manifest(bad)
        except ValueError:
            pass
        else:
            raise RuntimeError("X3 stale/wrong 2M cache manifest was accepted")
    print(f"[BUDGET] X2 selected operand 0.25, full Muon buffer 301989888B; X3 2M windows={budget['windows']} exact={budget['exact_payload_bytes']}B INT8={budget['int8_per64_payload_bytes']}B")
    print(f"[PASS] P103A X1 toy VJP; X2 full/tile; X3 exact window-key/fixed S+1 grid, INT8 nrms={nrms:.6g} size={expected}B")
    print("[LIMIT] X1 transformer attention, X2 optimizer, X3 whole-model/RAM/quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
