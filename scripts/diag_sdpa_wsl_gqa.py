#!/usr/bin/env python3
"""P060B: WSL-native SDPA GQA backend correctness, speed and memory gate."""
from __future__ import annotations

import argparse
import importlib.metadata
import os
import platform
import statistics
import time
import warnings


def _median_ms(torch, fn, warmup: int, iters: int) -> float:
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


def _peak_delta_mib(torch, fn) -> float:
    torch.cuda.synchronize()
    baseline = torch.cuda.memory_allocated()
    torch.cuda.reset_peak_memory_stats()
    output = fn()
    torch.cuda.synchronize()
    peak = torch.cuda.max_memory_allocated()
    del output
    return max(0, peak - baseline) / 2**20


def _version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "NOT_INSTALLED"


def _eligible(rows, baseline: str, candidates, max_speed_ratio: float,
              min_memory_reduction: float):
    if baseline not in rows:
        return []
    base_ms, base_memory, *_ = rows[baseline]
    selected = []
    for name in candidates:
        if name not in rows:
            continue
        speed_ratio = rows[name][0] / base_ms
        memory_reduction = 1.0 - rows[name][1] / base_memory
        if speed_ratio <= max_speed_ratio and memory_reduction >= min_memory_reduction:
            selected.append((name, speed_ratio, memory_reduction))
    return selected


def _grouped_broadcast_inputs(q, k, v):
    """Represent GQA as an extra batch group with zero-stride K/V views."""
    batch, q_heads, q_seq, dim = q.shape
    kv_heads, kv_seq = k.shape[1], k.shape[2]
    if q_heads % kv_heads:
        raise ValueError(f"q_heads={q_heads} is not divisible by kv_heads={kv_heads}")
    group = q_heads // kv_heads
    q_grouped = q.reshape(batch, kv_heads, group, q_seq, dim)
    k_grouped = k.unsqueeze(2).expand(batch, kv_heads, group, kv_seq, dim)
    v_grouped = v.unsqueeze(2).expand(batch, kv_heads, group, kv_seq, dim)
    return q_grouped, k_grouped, v_grouped


def _unique_storage_mib(*tensors):
    """Count physical tensor storages once; expanded views must not look materialized."""
    storages = {}
    for tensor in tensors:
        storage = tensor.untyped_storage()
        storages[storage.data_ptr()] = storage.nbytes()
    return sum(storages.values()) / 2**20


