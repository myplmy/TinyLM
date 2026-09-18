#!/usr/bin/env python3
"""기존 val.bin의 실제 텍스트와 임의 프롬프트를 한 모델로 이어쓰기한다.

캐시·토크나이저·체크포인트를 다운로드하거나 생성하지 않는다. ``--text-only``는 모델을
전혀 로드하지 않고 validation 문맥/정답만 보여 준다.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np

from tinylm.infer.text_probe import select_cache, span_offsets, target_token_start


def _prompts(args):
    values = list(args.prompt or [])
    if args.prompt_file:
        values.extend(line.strip() for line in Path(args.prompt_file).read_text(encoding="utf-8").splitlines()
                      if line.strip())
    return values


def _print_block(title, text):
    print("\n" + "=" * 78)
    print(title)
    print("-" * 78)
    print(text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ckpt-path", help="명시적 checkpoint .pt; --text-only에서는 불필요")
    ap.add_argument("--arch", choices=["dense", "tied"], default="dense")
    ap.add_argument("--cache-data", default="en",
                    help="validation cache identity; project WikiText-103 cache is en")
    ap.add_argument("--model-data",
                    help="checkpoint tokenizer identity, e.g. ko-en or en; model run에서는 필수")
    ap.add_argument("--cache-dir", help="기존 cache dir(meta.json + val.bin)")
    ap.add_argument("--pool-tokens", help="cache 선택 토큰 칸(예: 100M); 후보가 여럿이면 필수")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--context-tokens", type=int, default=96)
    ap.add_argument("--target-tokens", type=int, default=48)
    ap.add_argument("--seed", type=int, default=99)
    ap.add_argument("--max-new", type=int, default=80)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--top-k", type=int, default=40)
    ap.add_argument("--device", choices=["cpu", "cuda"], default=None)
    ap.add_argument("--prompt", action="append", help="임의 prompt; 여러 번 지정 가능")
    ap.add_argument("--prompt-file", help="UTF-8 prompt 한 줄당 하나")
    ap.add_argument("--text-only", action="store_true", help="모델 없이 validation 실제 텍스트만 출력")
    args = ap.parse_args()

    cache = select_cache(ROOT / "data_cache", args.cache_data, args.pool_tokens, args.cache_dir)
    meta = json.loads((cache / "meta.json").read_text(encoding="utf-8"))
    dtype = np.dtype(meta.get("token_dtype", "uint16"))
    val = np.memmap(cache / "val.bin", dtype=dtype, mode="r")

    from tinylm.data import load_tokenizer
    cache_tok = load_tokenizer(args.cache_data)
    offsets = span_offsets(len(val), args.context_tokens, args.target_tokens,
                           args.samples, args.seed)
    spans = []
    for offset in offsets:
        ids = np.asarray(val[offset:offset + args.context_tokens + args.target_tokens], dtype=np.int64)
        context_ids = ids[:args.context_tokens].tolist()
        target_ids = ids[args.context_tokens:].tolist()
        context = cache_tok.decode(context_ids)
        target = cache_tok.decode(target_ids)
        spans.append((offset, ids, context, target))
        _print_block(f"VAL offset={offset} context ({args.context_tokens} tokens)", context)
        _print_block(f"GOLD continuation ({args.target_tokens} tokens)", target)

    print(f"\n[cache] {cache} data={args.cache_data} dtype={dtype} val_tokens={len(val):,}")
    print("[scope] 이 val.bin은 프로젝트 캐시의 말미 validation split이다. "
          "공식 WikiText validation split이라고 자동 승격하지 않는다.")
    if args.text_only:
        return 0
    if not args.ckpt_path:
        ap.error("--ckpt-path is required unless --text-only is set")
    if not args.model_data:
        ap.error("--model-data is required for a checkpoint; tokenizer identity is not guessed")

    import torch
    import torch.nn.functional as F
    from tinylm.infer.generate import load_model, sample

    model, cfg, device = load_model(args.arch, args.ckpt_path, args.device)
    model_tok = load_tokenizer(args.model_data)
    dev_type = device if isinstance(device, str) else device.type
    autocast = dict(dtype=torch.bfloat16, enabled=(dev_type == "cuda"))

    for index, (offset, ids, context, target) in enumerate(spans, 1):
        if args.model_data == args.cache_data:
            model_ids = ids.tolist()
            target_start = args.context_tokens
            crossed = 0
        else:
            encoded = model_tok.encode(context + target)
            model_ids = list(encoded.ids)
            target_start, crossed = target_token_start(encoded.offsets, len(context))
        if len(model_ids) > cfg.max_seq_len:
            raise ValueError(
                f"retokenized validation span has {len(model_ids)} tokens, "
                f"exceeding checkpoint max_seq_len={cfg.max_seq_len}")
        x = torch.tensor(model_ids[:-1], dtype=torch.long, device=device).unsqueeze(0)
        y = torch.tensor(model_ids[target_start:], dtype=torch.long, device=device)
        with torch.no_grad(), torch.autocast(dev_type, **autocast):
            logits = model(x)[:, target_start - 1:, :].float().squeeze(0)
        nll = float(F.cross_entropy(logits, y))
        target_bytes = max(1, len(target.encode("utf-8")))
        bpb = nll * len(y) / (target_bytes * math.log(2))
        generated = sample(model, cfg, model_tok, context, max_new=args.max_new,
                           temperature=args.temperature, top_k=args.top_k,
                           device=device, use_cache=True)
        continuation = generated[len(context):] if generated.startswith(context) else generated
        _print_block(f"MODEL continuation #{index} offset={offset}", continuation)
        print(f"[teacher-forced] target_nll={nll:.6f} ppl={math.exp(min(nll, 20)):.3f} "
              f"sample_bpb={bpb:.6f} model_tokens={len(model_ids)} "
              f"boundary_cross_tokens_dropped={crossed}")

    for index, prompt in enumerate(_prompts(args), 1):
        generated = sample(model, cfg, model_tok, prompt, max_new=args.max_new,
                           temperature=args.temperature, top_k=args.top_k,
                           device=device, use_cache=True)
        _print_block(f"USER prompt #{index}", generated)

    print("\n[interpretation] 이 모델은 사전학습 next-token continuation 모델이다. "
          "질문응답·지시이행 실패를 곧바로 모델 로딩 실패로 해석하지 않는다.")
    print(f"[tokenizers] cache={args.cache_data} model={args.model_data}; "
          "서로 다르면 표시된 원문을 모델 토크나이저로 재인코딩했다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
