#!/usr/bin/env python3
"""P060B Stage0bW: actual TinyLM checkpoint off/on default-GQA integration."""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _median_ms(torch, fn, warmup, iters):
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()
    values = []
    for _ in range(iters):
        started = time.perf_counter()
        fn()
        torch.cuda.synchronize()
        values.append((time.perf_counter() - started) * 1e3)
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


def _metrics(actual, expected):
    a, e = actual.float().reshape(-1), expected.float().reshape(-1)
    error = a - e
    ref_rms = e.square().mean().sqrt().clamp_min(1e-12)
    return (
        float(error.abs().max()),
        float(error.square().mean().sqrt() / ref_rms),
        float(a.dot(e) / (a.norm() * e.norm()).clamp_min(1e-12)),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ckpt", required=True)
    parser.add_argument("--arch", choices=["dense", "tied"], required=True)
    parser.add_argument("--seq", type=int, default=256)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--iters", type=int, default=10)
    parser.add_argument("--max-nrms", type=float, default=1e-3)
    parser.add_argument("--min-cosine", type=float, default=0.999999)
    args = parser.parse_args()

    import torch
    from tinylm.infer.generate import load_model

    if not torch.cuda.is_available():
        print("[GATE FAIL] CUDA unavailable")
        return 2
    model, cfg, device = load_model(args.arch, args.ckpt, "cuda")
    torch.manual_seed(6001)
    tokens = torch.randint(0, cfg.vocab_size, (1, args.seq), device=device)
    next_token = torch.randint(0, cfg.vocab_size, (1, 1), device=device)

    def forward(enabled, use_cache=False):
        cfg.sdpa_gqa = bool(enabled)
        return model(tokens, use_cache=use_cache, logits_last_only=True)

    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        off = forward(False)
        on = forward(True)
        off_prefill, off_past = forward(False, use_cache=True)
        on_prefill, on_past = forward(True, use_cache=True)
        cfg.sdpa_gqa = False
        off_decode, _ = model(next_token, past_kv=off_past, use_cache=True,
                              logits_last_only=True)
        cfg.sdpa_gqa = True
        on_decode, _ = model(next_token, past_kv=on_past, use_cache=True,
                             logits_last_only=True)

    rows = {
        "full_forward": _metrics(on, off),
        "cache_prefill": _metrics(on_prefill, off_prefill),
        "cache_decode": _metrics(on_decode, off_decode),
    }
    print("path\tmax_abs\tnrms\tcosine")
    failures = []
    for name, (max_abs, nrms, cosine) in rows.items():
        print(f"{name}\t{max_abs:.6g}\t{nrms:.6g}\t{cosine:.9f}")
        if nrms > args.max_nrms or cosine < args.min_cosine:
            failures.append(name)

    def off_call():
        cfg.sdpa_gqa = False
        return model(tokens, logits_last_only=True)

    def on_call():
        cfg.sdpa_gqa = True
        return model(tokens, logits_last_only=True)

    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        off_ms = _median_ms(torch, off_call, args.warmup, args.iters)
        on_ms = _median_ms(torch, on_call, args.warmup, args.iters)
        off_peak = _peak_mib(torch, off_call)
        on_peak = _peak_mib(torch, on_call)
    print(f"timing off_ms={off_ms:.6f} on_ms={on_ms:.6f} "
          f"on_over_off={on_ms/off_ms:.3f}x")
    print(f"allocation off_peak_MiB={off_peak:.3f} on_peak_MiB={on_peak:.3f} "
          f"reduction={(1-on_peak/max(off_peak,1e-12)):.3%}")
    cfg.sdpa_gqa = False
    if failures:
        print(f"[GATE FAIL] model-path agreement failures={failures}")
        return 4
    print("[PASS] P060B Stage0bW: actual checkpoint full/prefill/decode agreement; "
          "timing and allocation recorded")
    print("NOTE: default remains off; backward, training step and quality remain NOT_RUN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
