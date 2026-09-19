#!/usr/bin/env python3
"""P022C C1: BF16 vs FP8 current/delayed scaling including cast overhead."""
from __future__ import annotations

import argparse
import os
import platform
import statistics
import time


def _median_ms(torch, fn, warmup, iters):
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()
    values = []
    for _ in range(iters):
        start = time.perf_counter()
        fn()
        torch.cuda.synchronize()
        values.append((time.perf_counter() - start) * 1e3)
    return statistics.median(values)


def _peak_mib(torch, fn):
    torch.cuda.synchronize()
    base = torch.cuda.memory_allocated()
    torch.cuda.reset_peak_memory_stats()
    output = fn()
    torch.cuda.synchronize()
    peak = torch.cuda.max_memory_allocated()
    del output
    return max(0, peak - base) / 2**20


def _metrics(torch, actual, reference):
    actual = actual.float().reshape(-1)
    reference = reference.float().reshape(-1)
    error = actual - reference
    ref_rms = reference.square().mean().sqrt().clamp_min(1e-12)
    nrms = error.square().mean().sqrt() / ref_rms
    cosine = actual.dot(reference) / (actual.norm() * reference.norm()).clamp_min(1e-12)
    return float(error.abs().max()), float(nrms), float(cosine)


def _gate_decision(rows, *, min_speedup, max_nrms, min_cosine):
    """Return a scientific gate result, never an execution-failure code."""
    numeric = [
        row for row in rows
        if row["nrms"] > max_nrms or row["cosine"] < min_cosine
    ]
    candidates = [row for row in rows if row["speedup"] >= min_speedup]
    if not candidates:
        return 8, "no speed candidate", numeric, candidates
    if numeric:
        return 8, "speed candidate failed numerical screen", numeric, candidates
    return 0, "speed and numerical candidate", numeric, candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m", type=int, default=8192)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--iters", type=int, default=30)
    parser.add_argument("--min-speedup", type=float, default=1.10)
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
    print(f"gpu={torch.cuda.get_device_name()} sm={torch.cuda.get_device_capability()} "
          f"torch={torch.__version__} warmup={args.warmup} iters={args.iters}")
    print("NOTE: forward includes absmax/scale/cast for current scaling and cast for delayed scaling; "
          "backward and whole training step remain NOT_RUN.")
    print("K\tN\tvariant\tms\tspeedup\tpeak_MiB\tmax_abs\tnrms\tcosine")

    fp8_rows = []
    for k, n in ((768, 2048), (2048, 768), (768, 768)):
        torch.manual_seed(22000 + k + n)
        x = torch.randn(args.m, k, device="cuda", dtype=torch.bfloat16)
        weight = torch.randn(n, k, device="cuda", dtype=torch.bfloat16)
        reference = F.linear(x, weight)

        delayed_sx = (448.0 / x.abs().amax().clamp_min(1e-8)).float()
        delayed_sw = (448.0 / weight.abs().amax().clamp_min(1e-8)).float()

        def bf16():
            return F.linear(x, weight)

        def scaled_mm(sx, sw):
            xq = (x * sx).to(torch.float8_e4m3fn)
            wq = (weight * sw).to(torch.float8_e4m3fn).t()
            return torch._scaled_mm(
                xq, wq, scale_a=(1.0 / sx).reshape(1),
                scale_b=(1.0 / sw).reshape(1), out_dtype=torch.bfloat16,
            )

        def current():
            sx = (448.0 / x.abs().amax().clamp_min(1e-8)).float()
            sw = (448.0 / weight.abs().amax().clamp_min(1e-8)).float()
            return scaled_mm(sx, sw)

        def delayed():
            return scaled_mm(delayed_sx, delayed_sw)

        baseline_ms = _median_ms(torch, bf16, args.warmup, args.iters)
        for name, fn in (("bf16", bf16), ("fp8_current", current), ("fp8_delayed", delayed)):
            try:
                output = fn()
                ms = baseline_ms if name == "bf16" else _median_ms(
                    torch, fn, args.warmup, args.iters
                )
                peak = _peak_mib(torch, fn)
            except Exception as exc:
                print(f"[GATE FAIL runtime] K={k} N={n} {name}: {type(exc).__name__}: {exc}")
                return 3
            max_abs, nrms, cosine = _metrics(torch, output, reference)
            speedup = baseline_ms / ms
            print(f"{k}\t{n}\t{name}\t{ms:.6f}\t{speedup:.3f}\t{peak:.3f}\t"
                  f"{max_abs:.6g}\t{nrms:.6g}\t{cosine:.9f}")
            if name != "bf16":
                fp8_rows.append({
                    "k": k, "n": n, "name": name, "speedup": speedup,
                    "nrms": nrms, "cosine": cosine, "peak_mib": peak,
                })

    code, reason, numeric, candidates = _gate_decision(
        fp8_rows, min_speedup=args.min_speedup,
        max_nrms=args.max_nrms, min_cosine=args.min_cosine,
    )
    if numeric:
        print("[NUMERIC SCREEN] " + repr([
            (row["k"], row["n"], row["name"], row["nrms"], row["cosine"])
            for row in numeric
        ]))
    if code:
        best = max((row["speedup"] for row in fp8_rows), default=0.0)
        print(f"[GATE NEGATIVE] {reason}; best cast/scaling-inclusive speedup={best:.3f}x, "
              "no Stage C2 quality run is opened")
        return code
    print(f"[GATE CANDIDATE] {len(candidates)} shape/path pairs reached "
          f"{args.min_speedup:.2f}x: {candidates}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
