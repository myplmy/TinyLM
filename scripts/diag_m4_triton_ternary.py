#!/usr/bin/env python3
"""P104A M4 direct Triton ternary-matmul gate; user-run CUDA only.

This bypasses ternary_kernel_linear's exception fallback. PASS means this
specific kernel call, reference agreement, and peak-memory observation;
it is not whole TLinear training or speed adoption.
"""
from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--m", type=int, default=64)
    ap.add_argument("--k", type=int, default=768)
    ap.add_argument("--n", type=int, default=768)
    ap.add_argument("--group", type=int, default=128)
    ap.add_argument("--max-nrms", type=float, default=0.02)
    ap.add_argument("--min-cosine", type=float, default=0.999)
    args = ap.parse_args()
    if min(args.m, args.k, args.n, args.group) < 1 or args.k % args.group:
        ap.error("positive dimensions and k divisible by group are required")
    if not (0 < args.max_nrms < 1 and 0 < args.min_cosine <= 1):
        ap.error("invalid numeric thresholds")
    if args.check_only:
        print(f"[CHECK_ONLY] M4 Triton direct gate M={args.m} K={args.k} N={args.n} G={args.group}; CUDA NOT_RUN")
        return 0

    import torch
    import torch.nn.functional as F
    import tinylm.model.ternary_kernel as kernel

    print(f"platform={platform.system()} torch={torch.__version__} cuda={torch.version.cuda}")
    print(f"cudnn={torch.backends.cudnn.version()} triton_import={kernel._HAS_TRITON}")
    if platform.system() != "Linux" or not torch.cuda.is_available() or not kernel._HAS_TRITON:
        print("[UNAVAILABLE] WSL CUDA and Triton are required; no fallback counted as PASS")
        return 2
    torch.manual_seed(104)
    device = torch.device("cuda")
    x = torch.randn(args.m, args.k, device=device, dtype=torch.bfloat16)
    codes = torch.randint(-1, 2, (args.n, args.k), device=device, dtype=torch.int8)
    alpha = torch.rand(args.n, args.k // args.group, device=device, dtype=torch.float32) + 0.05
    weight = (codes.float().view(args.n, -1, args.group) * alpha[..., None]).reshape(args.n, args.k)
    ref = F.linear(x.float(), weight)
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    before = torch.cuda.memory_allocated()
    try:
        got = kernel._triton_matmul(x, codes, alpha, args.group)
        torch.cuda.synchronize()
    except Exception as exc:
        print(f"[UNAVAILABLE] direct Triton call failed: {type(exc).__name__}: {exc}")
        return 2
    peak = torch.cuda.max_memory_allocated()
    diff = got.float() - ref.float()
    nrms = float(diff.square().mean().sqrt() / ref.float().square().mean().sqrt().clamp_min(1e-12))
    cosine = float(F.cosine_similarity(got.float().reshape(1, -1), ref.float().reshape(1, -1)))
    max_abs = float(diff.abs().amax())
    finite = bool(torch.isfinite(got).all())
    print(f"direct_call=YES dtype={got.dtype} nrms={nrms:.8g} cosine={cosine:.8g} max_abs={max_abs:.8g}")
    print(f"peak_allocated_bytes={peak} incremental_peak_bytes={max(0, peak-before)}")
    if not finite or nrms > args.max_nrms or cosine < args.min_cosine:
        print("[GATE NEGATIVE] direct call ran but numeric threshold failed")
        return 8
    print("[PASS] M4 direct Triton invocation, numeric gate, peak allocation; whole-model NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
