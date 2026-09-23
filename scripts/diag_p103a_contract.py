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
        boundary_cache_bytes,
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
    print(f"[PASS] P103A X1 toy VJP; X2 full/tile output; X3 INT8 nrms={nrms:.6g} size={expected}B")
    print("[LIMIT] X1 transformer attention, X2 optimizer, X3 whole-model/RAM/quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
