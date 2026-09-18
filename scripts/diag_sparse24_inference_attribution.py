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


def _error_stats(torch, actual, expected) -> dict[str, float | bool]:
    """Return scale-aware FP16 GEMM agreement metrics.

    Elementwise ``rtol/atol`` is retained as a diagnostic, but it is not a
    suitable sole gate for wide random GEMMs: values near zero fail an
    absolute threshold while the aggregate output remains accurate.  The
    gate therefore uses normalized RMS plus cosine and still prints max-abs.
    """
    a = actual.float().reshape(-1)
    e = expected.float().reshape(-1)
    delta = a - e
    rms = delta.square().mean().sqrt()
    reference_rms = e.square().mean().sqrt()
    normalized_rms = rms / reference_rms.clamp_min(1e-12)
    denom = a.norm() * e.norm()
    cosine = (a.dot(e) / denom.clamp_min(1e-12))
    finite = bool(torch.isfinite(a).all() and torch.isfinite(e).all())
    try:
        torch.testing.assert_close(actual, expected, rtol=2e-2, atol=2e-2)
        legacy_close = True
    except AssertionError:
        legacy_close = False
    return {
        "max_abs": float(delta.abs().max()),
        "max_abs_ratio": float(delta.abs().max() / reference_rms.clamp_min(1e-12)),
        "rms": float(rms),
        "reference_rms": float(reference_rms),
        "normalized_rms": float(normalized_rms),
        "cosine": float(cosine),
        "finite": finite,
        "legacy_close": legacy_close,
    }


def _agreement_ok(metrics: dict[str, float | bool], *, max_nrms: float,
                  max_abs_ratio: float, min_cosine: float) -> bool:
    return bool(
        metrics["finite"]
        and float(metrics["normalized_rms"]) <= max_nrms
        and float(metrics["max_abs_ratio"]) <= max_abs_ratio
        and float(metrics["cosine"]) >= min_cosine
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m-values", type=_parse_m_values,
                        default=_parse_m_values("1,16,128,1024,8192"))
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--iters", type=int, default=30)
    parser.add_argument("--prefill-speedup", type=float, default=1.10)
    parser.add_argument("--max-nrms", type=float, default=1e-3,
                        help="maximum RMS(error)/RMS(reference) for FP16 GEMM")
    parser.add_argument("--max-abs-ratio", type=float, default=1e-2,
                        help="maximum max_abs(error)/RMS(reference)")
    parser.add_argument("--min-cosine", type=float, default=0.999999,
                        help="minimum flattened-output cosine agreement")
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
          "ref_rms\tnrms\tmax_abs_ratio\tcosine\tlegacy_close\t"
          "dense_peak_MiB\tsparse_peak_MiB")

    inference_prefill = []
    inference_decode = []
    unsupported = []
    correctness_failures = []
    legacy_warnings = []
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
                metrics = _error_stats(torch, actual, expected)
                if not bool(metrics["legacy_close"]):
                    legacy_warnings.append((layout, m, k, n))
                if not _agreement_ok(
                    metrics, max_nrms=args.max_nrms,
                    max_abs_ratio=args.max_abs_ratio, min_cosine=args.min_cosine
                ):
                    print(f"[GATE FAIL correctness] layout={layout} M={m} K={k} N={n}: "
                          f"max_abs={metrics['max_abs']:.6g} rms={metrics['rms']:.6g} "
                          f"ref_rms={metrics['reference_rms']:.6g} "
                          f"nrms={metrics['normalized_rms']:.6g} "
                          f"max_abs_ratio={metrics['max_abs_ratio']:.6g} "
                          f"cosine={metrics['cosine']:.9f} finite={metrics['finite']}")
                    correctness_failures.append((layout, m, k, n))
                    # A bad row must not suppress later shape diagnostics.  Its
                    # speed is not admitted to the candidate set.
                    continue
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
                      f"{speedup:.3f}\t{metrics['max_abs']:.6g}\t{metrics['rms']:.6g}\t"
                      f"{metrics['reference_rms']:.6g}\t{metrics['normalized_rms']:.6g}\t"
                      f"{metrics['max_abs_ratio']:.6g}\t"
                      f"{metrics['cosine']:.9f}\t{int(bool(metrics['legacy_close']))}\t"
                      f"{dense_peak_mib:.3f}\t{sparse_peak_mib:.3f}")
                if layout == "inference_exact2of4":
                    if m == 1:
                        inference_decode.append(speedup)
                    elif m <= 1024:
                        inference_prefill.append(speedup)

    if legacy_warnings:
        print(f"[LEGACY TOLERANCE WARNING] elementwise rtol/atol failed in "
              f"{len(legacy_warnings)} row(s), but scale-aware agreement decides the gate: "
              f"{legacy_warnings}")
    if correctness_failures:
        print(f"[GATE FAIL] scale-aware correctness failures={len(correctness_failures)} "
              f"rows={correctness_failures}")
        return 4
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
