#!/usr/bin/env python3
"""P025B Stage0a: strict native 2:4 backend and same-session speed gate."""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _median_ms(torch, fn, warmup: int, iters: int) -> float:
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()
    samples = []
    for _ in range(iters):
        start = time.perf_counter()
        fn()
        torch.cuda.synchronize()
        samples.append((time.perf_counter() - start) * 1e3)
    return statistics.median(samples)


def main() -> int:
    ap = argparse.ArgumentParser(description="P025B native 2:4 backend gate")
    ap.add_argument("--m", type=int, default=8192)
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--iters", type=int, default=30)
    args = ap.parse_args()

    import torch
    import torch.nn.functional as F
    from tinylm.model.sparse_connectivity import exact_nm_mask

    if not torch.cuda.is_available():
        print("[GATE FAIL] CUDA is unavailable; native 2:4 was not tested.")
        return 2
    try:
        from torch.sparse import to_sparse_semi_structured
    except Exception as exc:
        print(f"[GATE FAIL] torch sparse semi-structured API unavailable: {exc}")
        return 2

    device = "cuda"
    capability = torch.cuda.get_device_capability()
    print(
        f"GPU={torch.cuda.get_device_name()} sm_{capability[0]}{capability[1]} "
        f"torch={torch.__version__}"
    )
    shapes = [(768, 2048), (2048, 768)]  # (K, N), actual TinyLM MLP directions
    speedups = []
    for k, n in shapes:
        torch.manual_seed(250 + k + n)
        x = torch.randn(args.m, k, device=device, dtype=torch.float16)
        dense_weight = torch.randn(n, k, device=device, dtype=torch.float16)
        mask = exact_nm_mask(dense_weight, n=2, m=4)
        counts = mask.reshape(n, -1, 4).sum(dim=-1)
        if not bool(torch.all(counts == 2)):
            raise AssertionError("generated mask violates exact 2:4 conservation")
        masked_weight = dense_weight * mask
        try:
            sparse_weight = to_sparse_semi_structured(masked_weight)
            dense_out = F.linear(x, masked_weight)
            sparse_out = F.linear(x, sparse_weight)
            torch.testing.assert_close(sparse_out, dense_out, rtol=2e-2, atol=2e-2)

            # Dgrad support is required; weight-gradient support is audited separately later.
            x_grad = x.detach().clone().requires_grad_(True)
            F.linear(x_grad, sparse_weight).float().square().mean().backward()
            if x_grad.grad is None or not torch.isfinite(x_grad.grad).all():
                raise AssertionError("sparse input-gradient missing or non-finite")

            dense_ms = _median_ms(torch, lambda: F.linear(x, masked_weight), args.warmup, args.iters)
            sparse_ms = _median_ms(torch, lambda: F.linear(x, sparse_weight), args.warmup, args.iters)
        except Exception as exc:
            print(f"[GATE FAIL] M={args.m} K={k} N={n}: {type(exc).__name__}: {exc}")
            return 3
        speedup = dense_ms / sparse_ms
        speedups.append(speedup)
        print(
            f"M={args.m} K={k} N={n} layout={type(sparse_weight).__name__} "
            f"dense={dense_ms:.4f}ms sparse={sparse_ms:.4f}ms speedup={speedup:.3f}x"
        )

    floor = min(speedups)
    if floor < 1.25:
        print(f"[GATE NEGATIVE] minimum MLP speedup {floor:.3f}x is below 1.25x.")
        print("Do not open acceleration stages; memory-only continuation requires a new decision.")
        return 4
    print(f"[GATE PASS] native 2:4 forward and input-gradient worked; minimum speedup={floor:.3f}x")
    print("NOTE: whole-step speedup, sparse weight-gradient, quality, and VRAM remain NOT_RUN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
