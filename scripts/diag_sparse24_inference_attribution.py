#!/usr/bin/env python3
"""P025B Stage0bWc: attribute 2:4 inference/training-pack speed by M.

This is a synthetic kernel diagnostic, not trained-model inference. Packing is
performed once and excluded from timings. The one-way exact-2:4 inference pack
and bidirectional training pack are measured separately.
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


def _parse_m_values(raw: str) -> list[int]:
    values = []
    for item in raw.split(","):
        value = int(item.strip())
        if value <= 0:
            raise argparse.ArgumentTypeError("M values must be positive")
        if value not in values:
            values.append(value)
    if not values:
        raise argparse.ArgumentTypeError("at least one M value is required")
    return values


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


def _peak_delta_mib(torch, fn) -> float:
    torch.cuda.synchronize()
    baseline = torch.cuda.memory_allocated()
    torch.cuda.reset_peak_memory_stats()
    output = fn()
    torch.cuda.synchronize()
    peak = torch.cuda.max_memory_allocated()
    del output
    return max(0, peak - baseline) / 2**20


def _error_stats(actual, expected) -> tuple[float, float]:
    delta = (actual.float() - expected.float()).abs()
    return float(delta.max()), float(delta.square().mean().sqrt())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m-values", type=_parse_m_values,
                        default=_parse_m_values("1,16,128,1024,8192"))
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--iters", type=int, default=30)
    parser.add_argument("--prefill-speedup", type=float, default=1.10)
    parser.add_argument("--require-wsl", action="store_true")
    args = parser.parse_args()

    release = platform.uname().release
    distro = os.environ.get("WSL_DISTRO_NAME", "")
    is_wsl = bool(distro) or "microsoft" in release.lower()
    print(f"runtime_system={platform.system()} release={release} "
          f"WSL_DISTRO_NAME={distro or '<unset>'}")
    if args.require_wsl and not is_wsl:
        print("[GATE FAIL] --require-wsl was set outside WSL")
        return 2

    import torch
    import torch.nn.functional as F
    from tinylm.model.sparse_connectivity import exact_nm_mask

    try:
        package = importlib.metadata.version("nvidia-cusparselt-cu13")
    except importlib.metadata.PackageNotFoundError:
        package = "NOT_INSTALLED"
    print(f"torch={torch.__version__} cuda={torch.version.cuda} "
          f"cudnn={torch.backends.cudnn.version()} cusparselt={package} "
          f"compiled={bool(getattr(torch._C, '_has_cusparselt', False))} "
          f"available={torch.backends.cusparselt.is_available()} "
          f"backend_version={torch.backends.cusparselt.version()}")
    if not torch.cuda.is_available():
        print("[GATE FAIL] CUDA unavailable")
        return 2
    try:
        from torch.sparse import (
            SparseSemiStructuredTensorCUSPARSELT,
            to_sparse_semi_structured,
        )
    except Exception as exc:
        print(f"[GATE FAIL] sparse semi-structured API unavailable: {exc}")
        return 2

    capability = torch.cuda.get_device_capability()
    print(f"gpu={torch.cuda.get_device_name()} sm_{capability[0]}{capability[1]} "
          f"m_values={args.m_values} warmup={args.warmup} iters={args.iters}")
    print("NOTE: packing is outside timing; this is kernel attribution, not model inference.")
    print("layout\tM\tK\tN\tdense_ms\tsparse_ms\tspeedup\tmax_abs\trms\t"
          "dense_peak_MiB\tsparse_peak_MiB")

    inference_prefill = []
    inference_decode = []
    unsupported = []
    for k, n in ((768, 2048), (2048, 768)):
        torch.manual_seed(2500 + k + n)
        dense_weight = torch.randn(n, k, device="cuda", dtype=torch.float16)
        masked_weight = dense_weight * exact_nm_mask(dense_weight, n=2, m=4)
        inference_kept = masked_weight.ne(0).reshape(n, -1, 4).sum(dim=-1)
        if not bool(torch.all(inference_kept == 2)):
            print(f"[GATE FAIL mask] K={k} N={n}: inference mask is not exact 2:4")
            return 3
        try:
            inference_sparse = to_sparse_semi_structured(masked_weight)
            training_sparse = SparseSemiStructuredTensorCUSPARSELT.prune_dense_static_sort(
                dense_weight
            )
            training_dense = training_sparse.to_dense()
        except Exception as exc:
            print(f"[GATE FAIL pack] K={k} N={n}: {type(exc).__name__}: {exc}")
            return 3
        print(f"[pack] K={k} N={n} "
              f"inference(packed={inference_sparse.packed is not None},"
              f"packed_t={inference_sparse.packed_t is not None}) "
              f"training(packed={training_sparse.packed is not None},"
              f"packed_t={training_sparse.packed_t is not None})")
        training_nonzero = training_dense.ne(0)
        tiles = training_nonzero.reshape(n // 4, 4, k // 4, 4).permute(0, 2, 1, 3)
        row_counts = tiles.sum(dim=-1)
        col_counts = tiles.sum(dim=-2)
        if not bool(torch.all(row_counts <= 2)) or not bool(torch.all(col_counts <= 2)):
            print(f"[GATE FAIL mask] K={k} N={n}: training pack violates bidirectional <=2:4")
            return 3
        tile_kept = tiles.sum(dim=(-1, -2))
        print(f"[mask] K={k} N={n} inference_kept_per_row4=2 "
              f"training_kept_per_4x4={int(tile_kept.min())}..{int(tile_kept.max())}")

        for m in args.m_values:
            x = torch.randn(m, k, device="cuda", dtype=torch.float16)
            for layout, dense, sparse in (
                ("inference_exact2of4", masked_weight, inference_sparse),
                ("training_bidirectional", training_dense, training_sparse),
            ):
                try:
                    expected = F.linear(x, dense)
                    actual = F.linear(x, sparse)
                except (NotImplementedError, RuntimeError) as exc:
                    print(f"[UNSUPPORTED] layout={layout} M={m} K={k} N={n}: "
                          f"{type(exc).__name__}: {str(exc).splitlines()[0]}")
                    unsupported.append((layout, m, k, n))
                    continue
                try:
                    torch.testing.assert_close(actual, expected, rtol=2e-2, atol=2e-2)
                except AssertionError as exc:
                    max_abs, rms = _error_stats(actual, expected)
                    print(f"[GATE FAIL correctness] layout={layout} M={m} K={k} N={n}: "
                          f"max_abs={max_abs:.6g} rms={rms:.6g}; "
                          f"{str(exc).splitlines()[0]}")
                    return 4
                max_abs, rms = _error_stats(actual, expected)
                try:
                    dense_ms = _median_ms(
                        torch, lambda x=x, dense=dense: F.linear(x, dense),
                        args.warmup, args.iters,
                    )
                    sparse_ms = _median_ms(
                        torch, lambda x=x, sparse=sparse: F.linear(x, sparse),
                        args.warmup, args.iters,
                    )
                    dense_peak_mib = _peak_delta_mib(
                        torch, lambda x=x, dense=dense: F.linear(x, dense)
                    )
                    sparse_peak_mib = _peak_delta_mib(
                        torch, lambda x=x, sparse=sparse: F.linear(x, sparse)
                    )
                except Exception as exc:
                    print(f"[GATE FAIL timing] layout={layout} M={m} K={k} N={n}: "
                          f"{type(exc).__name__}: {str(exc).splitlines()[0]}")
                    return 5
                speedup = dense_ms / sparse_ms
                print(f"{layout}\t{m}\t{k}\t{n}\t{dense_ms:.6f}\t{sparse_ms:.6f}\t"
                      f"{speedup:.3f}\t{max_abs:.6g}\t{rms:.6g}\t"
                      f"{dense_peak_mib:.3f}\t{sparse_peak_mib:.3f}")
                if layout == "inference_exact2of4":
                    if m == 1:
                        inference_decode.append(speedup)
                    elif m <= 1024:
                        inference_prefill.append(speedup)

    if inference_decode:
        print(f"[DECODE] supported_shapes={len(inference_decode)} "
              f"min_speedup={min(inference_decode):.3f}x "
              f"max_speedup={max(inference_decode):.3f}x")
    else:
        print("[DECODE] M=1 inference pack unsupported; decode acceleration unavailable.")
    if not inference_prefill:
        print("[GATE NEGATIVE] no supported M=16..1024 inference-prefill measurement")
        return 8
    best = max(inference_prefill)
    floor = min(inference_prefill)
    print(f"[PREFILL] supported_shapes={len(inference_prefill)} "
          f"min_speedup={floor:.3f}x max_speedup={best:.3f}x "
          f"unsupported_cases={len(unsupported)}")
    if best < args.prefill_speedup:
        print(f"[GATE NEGATIVE] no inference-prefill shape reached "
              f"{args.prefill_speedup:.2f}x; do not claim inference acceleration.")
        return 8
    print(f"[GATE CANDIDATE] at least one inference-prefill shape reached "
          f"{args.prefill_speedup:.2f}x. Trained-checkpoint inference remains NOT_RUN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
