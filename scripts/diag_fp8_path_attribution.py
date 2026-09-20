#!/usr/bin/env python3
"""P022C Stage0bWc: attribute FP8 scaling, cast and cached-weight costs.

Five forward paths are compared with identical shapes and measurement methods:

``A`` BF16 baseline; ``B`` prepared FP8 GEMM; ``C`` cached FP8 weight with an
activation cast each call; ``D`` historical delayed scaling; and ``E``
historical current scaling.  Weight caching is synthetic-forward-only: this
script does not add a cache to TLinear or change training semantics.
"""
from __future__ import annotations

import argparse
import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts._gpu_bench_attribution import (  # noqa: E402
    event_batch_ms,
    measure_variants,
    profiler_rows,
)
from scripts.diag_fp8_scaling_overhead import _metrics  # noqa: E402


def _bytes_to_mib(value: int) -> float:
    return value / 2**20


def _fp8_tensor_ledger(m: int, k: int, n: int) -> dict[str, dict[str, int]]:
    """Logical extra bytes and lifetimes beyond shared BF16 x/weight tensors."""
    bf16_x = m * k * 2
    bf16_w = n * k * 2
    fp8_x = m * k
    fp8_w = n * k
    bf16_out = m * n * 2
    scalar_pair = 2 * 4
    return {
        "A_bf16": {
            "persistent": 0,
            "per_call_temporaries": bf16_out,
        },
        "B_prepared_fp8": {
            "persistent": fp8_x + fp8_w + scalar_pair,
            "per_call_temporaries": bf16_out,
        },
        "C_weight_cached": {
            "persistent": fp8_w + scalar_pair,
            "per_call_temporaries": bf16_x + fp8_x + bf16_out,
        },
        "D_delayed": {
            "persistent": scalar_pair,
            "per_call_temporaries": bf16_x + fp8_x + bf16_w + fp8_w + bf16_out,
        },
        "E_current": {
            "persistent": 0,
            "per_call_temporaries": bf16_x + fp8_x + bf16_w + fp8_w + bf16_out + scalar_pair,
        },
    }


