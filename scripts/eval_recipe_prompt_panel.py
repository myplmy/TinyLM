#!/usr/bin/env python3
"""Deterministic P097 continuation panel with each checkpoint's own tokenizer."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.eval_bench_suite import _model_specs
from scripts.probe_prompts import PROMPTS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--model-data", nargs="+", required=True)
    parser.add_argument("--model-arch", nargs="+", default=["dense"])
    parser.add_argument("--preset", default="m100s10")
    parser.add_argument("--tokens", default="300M")
    parser.add_argument("--max-new", type=int, default=80)
    parser.add_argument("--device", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        for index, (prompt, purpose, max_new) in enumerate(PROMPTS, 1):
            print(f"{index}\tmax_new={min(max_new, args.max_new)}\t{prompt}\t{purpose}")
        return 0
    try:
        specs = _model_specs(args.models, args.model_data[0], args.model_data, args.model_arch)
    except ValueError as exc:
        parser.error(str(exc))

    output = ROOT / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        print(f"[STOP] refusing to append/overwrite prompt panel: {output}")
        return 3

    import torch
    from tinylm import paths
    from tinylm.data import load_tokenizer
    from tinylm.infer.generate import load_model, sample

    rows = []
    for tag, data, arch in specs:
        checkpoint = paths.RUNS / "ckpt" / f"{args.preset}_{data}_{args.tokens}_{tag}.pt"
        if not checkpoint.is_file():
            print(f"[GATE FAIL] checkpoint missing: {checkpoint.name}")
            return 2
        tokenizer = load_tokenizer(data)
        model, cfg, device = load_model(arch, str(checkpoint), device=args.device)
        model.eval()
        for index, (prompt, purpose, planned_max) in enumerate(PROMPTS, 1):
            max_new = min(planned_max, args.max_new)
            generated = sample(
                model, cfg, tokenizer, prompt,
                max_new=max_new, temperature=0.0, top_k=1,
                device=device, use_cache=True, logits_last_only=True,
            )
            continuation = generated[len(prompt):] if generated.startswith(prompt) else generated
            row = {
                "model": tag, "data": data, "arch": arch,
                "prompt_id": index, "prompt": prompt, "purpose": purpose,
                "max_new": max_new, "continuation": continuation,
            }
            rows.append(row)
            print(f"[panel] model={tag} data={data} prompt={index} chars={len(continuation)}")
        del model
        if str(device) == "cuda":
            torch.cuda.empty_cache()

    with output.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[PASS] P097 prompt panel rows={len(rows)} -> {output.relative_to(ROOT)}")
    print("[LIMIT] qualitative continuations require human review; this script does not rank them")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
