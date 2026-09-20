#!/usr/bin/env python3
"""P025B Stage0bWe/Wf: separate cuSPARSELt call-path overheads.

Stage0bWe keeps the historical ``F.linear`` path and reports synchronized wall
time, consecutive CUDA Event time, host enqueue time, peak allocation, padding
at M=1, profiler rows and optional CUDA Graph replay.  Stage0bWf uses the
existing compressed weight with PyTorch's low-level ``_cslt_sparse_mm``
arguments to probe algorithm and Split-K candidates, then confirms the selected
candidate in a fresh alternating-order comparison.

This remains a synthetic FP16 GEMM diagnostic.  Packing is measured separately
and excluded from repeated GEMM timings.  CUDA Event time is not called a pure
kernel time; only profiler rows attribute individual GPU operations.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts._gpu_bench_attribution import (  # noqa: E402
    event_batch_ms,
    measure_variants,
    parse_int_csv,
    profiler_rows,
    tensor_mib,
)
from scripts.diag_sparse24_inference_attribution import (  # noqa: E402
    _agreement_ok,
    _error_stats,
)


def _parse_signed_csv(raw: str) -> list[int]:
    values: list[int] = []
    for item in raw.split(","):
        value = int(item.strip())
        if value not in values:
            values.append(value)
    if not values:
        raise ValueError("at least one integer is required")
    return values


def _parse_layouts(raw: str) -> list[str]:
    aliases = {"inference": "inference", "training": "training"}
    values = []
    for item in raw.split(","):
        name = item.strip().lower()
        if name not in aliases:
            raise ValueError("layouts must be inference and/or training")
        if name not in values:
            values.append(name)
    if not values:
        raise ValueError("at least one layout is required")
    return values


def _capture_graph(torch, fn):
    """Capture one fixed-shape callable and return (output, replay callable)."""
    side_stream = torch.cuda.Stream()
    side_stream.wait_stream(torch.cuda.current_stream())
    with torch.cuda.stream(side_stream):
        for _ in range(3):
            fn()
    torch.cuda.current_stream().wait_stream(side_stream)
    torch.cuda.synchronize()
    graph = torch.cuda.CUDAGraph()
    with torch.cuda.graph(graph):
        output = fn()

    def replay():
        graph.replay()
        return output

    return output, replay


def _print_profile(label: str, rows) -> None:
    print(f"[profile] {label} top={len(rows)}")
    for row in rows:
        print(
            "  kernel_op=" + row["key"]
            + f" calls={row['calls']} device_us={row['device_us']:.3f}"
            + f" cpu_us={row['cpu_us']:.3f}"
            + f" device_memory_MiB={row['device_memory_mib']:.3f}"
        )


def _pack(torch, sparse_cls, to_sparse, dense_weight, masked_weight):
    records = {}
    for name, builder in (
        ("inference", lambda: to_sparse(masked_weight)),
        ("training", lambda: sparse_cls.prune_dense_static_sort(dense_weight)),
    ):
        torch.cuda.synchronize()
        started = time.perf_counter()
        sparse = builder()
        torch.cuda.synchronize()
        elapsed = (time.perf_counter() - started) * 1e3
        records[name] = (sparse, elapsed)
    return records


def _dense_for_layout(layout: str, masked_weight, training_sparse):
    return masked_weight if layout == "inference" else training_sparse.to_dense()


def _raw_cslt_call(torch, sparse, x_padded, rows: int, *, alg_id: int,
                   split_k: int, split_k_mode: int):
    if sparse.packed is None:
        raise RuntimeError("selected sparse orientation has no packed tensor")
    result = torch._cslt_sparse_mm(
        sparse.packed,
        x_padded.t(),
        alg_id=alg_id,
        split_k=split_k,
        split_k_mode=split_k_mode,
    ).t()
    return result[:rows]


def _print_measurement(prefix: str, rows: dict[str, dict[str, float]]) -> None:
    print("label\twall_sync_ms\twall_MAD\tevent_batch_ms\tevent_MAD\t"
          "host_enqueue_us\thost_MAD\tpeak_delta_MiB\tpeak_MAD")
    for name, row in rows.items():
        print(
            f"{prefix}:{name}\t{row['wall']:.6f}\t{row['wall_mad']:.6f}\t"
            f"{row['event']:.6f}\t{row['event_mad']:.6f}\t"
            f"{row['host']:.3f}\t{row['host_mad']:.3f}\t"
            f"{row['peak']:.3f}\t{row['peak_mad']:.3f}"
        )


def _attribute(torch, F, sparse_cls, packs, *, k: int, n: int, m_values,
               layouts, args) -> int:
    failures = []
    for m in m_values:
        x = torch.randn(m, k, device="cuda", dtype=torch.float16)
        # The class method is the exact dispatcher helper used by PyTorch.
        x_padded = sparse_cls._pad_dense_input(x)
        if x_padded.shape != x.shape:
            pad_fn = lambda x=x: sparse_cls._pad_dense_input(x)
            pad_event = event_batch_ms(
                torch, pad_fn, warmup=args.warmup, iters=args.iters
            )
            print(
                f"[padding] M={m} padded_M={x_padded.shape[0]} "
                f"input_MiB={tensor_mib(x):.6f} padded_MiB={tensor_mib(x_padded):.6f} "
                f"pad_event_batch_ms={pad_event:.6f}; slicing is a view"
            )
        else:
            print(f"[padding] M={m} padded_M={m} pad_event_batch_ms=0")

        for layout in layouts:
            sparse, pack_ms = packs[layout]
            dense = _dense_for_layout(layout, packs["inference_dense"], packs["training"][0])
            expected = F.linear(x, dense)
            actual = F.linear(x, sparse)
            metrics = _error_stats(torch, actual, expected)
            ok = _agreement_ok(
                metrics,
                max_nrms=args.max_nrms,
                max_abs_ratio=args.max_abs_ratio,
                min_cosine=args.min_cosine,
            )
            print(
                f"[agreement] layout={layout} M={m} K={k} N={n} ok={int(ok)} "
                f"nrms={metrics['normalized_rms']:.8g} "
                f"max_abs_ratio={metrics['max_abs_ratio']:.8g} "
                f"cosine={metrics['cosine']:.9f} pack_wall_ms={pack_ms:.6f}"
            )
            if not ok:
                failures.append((layout, m, k, n))
                continue

            variants = {
                "dense": lambda x=x, dense=dense: F.linear(x, dense),
                "sparse_dispatch": lambda x=x, sparse=sparse: F.linear(x, sparse),
            }
            if x_padded.shape != x.shape:
                variants["sparse_explicit_pad"] = (
                    lambda x_padded=x_padded, sparse=sparse, m=m:
                    F.linear(x_padded, sparse)[:m]
                )
            measurements = measure_variants(
                torch,
                variants,
                rounds=args.rounds,
                warmup=args.warmup,
                iters=args.iters,
            )
            _print_measurement(f"{layout}:M{m}:K{k}:N{n}", measurements)
            dense_event = measurements["dense"]["event"]
            sparse_event = measurements["sparse_dispatch"]["event"]
            print(
                f"[ratio] layout={layout} M={m} event_dense_over_sparse="
                f"{dense_event / sparse_event:.3f}x wall_dense_over_sparse="
                f"{measurements['dense']['wall'] / measurements['sparse_dispatch']['wall']:.3f}x"
            )

            if args.profile_iters:
                for name, fn in variants.items():
                    _print_profile(
                        f"{layout}:M{m}:K{k}:N{n}:{name}",
                        profiler_rows(torch, fn, iters=args.profile_iters),
                    )

            if args.cuda_graph:
                for name in ("dense", "sparse_dispatch"):
                    try:
                        graph_output, replay = _capture_graph(torch, variants[name])
                        torch.testing.assert_close(
                            graph_output, variants[name](), rtol=2e-2, atol=2e-2
                        )
                        graph_event = event_batch_ms(
                            torch, replay, warmup=args.warmup, iters=args.iters
                        )
                        print(
                            f"[cuda_graph] layout={layout} M={m} variant={name} "
                            f"event_batch_ms={graph_event:.6f} status=OK"
                        )
                    except Exception as exc:
                        print(
                            f"[cuda_graph] layout={layout} M={m} variant={name} "
                            f"status=UNAVAILABLE reason={type(exc).__name__}: "
                            f"{str(exc).splitlines()[0]}"
                        )

    if failures:
        print(f"[GATE FAIL correctness] rows={failures}")
        return 4
    print("[ATTRIBUTION COMPLETE] wall/event/host/profiler are separate; "
          "public plan reuse remains NOT_IMPLEMENTED")
    return 0


def _tune(torch, F, sparse_cls, packs, *, k: int, n: int, m_values,
          layouts, args) -> tuple[bool, list[tuple]]:
    max_alg = torch.backends.cusparselt.get_max_alg_id()
    if args.alg_ids == "auto":
        alg_ids = list(range(max_alg)) if isinstance(max_alg, int) and max_alg > 0 else [0]
    else:
        alg_ids = parse_int_csv(args.alg_ids, minimum=0)
    split_ks = parse_int_csv(args.split_k_values, minimum=1)
    split_modes = _parse_signed_csv(args.split_k_modes)
    print(
        f"[tuning contract] backend_version={torch.backends.cusparselt.version()} "
        f"reported_max_alg_id={max_alg} alg_ids={alg_ids} split_k={split_ks} "
        f"split_k_modes={split_modes}"
    )
    if max_alg is None and args.alg_ids == "auto":
        print("[tuning limitation] local PyTorch has no max-alg mapping for this "
              "cuSPARSELt version; auto mode preserves alg0 only")

    any_candidate = False
    summaries = []
    for m in m_values:
        x = torch.randn(m, k, device="cuda", dtype=torch.float16)
        x_padded = sparse_cls._pad_dense_input(x)
        for layout in layouts:
            sparse, _pack_ms = packs[layout]
            dense = _dense_for_layout(layout, packs["inference_dense"], packs["training"][0])
            reference = F.linear(x, dense)
            dense_fn = lambda x=x, dense=dense: F.linear(x, dense)
            dense_event = event_batch_ms(
                torch, dense_fn, warmup=args.warmup, iters=args.iters
            )
            search_started = time.perf_counter()
            supported = []
            for alg_id in alg_ids:
                for split_k in split_ks:
                    modes = [-1] if split_k == 1 else split_modes
                    for split_mode in modes:
                        fn = (
                            lambda sparse=sparse, x_padded=x_padded, m=m,
                            alg_id=alg_id, split_k=split_k, split_mode=split_mode:
                            _raw_cslt_call(
                                torch, sparse, x_padded, m,
                                alg_id=alg_id, split_k=split_k,
                                split_k_mode=split_mode,
                            )
                        )
                        try:
                            output = fn()
                            metrics = _error_stats(torch, output, reference)
                            if not _agreement_ok(
                                metrics,
                                max_nrms=args.max_nrms,
                                max_abs_ratio=args.max_abs_ratio,
                                min_cosine=args.min_cosine,
                            ):
                                print(
                                    f"[tune reject correctness] layout={layout} M={m} "
                                    f"alg={alg_id} split_k={split_k} mode={split_mode} "
                                    f"nrms={metrics['normalized_rms']:.8g}"
                                )
                                continue
                            event_ms = event_batch_ms(
                                torch, fn, warmup=args.tune_warmup,
                                iters=args.tune_iters,
                            )
                            supported.append((event_ms, alg_id, split_k, split_mode, fn))
                            print(
                                f"[tune row] layout={layout} M={m} K={k} N={n} "
                                f"alg={alg_id} split_k={split_k} mode={split_mode} "
                                f"event_batch_ms={event_ms:.6f} "
                                f"dense_over_candidate={dense_event / event_ms:.3f}x"
                            )
                        except Exception as exc:
                            print(
                                f"[tune unsupported] layout={layout} M={m} alg={alg_id} "
                                f"split_k={split_k} mode={split_mode} "
                                f"reason={type(exc).__name__}: {str(exc).splitlines()[0]}"
                            )
            search_wall_ms = (time.perf_counter() - search_started) * 1e3
            if not supported:
                print(f"[tune no-supported] layout={layout} M={m} search_wall_ms={search_wall_ms:.3f}")
                summaries.append((layout, m, None, 0.0))
                continue

            supported.sort(key=lambda row: row[0])
            _, alg_id, split_k, split_mode, tuned_fn = supported[0]
            default_fn = (
                lambda sparse=sparse, x_padded=x_padded, m=m:
                _raw_cslt_call(
                    torch, sparse, x_padded, m,
                    alg_id=0, split_k=1, split_k_mode=-1,
                )
            )
            confirmed = measure_variants(
                torch,
                {"dense": dense_fn, "default_alg0": default_fn, "tuned": tuned_fn},
                rounds=args.rounds,
                warmup=args.warmup,
                iters=args.iters,
            )
            _print_measurement(f"confirm:{layout}:M{m}:K{k}:N{n}", confirmed)
            speedup = confirmed["dense"]["event"] / confirmed["tuned"]["event"]
            print(
                f"[tune selected] layout={layout} M={m} alg={alg_id} "
                f"split_k={split_k} mode={split_mode} search_wall_ms={search_wall_ms:.3f} "
                f"confirmed_event_speedup={speedup:.3f}x"
            )
            if args.profile_iters:
                _print_profile(
                    f"tuned:{layout}:M{m}:K{k}:N{n}",
                    profiler_rows(torch, tuned_fn, iters=args.profile_iters),
                )
            any_candidate |= speedup >= args.min_speedup
            summaries.append((layout, m, (alg_id, split_k, split_mode), speedup))
    return any_candidate, summaries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("attribute", "tune"), default="attribute")
    parser.add_argument("--m-values", default="1,8,128,8192")
    parser.add_argument("--layouts", default="inference,training")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--iters", type=int, default=20)
    parser.add_argument("--profile-iters", type=int, default=3)
    parser.add_argument("--cuda-graph", action="store_true")
    parser.add_argument("--alg-ids", default="auto")
    parser.add_argument("--split-k-values", default="1,2,4")
    parser.add_argument("--split-k-modes", default="0,1")
    parser.add_argument("--tune-warmup", type=int, default=3)
    parser.add_argument("--tune-iters", type=int, default=10)
    parser.add_argument("--min-speedup", type=float, default=1.10)
    parser.add_argument("--max-nrms", type=float, default=1e-3)
    parser.add_argument("--max-abs-ratio", type=float, default=1e-2)
    parser.add_argument("--min-cosine", type=float, default=0.999999)
    parser.add_argument("--require-wsl", action="store_true")
    args = parser.parse_args()

    try:
        m_values = parse_int_csv(args.m_values)
        layouts = _parse_layouts(args.layouts)
    except ValueError as exc:
        parser.error(str(exc))

    release = platform.uname().release
    distro = os.environ.get("WSL_DISTRO_NAME", "")
    is_wsl = bool(distro) or "microsoft" in release.lower()
    print(f"runtime_system={platform.system()} release={release} WSL_DISTRO_NAME={distro or '<unset>'}")
    if args.require_wsl and not is_wsl:
        print("[GATE FAIL] --require-wsl was set outside WSL")
        return 2

    import torch
    import torch.nn.functional as F
    from torch.sparse import SparseSemiStructuredTensorCUSPARSELT, to_sparse_semi_structured
    from tinylm.model.sparse_connectivity import exact_nm_mask

    try:
        package = importlib.metadata.version("nvidia-cusparselt-cu13")
    except importlib.metadata.PackageNotFoundError:
        package = "NOT_INSTALLED"
    print(
        f"torch={torch.__version__} cuda={torch.version.cuda} cudnn={torch.backends.cudnn.version()} "
        f"cusparselt_pkg={package} backend_version={torch.backends.cusparselt.version()} "
        f"compiled={bool(getattr(torch._C, '_has_cusparselt', False))} "
        f"available={torch.backends.cusparselt.is_available()}"
    )
    if not torch.cuda.is_available():
        print("[GATE FAIL] CUDA unavailable")
        return 2

    print(
        "NOTE: wall_sync includes dispatch+GPU+synchronize; event_batch includes all GPU ops; "
        "host_enqueue excludes final drain; profiler rows attribute individual ops."
    )
    all_tune_summaries = []
    tune_candidate = False
    for k, n in ((768, 2048), (2048, 768)):
        torch.manual_seed(25000 + k + n)
        dense_weight = torch.randn(n, k, device="cuda", dtype=torch.float16)
        masked_weight = dense_weight * exact_nm_mask(dense_weight, n=2, m=4)
        pack_records = _pack(
            torch,
            SparseSemiStructuredTensorCUSPARSELT,
            to_sparse_semi_structured,
            dense_weight,
            masked_weight,
        )
        packs = {
            "inference": pack_records["inference"],
            "training": pack_records["training"],
            "inference_dense": masked_weight,
        }
        print(
            f"[pack] K={k} N={n} inference_wall_ms={pack_records['inference'][1]:.6f} "
            f"training_wall_ms={pack_records['training'][1]:.6f} "
            f"inference_packed_t={pack_records['inference'][0].packed_t is not None} "
            f"training_packed_t={pack_records['training'][0].packed_t is not None}"
        )
        if args.mode == "attribute":
            code = _attribute(
                torch,
                F,
                SparseSemiStructuredTensorCUSPARSELT,
                packs,
                k=k,
                n=n,
                m_values=m_values,
                layouts=layouts,
                args=args,
            )
            if code:
                return code
        else:
            candidate, summaries = _tune(
                torch,
                F,
                SparseSemiStructuredTensorCUSPARSELT,
                packs,
                k=k,
                n=n,
                m_values=m_values,
                layouts=layouts,
                args=args,
            )
            tune_candidate |= candidate
            all_tune_summaries.extend((k, n, *row) for row in summaries)

    if args.mode == "tune":
        print(f"[tune summary] {all_tune_summaries}")
        if not tune_candidate:
            print(f"[GATE NEGATIVE] no confirmed tuned row reached {args.min_speedup:.2f}x")
            return 8
        print(f"[GATE CANDIDATE] at least one tuned row reached {args.min_speedup:.2f}x; "
              "TLinear/model integration remains NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