def _captured_call(fn):
    """Capture backend-selection diagnostics without flooding the run log."""
    caught = []
    result = None
    error = None
    try:
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")
            result = fn()
        caught = [str(record.message).split("(Triggered internally", 1)[0].strip()
                  for record in records]
    except Exception as exc:  # backend probe must preserve the local runtime reason
        error = exc
        caught = [str(record.message).split("(Triggered internally", 1)[0].strip()
                  for record in records]
    return result, list(dict.fromkeys(caught)), error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--iters", type=int, default=20)
    parser.add_argument("--require-wsl", action="store_true")
    parser.add_argument("--max-speed-ratio", type=float, default=1.05)
    parser.add_argument("--min-memory-reduction", type=float, default=0.10)
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
    from torch.nn.attention import SDPBackend, sdpa_kernel

    print(f"torch={torch.__version__} cuda={torch.version.cuda} "
          f"cudnn={torch.backends.cudnn.version()} triton={_version('triton')} "
          f"flash-attn={_version('flash-attn')}")
    if not torch.cuda.is_available():
        print("[GATE FAIL] CUDA unavailable")
        return 2
    capability = torch.cuda.get_device_capability()
    print(f"gpu={torch.cuda.get_device_name()} sm_{capability[0]}{capability[1]}")
    print("NOTE: PyTorch native SDPA backends are probed; external flash-attn is not required.")

    variants = (
        ("off_default", None, False, False),
        ("on_default", None, True, False),
        ("on_cudnn", SDPBackend.CUDNN_ATTENTION, True, False),
        ("on_flash", SDPBackend.FLASH_ATTENTION, True, False),
        ("on_efficient", SDPBackend.EFFICIENT_ATTENTION, True, False),
        # Local torch 2.10 rejects dense Hq=12/Hkv=3 in the direct efficient path.
        # Preserve that result, then separately test PyTorch's suggested grouped
        # singleton broadcast without materializing K/V repeats.
        ("on_efficient_broadcast", SDPBackend.EFFICIENT_ATTENTION, False, True),
    )
    primary_candidate = False
    for shape_index, (batch, seq) in enumerate(((8, 1024), (1, 128))):
        torch.manual_seed(6000 + batch + seq)
        q = torch.randn(batch, 12, seq, 64, device="cuda", dtype=torch.bfloat16)
        k = torch.randn(batch, 3, seq, 64, device="cuda", dtype=torch.bfloat16)
        v = torch.randn(batch, 3, seq, 64, device="cuda", dtype=torch.bfloat16)
        k_rep = k.repeat_interleave(4, dim=1)
        v_rep = v.repeat_interleave(4, dim=1)
        with sdpa_kernel(SDPBackend.MATH):
            reference = F.scaled_dot_product_attention(q, k_rep, v_rep, is_causal=True)

        rows = {}
        print(f"[shape] batch={batch} seq={seq} q_heads=12 kv_heads=3 head_dim=64 bf16")
        print("variant\tstatus\tms\tvs_off\tworking_MiB\tmemory_reduction\tmax_abs\trms")
        for name, backend, gqa, grouped_broadcast in variants:
            if grouped_broadcast:
                query, key, value = _grouped_broadcast_inputs(q, k, v)
            else:
                query = q
                key, value = (k, v) if gqa else (k_rep, v_rep)

            def call(backend=backend, gqa=gqa, query=query, key=key, value=value,
                     grouped_broadcast=grouped_broadcast):
                if backend is None:
                    result = F.scaled_dot_product_attention(
                        query, key, value, is_causal=True, enable_gqa=gqa
                    )
                else:
                    with sdpa_kernel(backend):
                        result = F.scaled_dot_product_attention(
                            query, key, value, is_causal=True, enable_gqa=gqa
                        )
                return result.reshape_as(q) if grouped_broadcast else result

            output, backend_warnings, backend_error = _captured_call(call)
            if backend_error is not None:
                diagnostic = " | ".join(backend_warnings) or "no backend diagnostic"
                print(f"{name}\tUNAVAILABLE\t-\t-\t-\t-\t-\t-\t"
                      f"{type(backend_error).__name__}: {str(backend_error).splitlines()[0]}; "
                      f"diagnostic={diagnostic}")
                continue
            if backend_warnings:
                print(f"[BACKEND WARNING] variant={name} diagnostic="
                      + " | ".join(backend_warnings))
            delta = (output.float() - reference.float()).abs()
            max_abs = float(delta.max())
            rms = float(delta.square().mean().sqrt())
            try:
                torch.testing.assert_close(output, reference, rtol=5e-2, atol=5e-2)
            except AssertionError as exc:
                print(f"[GATE FAIL correctness] variant={name} batch={batch} seq={seq} "
                      f"max_abs={max_abs:.6g} rms={rms:.6g}; "
                      f"{str(exc).splitlines()[0]}")
                return 4
            try:
                def quiet_call():
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        return call()

                ms = _median_ms(torch, quiet_call, args.warmup, args.iters)
                peak_delta = _peak_delta_mib(torch, quiet_call)
                input_mib = _unique_storage_mib(query, key, value)
                working_mib = input_mib + peak_delta
                rows[name] = (ms, working_mib, max_abs, rms)
            except Exception as exc:
                print(f"[GATE FAIL timing] variant={name} batch={batch} seq={seq}: "
                      f"{type(exc).__name__}: {str(exc).splitlines()[0]}")
                return 5
            off = rows.get("off_default")
            ratio = ms / off[0] if off else 1.0
            reduction = 1.0 - working_mib / off[1] if off else 0.0
            print(f"{name}\tOK\t{ms:.4f}\t{ratio:.3f}x\t{working_mib:.3f}\t"
                  f"{reduction:.3%}\t{max_abs:.6g}\t{rms:.6g}")

        if "off_default" not in rows:
            print("[GATE FAIL] off_default baseline unavailable")
            return 3
        default_eligible = _eligible(
            rows, "off_default", ("on_default",),
            args.max_speed_ratio, args.min_memory_reduction,
        )
        forced_eligible = _eligible(
            rows, "off_default", (
                "on_cudnn", "on_flash", "on_efficient", "on_efficient_broadcast"
            ),
            args.max_speed_ratio, args.min_memory_reduction,
        )
        if default_eligible:
            print("[DEFAULT CANDIDATE] " + ", ".join(
                f"{name} speed={ratio:.3f}x memory={reduction:.1%}"
                for name, ratio, reduction in default_eligible
            ))
        if forced_eligible:
            print("[FORCED CANDIDATE] " + ", ".join(
                f"{name} speed={ratio:.3f}x memory={reduction:.1%}"
                for name, ratio, reduction in forced_eligible
            ))
        if not forced_eligible:
            print(f"[SHAPE NEGATIVE] no forced GQA backend met speed<=+"
                  f"{(args.max_speed_ratio - 1.0):.0%} and memory reduction>="
                  f"{args.min_memory_reduction:.0%}")
        if shape_index == 0 and (default_eligible or forced_eligible):
            primary_candidate = True

    if not primary_candidate:
        print("[GATE NEGATIVE] standard B8/T1024 shape has no practical default or forced GQA candidate")
        return 8
    print("[GATE CANDIDATE] WSL dispatcher-selected or forced GQA passed the practical "
          "micro-gate; backend identity and integration remain NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
