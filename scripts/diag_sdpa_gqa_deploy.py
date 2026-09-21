#!/usr/bin/env python3
"""P060B Stage2W: actual-text prefill/decode GQA deployment gate."""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROMPTS = (
    "대한민국의 수도 서울은",
    "인공지능 모델의 학습 과정을 간단히 설명하면",
    "The most important trade-off in a small language model is",
)


def _median_ms(torch, fn, warmup: int, iters: int) -> float:
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


def _peak_mib(torch, fn) -> float:
    torch.cuda.synchronize()
    base = torch.cuda.memory_allocated()
    torch.cuda.reset_peak_memory_stats()
    result = fn()
    torch.cuda.synchronize()
    peak = torch.cuda.max_memory_allocated()
    del result
    return max(0, peak - base) / 2**20


def _metrics(actual, expected):
    a = actual.float().reshape(-1)
    e = expected.float().reshape(-1)
    error = a - e
    nrms = error.square().mean().sqrt() / e.square().mean().sqrt().clamp_min(1e-12)
    cosine = a.dot(e) / (a.norm() * e.norm()).clamp_min(1e-12)
    return float(error.abs().max()), float(nrms), float(cosine)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ckpt", required=True)
    parser.add_argument("--arch", choices=("dense", "tied"), required=True)
    parser.add_argument("--data", default="ko-en")
    parser.add_argument("--seqs", default="128,512,1024")
    parser.add_argument("--max-new", type=int, default=32)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--iters", type=int, default=5)
    parser.add_argument("--max-nrms", type=float, default=1e-3)
    parser.add_argument("--min-cosine", type=float, default=0.999999)
    parser.add_argument("--max-slowdown", type=float, default=1.05)
    parser.add_argument("--min-benefit", type=float, default=0.05)
    args = parser.parse_args()

    import torch
    from tinylm.data import load_tokenizer
    from tinylm.infer.generate import load_model, sample

    if not torch.cuda.is_available():
        print("[GATE FAIL] CUDA unavailable")
        return 2
    model, cfg, device = load_model(args.arch, args.ckpt, "cuda")
    tokenizer = load_tokenizer(args.data)
    seqs = [int(value) for value in args.seqs.split(",")]
    if max(seqs) > cfg.max_seq_len:
        print(f"[GATE FAIL] seq {max(seqs)} exceeds model max {cfg.max_seq_len}")
        return 2
    torch.manual_seed(6021)
    rows = []
    try:
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
            for seq in seqs:
                tokens = torch.randint(0, cfg.vocab_size, (1, seq), device=device)
                next_token = torch.randint(0, cfg.vocab_size, (1, 1), device=device)

                def prefill(enabled):
                    cfg.sdpa_gqa = enabled
                    return model(tokens, use_cache=True, logits_last_only=True)

                cfg.sdpa_gqa = False
                off_logits, off_past = prefill(False)
                cfg.sdpa_gqa = True
                on_logits, on_past = prefill(True)
                max_abs, nrms, cosine = _metrics(on_logits, off_logits)
                if nrms > args.max_nrms or cosine < args.min_cosine:
                    print(f"[GATE FAIL agreement] prefill seq={seq} nrms={nrms} cosine={cosine}")
                    return 4

                def off_prefill():
                    return prefill(False)

                def on_prefill():
                    return prefill(True)

                def decode(enabled, past):
                    cfg.sdpa_gqa = enabled
                    return model(next_token, past_kv=past, use_cache=True,
                                 logits_last_only=True)

                off_decode, _ = decode(False, off_past)
                on_decode, _ = decode(True, on_past)
                dmax, dnrms, dcos = _metrics(on_decode, off_decode)
                if dnrms > args.max_nrms or dcos < args.min_cosine:
                    print(f"[GATE FAIL agreement] decode seq={seq} nrms={dnrms} cosine={dcos}")
                    return 4

                off_p_ms = _median_ms(torch, off_prefill, args.warmup, args.iters)
                on_p_ms = _median_ms(torch, on_prefill, args.warmup, args.iters)
                off_d = lambda: decode(False, off_past)
                on_d = lambda: decode(True, on_past)
                off_d_ms = _median_ms(torch, off_d, args.warmup, args.iters)
                on_d_ms = _median_ms(torch, on_d, args.warmup, args.iters)
                off_peak = _peak_mib(torch, off_d)
                on_peak = _peak_mib(torch, on_d)
                rows.append({
                    "seq": seq,
                    "prefill_ratio": on_p_ms / off_p_ms,
                    "decode_ratio": on_d_ms / off_d_ms,
                    "peak_reduction": 1 - on_peak / max(off_peak, 1e-12),
                })
                print(
                    f"seq={seq} prefill_off_ms={off_p_ms:.6f} prefill_on_ms={on_p_ms:.6f} "
                    f"on_over_off={on_p_ms/off_p_ms:.3f}x max_abs={max_abs:.6g} "
                    f"nrms={nrms:.3e} cosine={cosine:.9f}"
                )
                print(
                    f"seq={seq} decode_off_ms={off_d_ms:.6f} decode_on_ms={on_d_ms:.6f} "
                    f"on_over_off={on_d_ms/off_d_ms:.3f} peak_off_MiB={off_peak:.3f} "
                    f"peak_on_MiB={on_peak:.3f} reduction={rows[-1]['peak_reduction']:.3%} "
                    f"nrms={dnrms:.3e} cosine={dcos:.9f}"
                )
    except RuntimeError as exc:
        print(f"[GATE FAIL backend] {type(exc).__name__}: {exc}")
        return 5

    outputs = {}
    for enabled in (False, True):
        cfg.sdpa_gqa = enabled
        outputs[enabled] = [
            sample(model, cfg, tokenizer, prompt, max_new=args.max_new,
                   temperature=0.0, top_k=1, device=device, use_cache=True,
                   stop_at_eos=False, logits_last_only=True)
            for prompt in PROMPTS
        ]
    cfg.sdpa_gqa = False
    for index, prompt in enumerate(PROMPTS):
        same = outputs[False][index] == outputs[True][index]
        print(f"text_prompt={index + 1} exact_equal={int(same)} prompt={prompt!r}")
        if not same:
            print(f"  off={outputs[False][index]!r}")
            print(f"  on ={outputs[True][index]!r}")
            return 6

    worst = max(max(row["prefill_ratio"], row["decode_ratio"]) for row in rows)
    best_speed = max(
        max(1 / row["prefill_ratio"], 1 / row["decode_ratio"]) for row in rows
    )
    best_memory = max(row["peak_reduction"] for row in rows)
    if worst > args.max_slowdown or max(best_speed - 1, best_memory) < args.min_benefit:
        print(f"[GATE NEGATIVE] worst_slowdown={worst:.3f}x best_speedup={best_speed:.3f}x "
              f"best_peak_reduction={best_memory:.3%}")
        return 8
    print(f"[GATE CANDIDATE] worst_slowdown={worst:.3f}x best_speedup={best_speed:.3f}x "
          f"best_peak_reduction={best_memory:.3%}; three greedy texts exact")
    print("[LIMIT] this is one checkpoint/seed; 300M quality training remains separate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
