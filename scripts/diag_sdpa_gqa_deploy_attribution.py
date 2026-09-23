#!/usr/bin/env python3
"""P060B Stage2b: attribute cached GQA drift without changing Stage2W limits.

User-run GPU diagnostic. It collects all requested lengths and distinguishes
prefill-cache drift from the decode-kernel change using four crossed paths.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from diag_sdpa_gqa_deploy import PROMPTS, _median_ms, _metrics, _peak_mib


def _capture_attention(model, fn):
    outputs = {}
    handles = []
    for index, layer in enumerate(model.layers):
        def capture(_module, _inputs, value, layer_index=index):
            outputs[layer_index] = value.detach()
        handles.append(layer.attn_mod.register_forward_hook(capture))
    try:
        result = fn()
    finally:
        for handle in handles:
            handle.remove()
    return result, outputs


def _compare(torch, label, actual, reference, limit, cosine_floor):
    maximum, nrms, cosine = _metrics(actual, reference)
    same_token = bool(torch.equal(actual.argmax(-1), reference.argmax(-1)))
    passed = nrms <= limit and cosine >= cosine_floor
    print(
        f"path={label} max_abs={maximum:.8g} nrms={nrms:.9g} "
        f"cosine={cosine:.9g} argmax_equal={int(same_token)} "
        f"agreement={'PASS' if passed else 'FAIL'}"
    )
    return passed


def _cache_difference(torch, off_cache, on_cache, seq):
    if off_cache.keys() != on_cache.keys():
        raise RuntimeError(f"seq={seq} cache owner keys differ")
    worst = 0.0
    for owner in sorted(off_cache, key=str):
        for channel, left, right in zip(("k", "v"), off_cache[owner], on_cache[owner]):
            maximum, nrms, cosine = _metrics(right, left)
            worst = max(worst, nrms)
            print(
                f"cache seq={seq} owner={owner} part={channel} "
                f"max_abs={maximum:.8g} nrms={nrms:.9g} cosine={cosine:.9g}"
            )
    return worst


def _first_layer_difference(torch, reference, candidate, limit, cosine_floor):
    if reference.keys() != candidate.keys():
        raise RuntimeError("attention layer capture keys differ")
    for layer_index in sorted(reference):
        maximum, nrms, cosine = _metrics(candidate[layer_index], reference[layer_index])
        if nrms > limit or cosine < cosine_floor:
            print(
                f"first_attention_divergence layer={layer_index} "
                f"max_abs={maximum:.8g} nrms={nrms:.9g} cosine={cosine:.9g}"
            )
            return layer_index
    print("first_attention_divergence none_above_registered_limit")
    return None


def gate_status(*, backend_failed, agreement_failed, text_failed,
                ratios, reductions, slowdown_limit, min_benefit):
    """Return 5=runtime error, 4=agreement error, 8=valid speed/memory negative."""
    if backend_failed:
        return 5
    if agreement_failed or text_failed:
        return 4
    if not ratios:
        return 4
    worst = max(ratios)
    best_speed = max(1.0 / value for value in ratios)
    best_memory = max(reductions, default=0.0)
    if worst > slowdown_limit or max(best_speed - 1.0, best_memory) < min_benefit:
        return 8
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ckpt", required=True)
    parser.add_argument("--arch", choices=("dense", "tied"), required=True)
    parser.add_argument("--data", default="ko-en")
    parser.add_argument("--seqs", default="128,512,1023,1024")
    parser.add_argument("--max-new", type=int, default=32)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--iters", type=int, default=5)
    parser.add_argument("--max-nrms", type=float, default=0.001)
    parser.add_argument("--min-cosine", type=float, default=0.999999)
    parser.add_argument("--max-slowdown", type=float, default=1.05)
    parser.add_argument("--min-benefit", type=float, default=0.05)
    args = parser.parse_args()
    seqs = [int(item) for item in args.seqs.split(",")]
    if not seqs or min(seqs) < 1 or len(seqs) != len(set(seqs)):
        parser.error("--seqs needs distinct positive lengths")
    if min(args.warmup, args.iters, args.max_new) < 1:
        parser.error("--warmup, --iters and --max-new must be positive")

    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from tinylm.data import load_tokenizer
    from tinylm.infer.generate import load_model, sample

    if not torch.cuda.is_available():
        print("[GATE FAIL runtime] CUDA unavailable")
        return 2
    model, cfg, device = load_model(args.arch, args.ckpt, "cuda")
    tokenizer = load_tokenizer(args.data)
    if max(seqs) > cfg.max_seq_len:
        print(f"[GATE FAIL shape] maximum seq={max(seqs)} > context={cfg.max_seq_len}")
        return 2
    torch.manual_seed(6022)
    agreement_failed = False
    backend_failed = False
    text_failed = False
    ratios = []
    reductions = []
    for seq in seqs:
        try:
            tokens = torch.randint(0, cfg.vocab_size, (1, seq), device=device)
            next_token = torch.randint(0, cfg.vocab_size, (1, 1), device=device)
            can_decode = seq + 1 <= cfg.max_seq_len
            for precision in ("bf16", "fp32_math"):
                autocast = (
                    torch.autocast("cuda", dtype=torch.bfloat16)
                    if precision == "bf16" else torch.autocast("cuda", enabled=False)
                )
                kernel = nullcontext() if precision == "bf16" else sdpa_kernel([SDPBackend.MATH])
                old_tf32 = torch.backends.cuda.matmul.allow_tf32
                if precision == "fp32_math":
                    torch.backends.cuda.matmul.allow_tf32 = False
                try:
                    with torch.no_grad(), autocast, kernel:
                        def prefill(enabled):
                            cfg.sdpa_gqa = enabled
                            return model(tokens, use_cache=True, logits_last_only=True)

                        def decode(enabled, past):
                            cfg.sdpa_gqa = enabled
                            return model(next_token, past_kv=past, use_cache=True,
                                         logits_last_only=True)

                        (off_logits, off_cache), _ = _capture_attention(model, lambda: prefill(False))
                        (on_logits, on_cache), _ = _capture_attention(model, lambda: prefill(True))
                        print(f"shape seq={seq} precision={precision} decode_supported={int(can_decode)}")
                        passed = _compare(
                            torch, "prefill_on_vs_off", on_logits, off_logits,
                            args.max_nrms, args.min_cosine,
                        )
                        if precision == "bf16":
                            agreement_failed |= not passed
                        _cache_difference(torch, off_cache, on_cache, seq)
                        if not can_decode:
                            if precision == "bf16":
                                off_p = _median_ms(torch, lambda: prefill(False), args.warmup, args.iters)
                                on_p = _median_ms(torch, lambda: prefill(True), args.warmup, args.iters)
                                prefill_ratio = on_p / off_p
                                ratios.append(prefill_ratio)
                                print(f"timing seq={seq} prefill_on_over_off={prefill_ratio:.4f}")
                            print(f"[NOT_RUN] seq={seq} decode exceeds context={cfg.max_seq_len}")
                            continue

                        (off_off, _), off_layers = _capture_attention(
                            model, lambda: decode(False, off_cache)
                        )
                        (on_off, _), on_off_layers = _capture_attention(
                            model, lambda: decode(True, off_cache)
                        )
                        (off_on, _), off_on_layers = _capture_attention(
                            model, lambda: decode(False, on_cache)
                        )
                        (on_on, _), _ = _capture_attention(
                            model, lambda: decode(True, on_cache)
                        )
                        print("paths: off_off=off-cache/off-decode; on_off=off-cache/on-decode")
                        print("paths: off_on=on-cache/off-decode; on_on=on-cache/on-decode")
                        for name, value in (
                            ("on_off_vs_off_off", on_off),
                            ("off_on_vs_off_off", off_on),
                            ("on_on_vs_off_off", on_on),
                        ):
                            passed = _compare(
                                torch, name, value, off_off,
                                args.max_nrms, args.min_cosine,
                            )
                            if precision == "bf16" and name == "on_on_vs_off_off":
                                agreement_failed |= not passed
                        print(f"layer_attribution seq={seq} precision={precision} decode_only")
                        _first_layer_difference(
                            torch, off_layers, on_off_layers,
                            args.max_nrms, args.min_cosine,
                        )
                        print(f"layer_attribution seq={seq} precision={precision} cache_only")
                        _first_layer_difference(
                            torch, off_layers, off_on_layers,
                            args.max_nrms, args.min_cosine,
                        )
                        if precision == "bf16":
                            off_p = _median_ms(torch, lambda: prefill(False), args.warmup, args.iters)
                            on_p = _median_ms(torch, lambda: prefill(True), args.warmup, args.iters)
                            off_d = _median_ms(
                                torch, lambda: decode(False, off_cache), args.warmup, args.iters
                            )
                            on_d = _median_ms(
                                torch, lambda: decode(True, off_cache), args.warmup, args.iters
                            )
                            off_peak = _peak_mib(torch, lambda: decode(False, off_cache))
                            on_peak = _peak_mib(torch, lambda: decode(True, off_cache))
                            prefill_ratio = on_p / off_p
                            decode_ratio = on_d / off_d
                            reduction = 1.0 - on_peak / max(off_peak, 1e-12)
                            ratios.extend((prefill_ratio, decode_ratio))
                            reductions.append(reduction)
                            print(
                                f"timing seq={seq} prefill_on_over_off={prefill_ratio:.4f} "
                                f"decode_on_over_off_same_cache={decode_ratio:.4f} "
                                f"decode_peak_reduction={reduction:.3%}"
                            )
                finally:
                    cfg.sdpa_gqa = False
                    torch.backends.cuda.matmul.allow_tf32 = old_tf32
        except (RuntimeError, NotImplementedError) as exc:
            backend_failed = True
            print(f"[GATE FAIL backend] seq={seq}: {type(exc).__name__}: {exc}")

    if not backend_failed:
        for index, prompt in enumerate(PROMPTS, 1):
            outputs = []
            for enabled in (False, True):
                cfg.sdpa_gqa = enabled
                outputs.append(sample(
                    model, cfg, tokenizer, prompt, max_new=args.max_new,
                    temperature=0.0, top_k=1, device=device, use_cache=True,
                    stop_at_eos=False, logits_last_only=True,
                ))
            same = outputs[0] == outputs[1]
            text_failed |= not same
            print(f"text_prompt={index} exact_equal={int(same)} prompt={prompt!r}")
            if not same:
                print(f"  off={outputs[0]!r}")
                print(f"  on ={outputs[1]!r}")
    cfg.sdpa_gqa = False
    status = gate_status(
        backend_failed=backend_failed, agreement_failed=agreement_failed,
        text_failed=text_failed, ratios=ratios, reductions=reductions,
        slowdown_limit=args.max_slowdown, min_benefit=args.min_benefit,
    )
    if status == 4:
        print("[GATE FAIL agreement] registered NRMS/cosine or greedy-text contract failed")
    elif status == 8:
        print("[GATE NEGATIVE] valid measurement missed speed/memory benefit")
    elif status == 0:
        print("[GATE CANDIDATE] numeric, text, speed and memory gates passed")
    print("[LIMIT] diagnostic attribution only; default sdpa_gqa remains off")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
