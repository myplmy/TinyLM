#!/usr/bin/env python3
"""P025B Stage0cW: whole linear primitive attribution for training-shaped M.

The diagnostic times forward, input-gradient and dense weight-gradient as one
fixed-shape primitive.  Sparse packing is measured separately and amortized
over gradient accumulation; it is never hidden outside the reported total.
This is still synthetic FP16 math, not a TLinear or optimizer quality run.
"""
from __future__ import annotations

import argparse
import os
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _event_ms(torch, fn, warmup: int, iters: int) -> float:
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(iters):
        fn()
    end.record()
    end.synchronize()
    return start.elapsed_time(end) / iters


def _wall_ms(torch, fn, warmup: int, iters: int) -> float:
    for _ in range(warmup):
        fn()
    values = []
    for _ in range(iters):
        torch.cuda.synchronize()
        started = time.perf_counter()
        fn()
        torch.cuda.synchronize()
        values.append((time.perf_counter() - started) * 1e3)
    return statistics.median(values)


def _pack_ms(torch, sparse_cls, weight, repeats: int) -> tuple[object, float]:
    values = []
    packed = None
    for _ in range(repeats):
        torch.cuda.synchronize()
        started = time.perf_counter()
        packed = sparse_cls.prune_dense_static_sort(weight)
        torch.cuda.synchronize()
        values.append((time.perf_counter() - started) * 1e3)
    assert packed is not None
    return packed, statistics.median(values)


def _graph_event_ms(torch, fn, warmup: int, iters: int) -> float:
    stream = torch.cuda.Stream()
    stream.wait_stream(torch.cuda.current_stream())
    with torch.cuda.stream(stream):
        for _ in range(warmup):
            fn()
    torch.cuda.current_stream().wait_stream(stream)
    torch.cuda.synchronize()
    graph = torch.cuda.CUDAGraph()
    with torch.cuda.graph(graph):
        fn()
    graph.replay()
    torch.cuda.synchronize()
    return _event_ms(torch, graph.replay, warmup=1, iters=iters)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m", type=int, default=8192)
    parser.add_argument("--accum", type=int, default=16)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--iters", type=int, default=10)
    parser.add_argument("--pack-repeats", type=int, default=5)
    parser.add_argument("--min-speedup", type=float, default=1.10)
    parser.add_argument("--require-wsl", action="store_true")
    args = parser.parse_args()

    release = platform.uname().release
    is_wsl = bool(os.environ.get("WSL_DISTRO_NAME")) or "microsoft" in release.lower()
    print(f"runtime={platform.system()} release={release} WSL_DISTRO_NAME="
          f"{os.environ.get('WSL_DISTRO_NAME', '<unset>')}")
    if args.require_wsl and not is_wsl:
        print("[GATE FAIL] WSL runtime required")
        return 2

    import torch
    import torch.nn.functional as F
    from torch.sparse import SparseSemiStructuredTensorCUSPARSELT

    if not torch.cuda.is_available():
        print("[GATE FAIL] CUDA unavailable")
        return 2
    print(f"gpu={torch.cuda.get_device_name()} torch={torch.__version__} "
          f"M={args.m} accum={args.accum}")
    print("NOTE: weight-gradient stays dense; pack is once per optimizer step and is amortized explicitly.")
    print("NOTE: graph time excludes pack; amortized time adds pack/accum back.")

    candidates = []
    for k, n in ((768, 2048), (2048, 768)):
        torch.manual_seed(25000 + k + n)
        x = torch.randn(args.m, k, device="cuda", dtype=torch.float16)
        grad_out = torch.randn(args.m, n, device="cuda", dtype=torch.float16)
        original = torch.randn(n, k, device="cuda", dtype=torch.float16)
        sparse, pack_ms = _pack_ms(
            torch, SparseSemiStructuredTensorCUSPARSELT, original, args.pack_repeats
        )
        dense = sparse.to_dense()
        if sparse.packed is None or sparse.packed_t is None:
            print(f"[GATE FAIL] K={k} N={n} bidirectional pack incomplete")
            return 3

        expected_y = F.linear(x, dense)
        expected_dx = grad_out @ dense
        actual_y = F.linear(x, sparse)
        actual_dx = grad_out @ sparse
        torch.testing.assert_close(actual_y, expected_y, rtol=2e-2, atol=2e-2)
        torch.testing.assert_close(actual_dx, expected_dx, rtol=2e-2, atol=2e-2)

        def dense_primitive():
            return F.linear(x, dense), grad_out @ dense, grad_out.t() @ x

        def sparse_primitive():
            return F.linear(x, sparse), grad_out @ sparse, grad_out.t() @ x

        dense_event = _event_ms(torch, dense_primitive, args.warmup, args.iters)
        sparse_event = _event_ms(torch, sparse_primitive, args.warmup, args.iters)
        dense_wall = _wall_ms(torch, dense_primitive, args.warmup, args.iters)
        sparse_wall = _wall_ms(torch, sparse_primitive, args.warmup, args.iters)
        dense_graph = _graph_event_ms(torch, dense_primitive, args.warmup, args.iters)
        sparse_graph = _graph_event_ms(torch, sparse_primitive, args.warmup, args.iters)
        event_amortized = sparse_event + pack_ms / args.accum
        wall_amortized = sparse_wall + pack_ms / args.accum
        graph_amortized = sparse_graph + pack_ms / args.accum
        event_speedup = dense_event / event_amortized
        wall_speedup = dense_wall / wall_amortized
        graph_speedup = dense_graph / graph_amortized
        candidates.append(max(event_speedup, wall_speedup, graph_speedup))
        print(
            f"[shape] M={args.m} K={k} N={n} pack_ms={pack_ms:.6f} "
            f"pack_per_micro_ms={pack_ms/args.accum:.6f}"
        )
        print(
            f"  eager_event dense={dense_event:.6f} sparse={sparse_event:.6f} "
            f"amortized={event_amortized:.6f} speedup={event_speedup:.3f}x"
        )
        print(
            f"  eager_wall  dense={dense_wall:.6f} sparse={sparse_wall:.6f} "
            f"amortized={wall_amortized:.6f} speedup={wall_speedup:.3f}x"
        )
        print(
            f"  graph_event dense={dense_graph:.6f} sparse={sparse_graph:.6f} "
            f"amortized={graph_amortized:.6f} speedup={graph_speedup:.3f}x"
        )

    floor = min(candidates)
    if floor < args.min_speedup:
        print(f"[GATE NEGATIVE] best amortized path floor={floor:.3f}x < {args.min_speedup:.2f}x")
        print("[LIMIT] memory-only sparse-master remains a separate question")
        return 8
    print(f"[GATE CANDIDATE] best amortized path floor={floor:.3f}x >= {args.min_speedup:.2f}x")
    print("[LIMIT] optimizer state, TLinear quantization, whole Transformer and quality remain NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
