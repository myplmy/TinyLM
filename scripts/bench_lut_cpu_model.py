#!/usr/bin/env python3
"""P014D native CPU LUT end-to-end greedy decode gate; training 0."""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROMPT = "대한민국의 수도 서울은"


def _decode(sample, model, cfg, tokenizer, device, max_new):
    return sample(
        model, cfg, tokenizer, PROMPT,
        max_new=max_new, temperature=0.0, top_k=1, device=device,
        use_cache=True, logits_last_only=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", default="m100R1c")
    parser.add_argument("--data", default="ko-en")
    parser.add_argument("--tokens", default="300M")
    parser.add_argument("--models", nargs="+", default=["mC_cla2_ag4", "mC_cla2_ag4_r20"])
    parser.add_argument("--max-new", type=int, default=32)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--iters", type=int, default=3)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--min-speedup", type=float, default=1.50)
    args = parser.parse_args()

    import torch
    from tinylm import paths
    from tinylm.data import load_tokenizer
    from tinylm.infer.generate import load_model, sample

    torch.set_num_threads(args.threads)
    tokenizer = load_tokenizer(args.data)
    print(f"torch={torch.__version__} threads={torch.get_num_threads()} prompt={PROMPT!r}")
    print("model\tpath\tmedian_ms\ttok_per_s\tvs_int8")
    candidates = []
    for tag in args.models:
        checkpoint = paths.RUNS / "ckpt" / f"{args.preset}_{args.data}_{args.tokens}_{tag}.pt"
        if not checkpoint.is_file():
            print(f"[GATE FAIL] checkpoint missing: {checkpoint.name}")
            return 2
        rows = {}
        outputs = {}
        for path in ("fp32", "int8", "lut_reference", "lut_native"):
            model, cfg, device = load_model(
                "dense" if "dense" in tag else "tied", str(checkpoint), device="cpu"
            )
            model.eval()
            if path != "fp32":
                model.drop_latent()
                if path == "int8":
                    model.to_int8()
                else:
                    model.to_lut()
                    model.cfg.lut_backend = "native_cpu" if path == "lut_native" else "reference"
                    model.cfg.lut_out_chunk = 256
            for _ in range(args.warmup):
                _decode(sample, model, cfg, tokenizer, device, 4)
            values = []
            output = ""
            for _ in range(args.iters):
                started = time.perf_counter()
                output = _decode(sample, model, cfg, tokenizer, device, args.max_new)
                values.append((time.perf_counter() - started) * 1e3)
            median_ms = statistics.median(values)
            rows[path] = median_ms
            outputs[path] = output
            del model
        if outputs["lut_reference"] != outputs["lut_native"]:
            print(f"[GATE FAIL correctness] {tag}: native/reference greedy outputs differ")
            return 4
        for path, median_ms in rows.items():
            ratio = rows["int8"] / median_ms
            print(f"{tag}\t{path}\t{median_ms:.3f}\t"
                  f"{args.max_new / (median_ms / 1e3):.3f}\t{ratio:.3f}x")
        speedup = rows["int8"] / rows["lut_native"]
        candidates.append(speedup)
        print(f"[model] {tag} native_vs_int8={speedup:.3f}x "
              f"native_vs_reference={rows['lut_reference'] / rows['lut_native']:.3f}x")

    if max(candidates, default=0.0) < args.min_speedup:
        print(f"[GATE NEGATIVE] no model reached native LUT/int8 >= {args.min_speedup:.2f}x")
        return 8
    print(f"[GATE CANDIDATE] at least one model reached native LUT/int8 >= {args.min_speedup:.2f}x")
    print("[LIMIT] per-row requantized weights; speed is valid, model quality remains separately measured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