def _print_profile(label: str, rows) -> None:
    print(f"[profile] {label} top={len(rows)}")
    for row in rows:
        print(
            "  kernel_op=" + row["key"]
            + f" calls={row['calls']} device_us={row['device_us']:.3f}"
            + f" cpu_us={row['cpu_us']:.3f}"
            + f" device_memory_MiB={row['device_memory_mib']:.3f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m", type=int, default=8192)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--iters", type=int, default=20)
    parser.add_argument("--profile-iters", type=int, default=3)
    parser.add_argument("--min-speedup", type=float, default=1.10)
    parser.add_argument("--max-memory-ratio", type=float, default=1.00)
    parser.add_argument("--max-nrms", type=float, default=0.03)
    parser.add_argument("--min-cosine", type=float, default=0.999)
    parser.add_argument("--require-wsl", action="store_true")
    args = parser.parse_args()

    release = platform.uname().release
    distro = os.environ.get("WSL_DISTRO_NAME", "")
    is_wsl = bool(distro) or "microsoft" in release.lower()
    print(f"runtime={platform.system()} release={release} WSL_DISTRO_NAME={distro or '<unset>'}")
    if args.require_wsl and not is_wsl:
        print("[GATE FAIL] WSL required")
        return 2

    import torch
    import torch.nn.functional as F

    if not torch.cuda.is_available() or not hasattr(torch, "_scaled_mm"):
        print("[GATE FAIL] CUDA FP8 _scaled_mm unavailable")
        return 2
    print(
        f"gpu={torch.cuda.get_device_name()} sm={torch.cuda.get_device_capability()} "
        f"torch={torch.__version__} rounds={args.rounds} warmup={args.warmup} "
        f"iters={args.iters}"
    )
    print(
        "NOTE: wall_sync includes dispatch+GPU+synchronize; event_batch includes every GPU op "
        "in the callable and is not a pure GEMM label; profiler rows attribute individual ops."
    )

    c_candidates = []
    all_numeric_ok = True
    for k, n in ((768, 2048), (2048, 768), (768, 768)):
        torch.manual_seed(22100 + k + n)
        x = torch.randn(args.m, k, device="cuda", dtype=torch.bfloat16)
        weight = torch.randn(n, k, device="cuda", dtype=torch.bfloat16)
        reference = F.linear(x, weight)

        sx = (448.0 / x.abs().amax().clamp_min(1e-8)).float()
        sw = (448.0 / weight.abs().amax().clamp_min(1e-8)).float()
        inv_sx = (1.0 / sx).reshape(1)
        inv_sw = (1.0 / sw).reshape(1)
        xq_cached = (x * sx).to(torch.float8_e4m3fn)
        wq_cached_t = (weight * sw).to(torch.float8_e4m3fn).t()

        def scaled(xq, wq_t, ax, bw):
            return torch._scaled_mm(
                xq,
                wq_t,
                scale_a=ax,
                scale_b=bw,
                out_dtype=torch.bfloat16,
            )

        def a_bf16():
            return F.linear(x, weight)

        def b_prepared():
            return scaled(xq_cached, wq_cached_t, inv_sx, inv_sw)

        def c_weight_cached():
            xq = (x * sx).to(torch.float8_e4m3fn)
            return scaled(xq, wq_cached_t, inv_sx, inv_sw)

        def d_delayed():
            xq = (x * sx).to(torch.float8_e4m3fn)
            wq_t = (weight * sw).to(torch.float8_e4m3fn).t()
            return scaled(xq, wq_t, (1.0 / sx).reshape(1), (1.0 / sw).reshape(1))

        def e_current():
            current_sx = (448.0 / x.abs().amax().clamp_min(1e-8)).float()
            current_sw = (448.0 / weight.abs().amax().clamp_min(1e-8)).float()
            xq = (x * current_sx).to(torch.float8_e4m3fn)
            wq_t = (weight * current_sw).to(torch.float8_e4m3fn).t()
            return scaled(
                xq,
                wq_t,
                (1.0 / current_sx).reshape(1),
                (1.0 / current_sw).reshape(1),
            )

        variants = {
            "A_bf16": a_bf16,
            "B_prepared_fp8": b_prepared,
            "C_weight_cached": c_weight_cached,
            "D_delayed": d_delayed,
            "E_current": e_current,
        }
        measurements = measure_variants(
            torch,
            variants,
            rounds=args.rounds,
            warmup=args.warmup,
            iters=args.iters,
        )
        ledger = _fp8_tensor_ledger(args.m, k, n)
        baseline_wall = measurements["A_bf16"]["wall"]
        baseline_event = measurements["A_bf16"]["event"]
        baseline_peak = measurements["A_bf16"]["peak"]
        print(f"[shape] M={args.m} K={k} N={n}")
        print(
            "variant\twall_sync_ms\twall_MAD\tevent_batch_ms\tevent_MAD\t"
            "host_enqueue_us\thost_MAD\tpeak_delta_MiB\tpersistent_MiB\t"
            "working_MiB\twall_speedup\tevent_speedup\tmax_abs\tnrms\tcosine\t"
            "speed_ok\tmemory_ok\tnumeric_ok"
        )
        for name, fn in variants.items():
            row = measurements[name]
            persistent_mib = _bytes_to_mib(ledger[name]["persistent"])
            working_mib = persistent_mib + row["peak"]
            output = fn()
            max_abs, nrms, cosine = _metrics(torch, output, reference)
            speedup = baseline_wall / row["wall"]
            event_speedup = baseline_event / row["event"]
            speed_ok = speedup >= args.min_speedup
            memory_ok = working_mib <= baseline_peak * args.max_memory_ratio
            numeric_ok = nrms <= args.max_nrms and cosine >= args.min_cosine
            all_numeric_ok &= name == "A_bf16" or numeric_ok
            print(
                f"{name}\t{row['wall']:.6f}\t{row['wall_mad']:.6f}\t"
                f"{row['event']:.6f}\t{row['event_mad']:.6f}\t"
                f"{row['host']:.3f}\t{row['host_mad']:.3f}\t"
                f"{row['peak']:.3f}\t{persistent_mib:.3f}\t{working_mib:.3f}\t"
                f"{speedup:.3f}\t{event_speedup:.3f}\t{max_abs:.6g}\t"
                f"{nrms:.8g}\t{cosine:.9f}\t{int(speed_ok)}\t"
                f"{int(memory_ok)}\t{int(numeric_ok)}"
            )
            print(
                f"[lifetime] variant={name} persistent_extra_MiB={persistent_mib:.3f} "
                f"logical_per_call_temporaries_MiB="
                f"{_bytes_to_mib(ledger[name]['per_call_temporaries']):.3f}"
            )
            if name == "C_weight_cached":
                c_candidates.append((k, n, speed_ok, memory_ok, numeric_ok, speedup))
            if args.profile_iters:
                _print_profile(
                    f"M{args.m}:K{k}:N{n}:{name}",
                    profiler_rows(torch, fn, iters=args.profile_iters),
                )

        components = {
            "x_absmax_scale": lambda: (448.0 / x.abs().amax().clamp_min(1e-8)).float(),
            "w_absmax_scale": lambda: (448.0 / weight.abs().amax().clamp_min(1e-8)).float(),
            "x_scale_cast": lambda: (x * sx).to(torch.float8_e4m3fn),
            "w_scale_cast": lambda: (weight * sw).to(torch.float8_e4m3fn),
            "prepared_scaled_mm": b_prepared,
        }
        for name, fn in components.items():
            component_ms = event_batch_ms(
                torch, fn, warmup=args.warmup, iters=args.iters
            )
            print(f"[component] M={args.m} K={k} N={n} name={name} "
                  f"event_batch_ms={component_ms:.6f}")

    passed = [row for row in c_candidates if row[2] and row[3] and row[4]]
    print(f"[independent summary] C_weight_cached rows={c_candidates}")
    if not passed:
        reason = "speed/memory/numeric gates did not all pass on any shape"
        if not all_numeric_ok:
            reason += "; FP8 numerical screen remains negative"
        print(f"[GATE NEGATIVE] {reason}; TLinear cache integration remains NOT_RUN")
        return 8
    print(f"[GATE CANDIDATE] {len(passed)} cached-weight row(s) passed all gates; "
          "TLinear cache invalidation/backward remain NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
