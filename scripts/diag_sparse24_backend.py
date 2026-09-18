#!/usr/bin/env python3
"""P025B native 2:4 backend diagnostic with inference/training packing split.

``to_sparse_semi_structured`` only packs the original orientation.  That is
enough for ``F.linear`` forward, but input-gradient needs the transposed packed
representation as well.  PyTorch's training-oriented ``prune_dense_static_sort``
creates both.  Keep the two paths separate so a missing ``packed_t`` is not
misreported as a cuSPARSELt/backend failure.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import os
import platform
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


def _packing_state(sparse_weight, label: str) -> None:
    transposed = sparse_weight.t()
    print(f"[{label}] shape={tuple(sparse_weight.shape)}")
    print(f"[{label}] packed_none={sparse_weight.packed is None}")
    print(f"[{label}] packed_t_none={sparse_weight.packed_t is None}")
    print(f"[{label}] t_packed_none={transposed.packed is None}")
    print(f"[{label}] t_packed_t_none={transposed.packed_t is None}")


def _is_missing_transpose_pack(exc: Exception) -> bool:
    return (
        isinstance(exc, NotImplementedError)
        and "matmul: operation is not supported" in str(exc)
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="P025B native 2:4 backend gate")
    ap.add_argument("--m", type=int, default=8192)
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--iters", type=int, default=30)
    ap.add_argument("--require-wsl", action="store_true",
                    help="WSL 재개 probe: Linux/WSL runtime이 아니면 CUDA 호출 전에 중단")
    args = ap.parse_args()

    release = platform.uname().release
    distro = os.environ.get("WSL_DISTRO_NAME", "")
    is_wsl = bool(distro) or "microsoft" in release.lower()
    print(f"runtime_system={platform.system()} release={release} WSL_DISTRO_NAME={distro or '<unset>'}")
    if args.require_wsl and not is_wsl:
        print("[GATE FAIL] --require-wsl was set but this process is not running inside WSL.")
        return 2

    import torch
    import torch.nn.functional as F
    from tinylm.model.sparse_connectivity import exact_nm_mask

    try:
        cusparselt_pkg = importlib.metadata.version("nvidia-cusparselt-cu13")
    except importlib.metadata.PackageNotFoundError:
        cusparselt_pkg = "NOT_INSTALLED"
    cusparselt_compiled = bool(getattr(torch._C, "_has_cusparselt", False))
    print(
        f"torch={torch.__version__} torch_cuda={torch.version.cuda} "
        f"cudnn={torch.backends.cudnn.version()} nvidia-cusparselt-cu13={cusparselt_pkg} "
        f"cusparselt_compiled={cusparselt_compiled}"
    )

    if not torch.cuda.is_available():
        print("[GATE FAIL] CUDA is unavailable; native 2:4 was not tested.")
        return 2
    try:
        from torch.sparse import (
            SparseSemiStructuredTensorCUSPARSELT,
            to_sparse_semi_structured,
        )
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
            inference_sparse = to_sparse_semi_structured(masked_weight)
        except Exception as exc:
            print(f"[GATE FAIL conversion] M={args.m} K={k} N={n}: {type(exc).__name__}: {exc}")
            return 3

        _packing_state(inference_sparse, "inference-pack")
        try:
            dense_out = F.linear(x, masked_weight)
            sparse_out = F.linear(x, inference_sparse)
            torch.testing.assert_close(sparse_out, dense_out, rtol=2e-2, atol=2e-2)
        except Exception as exc:
            print(f"[GATE FAIL forward] M={args.m} K={k} N={n}: {type(exc).__name__}: {exc}")
            return 4

        print(f"[PASS forward] M={args.m} K={k} N={n} exact row-wise 2:4")

        # The one-way inference pack is expected to lack packed_t.  Probe it so
        # the historical failure can be attributed to the exact stage.
        try:
            dense_x = x.detach().clone().requires_grad_(True)
            sparse_x = x.detach().clone().requires_grad_(True)
            F.linear(dense_x, masked_weight).float().square().mean().backward()
            F.linear(sparse_x, inference_sparse).float().square().mean().backward()
            if sparse_x.grad is None or not torch.isfinite(sparse_x.grad).all():
                raise AssertionError("sparse input-gradient missing or non-finite")
            torch.testing.assert_close(
                sparse_x.grad, dense_x.grad, rtol=2e-2, atol=2e-2
            )
            print("[INFO inference-pack dgrad] supported despite packed_t state")
        except Exception as exc:
            if not _is_missing_transpose_pack(exc):
                print(f"[GATE FAIL inference dgrad] M={args.m} K={k} N={n}: "
                      f"{type(exc).__name__}: {exc}")
                return 5
            print("[EXPECTED inference-pack limit] input-gradient needs packed_t: "
                  f"{type(exc).__name__}: {exc}")

        # Training-oriented packing prunes in a bidirectional 4x4 tile and
        # materializes both packed orientations.  This is the path whose dgrad
        # capability decides whether native sparse training can proceed.
        try:
            training_sparse = SparseSemiStructuredTensorCUSPARSELT.prune_dense_static_sort(
                dense_weight
            )
        except Exception as exc:
            print(f"[GATE FAIL training-pack] M={args.m} K={k} N={n}: "
                  f"{type(exc).__name__}: {exc}")
            return 6

        _packing_state(training_sparse, "training-pack")
        if training_sparse.packed is None or training_sparse.packed_t is None:
            print("[GATE FAIL training-pack] bidirectional pack is incomplete")
            return 6

        try:
            training_dense = training_sparse.to_dense()
            nonzero = training_dense.ne(0)
            tiles = nonzero.reshape(n // 4, 4, k // 4, 4).permute(0, 2, 1, 3)
            row_counts = tiles.sum(dim=-1)
            col_counts = tiles.sum(dim=-2)
            if not bool(torch.all(row_counts <= 2)) or not bool(torch.all(col_counts <= 2)):
                raise AssertionError("training pack violates bidirectional at-most-2:4")
            tile_kept = tiles.sum(dim=(-1, -2))
            print(
                f"[PASS training-mask] bidirectional <=2:4; "
                f"kept_per_4x4={int(tile_kept.min())}..{int(tile_kept.max())}"
            )

            dense_train_out = F.linear(x, training_dense)
            sparse_train_out = F.linear(x, training_sparse)
            torch.testing.assert_close(
                sparse_train_out, dense_train_out, rtol=2e-2, atol=2e-2
            )

            dense_x = x.detach().clone().requires_grad_(True)
            sparse_x = x.detach().clone().requires_grad_(True)
            F.linear(dense_x, training_dense).float().square().mean().backward()
            F.linear(sparse_x, training_sparse).float().square().mean().backward()
            if sparse_x.grad is None or not torch.isfinite(sparse_x.grad).all():
                raise AssertionError("training-pack input-gradient missing or non-finite")
            torch.testing.assert_close(
                sparse_x.grad, dense_x.grad, rtol=2e-2, atol=2e-2
            )

            dense_ms = _median_ms(
                torch, lambda: F.linear(x, training_dense), args.warmup, args.iters
            )
            sparse_ms = _median_ms(
                torch, lambda: F.linear(x, training_sparse), args.warmup, args.iters
            )
        except Exception as exc:
            print(f"[GATE FAIL training forward/dgrad] M={args.m} K={k} N={n}: "
                  f"{type(exc).__name__}: {exc}")
            return 7
        speedup = dense_ms / sparse_ms
        speedups.append(speedup)
        print(
            f"M={args.m} K={k} N={n} layout={type(training_sparse).__name__} "
            f"dense={dense_ms:.4f}ms sparse={sparse_ms:.4f}ms speedup={speedup:.3f}x"
        )

    floor = min(speedups)
    if floor < 1.25:
        print(f"[GATE NEGATIVE] minimum MLP speedup {floor:.3f}x is below 1.25x.")
        print("Do not open acceleration stages; memory-only continuation requires a new decision.")
        return 8
    print(f"[GATE PASS] bidirectionally packed native 2:4 forward and input-gradient worked; "
          f"minimum speedup={floor:.3f}x")
    print("NOTE: whole-step speedup, sparse weight-gradient, quality, and VRAM remain NOT_RUN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
