#!/usr/bin/env python3
"""메타데이터를 보고 모델을 고른 뒤 프롬프트를 반복 입력하는 TinyLM probe.

체크포인트 목록은 파일명과 ``runs/logs/*.json``만 읽어 만든다. 모델은 사용자가 하나를
선택한 뒤에만 로드한다. ``:val``은 그 모델의 기존 validation cache에서 실제 문맥을 하나
꺼내 gold continuation과 모델 continuation을 나란히 보여 준다.
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tinylm  # noqa: F401  # HF cache redirect before any optional HF import
from tinylm import paths
from tinylm.infer.catalog import discover_models, filter_models, resolve_selection


def _display(records, limit):
    shown = records[:limit]
    print("\n" + "=" * 118)
    print("  모델 선택 — val은 학습 JSON의 final/best random-crop 값이며 full-val·벤치 점수가 아닙니다")
    print("=" * 118)
    print(f"  {'번호':>4}  {'tag':<42} {'preset':<11} {'data':<14} {'arch':<6} {'val':>9} {'steps':>7} {'seed':>6}")
    print("  " + "-" * 114)
    for index, row in enumerate(shown, 1):
        val = f"{row.display_val:.5f}" if row.display_val is not None else "?"
        print(f"  {index:>4}  {row.selector[:42]:<42} {row.preset:<11} {row.data:<14} "
              f"{(row.arch or '?'):<6} {val:>9} {str(row.steps or '?'):>7} {str(row.seed or '?'):>6}")
    if len(records) > len(shown):
        print(f"  ... {len(records) - len(shown)}개 더 있음. `/검색어`로 좁히거나 --limit을 늘리세요.")
    return shown


def _choose(records, limit, preset_selection=None):
    if preset_selection:
        return resolve_selection(records, preset_selection)
    view = records
    while True:
        shown = _display(view, limit)
        raw = input("\n모델 번호/태그 (`/검색어`, `all`, `q`): ").strip()
        if raw.lower() in {"q", "quit", ":q"}:
            return None
        if raw.lower() == "all":
            view = records
            limit = len(records)
            continue
        if raw.startswith("/"):
            view = filter_models(records, raw[1:])
            if not view:
                print("일치 모델이 없습니다.")
                view = records
            continue
        try:
            return resolve_selection(shown, raw)
        except ValueError as exc:
            print(f"[선택 오류] {exc}")


def _metadata(record):
    print("\n" + "-" * 92)
    print(f"checkpoint : {record.checkpoint}")
    print(f"selector   : {record.selector}")
    print(f"preset/data: {record.preset} / {record.data} / {record.tokens}")
    print(f"arch       : {record.arch or 'UNKNOWN'}")
    print(f"val        : {record.display_val if record.display_val is not None else 'UNKNOWN'} "
          f"({'best_val' if record.is_best else 'final.val_loss'})")
    print(f"steps/pool : {record.steps or 'UNKNOWN'} / {record.pool_tokens or 'UNKNOWN'}")
    print(f"optimizer  : {record.optimizer or 'UNKNOWN'}  seed={record.seed or 'UNKNOWN'}")
    print("[주의] 사전학습 next-token 모델입니다. SFT가 없으면 질문응답·대화 지시이행을 기대하지 않습니다.")


def _validation_probe(record, model, cfg, tokenizer, device, *, max_new, temperature, top_k):
    import numpy as np
    from tinylm.infer.generate import sample
    from tinylm.infer.text_probe import select_cache, span_offsets

    pool = str(record.pool_tokens) if record.pool_tokens else None
    try:
        cache = select_cache(paths.DATA_CACHE, record.data, pool_tokens=pool)
    except ValueError as exc:
        print(f"[val] cache 자동 선택 실패: {exc}")
        print("      scripts/infer_text_probe.py --cache-dir <경로>를 사용하세요.")
        return
    meta = json.loads((cache / "meta.json").read_text(encoding="utf-8"))
    values = np.memmap(cache / "val.bin", dtype=np.dtype(meta.get("token_dtype", "uint16")), mode="r")
    context_tokens, target_tokens = 96, 48
    offset = span_offsets(len(values), context_tokens, target_tokens, 1, seed=99)[0]
    ids = list(map(int, values[offset:offset + context_tokens + target_tokens]))
    context = tokenizer.decode(ids[:context_tokens])
    gold = tokenizer.decode(ids[context_tokens:])
    generated = sample(
        model, cfg, tokenizer, context, max_new=max_new, temperature=temperature,
        top_k=top_k, device=device, use_cache=True, logits_last_only=True,
    )
    continuation = generated[len(context):] if generated.startswith(context) else generated
    print(f"\n[val offset={offset}] CONTEXT\n{context}")
    print(f"\n[val offset={offset}] GOLD\n{gold}")
    print(f"\n[val offset={offset}] MODEL\n{continuation}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="번호(정렬 전체 기준), 정확한 태그 또는 고유 부분문자열")
    parser.add_argument("--filter", default="", help="초기 모델 목록 필터")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--device", choices=["cpu", "cuda"], default=None)
    parser.add_argument("--max-new", type=int, default=96)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-k", type=int, default=40)
    parser.add_argument("--prompt", help="한 번만 생성하고 종료")
    parser.add_argument("--list", action="store_true", help="목록만 출력하고 모델을 로드하지 않음")
    args = parser.parse_args()

    records = discover_models(paths.RUNS / "ckpt", paths.RUNS / "logs")
    records = filter_models(records, args.filter)
    if not records:
        print("[STOP] 선택 가능한 checkpoint가 없습니다.", file=sys.stderr)
        return 2
    if args.list:
        _display(records, len(records) if args.limit <= 0 else args.limit)
        return 0

    fixed_selection = args.model
    while True:
        record = _choose(records, max(1, args.limit), fixed_selection)
        fixed_selection = None
        if record is None:
            return 0
        if record.arch not in {"dense", "tied"}:
            print("[STOP] JSON에 arch가 없어 안전하게 로드할 수 없습니다. 다른 모델을 고르세요.")
            continue
        _metadata(record)

        import torch
        from tinylm.data import load_tokenizer
        from tinylm.infer.generate import load_model, sample

        model, cfg, device = load_model(record.arch, str(record.checkpoint), args.device)
        tokenizer = load_tokenizer(record.data)
        print(f"[loaded] device={device}; generation uses KV cache + logits_last_only=True")

        if args.prompt is not None:
            print(sample(
                model, cfg, tokenizer, args.prompt, max_new=args.max_new,
                temperature=args.temperature, top_k=args.top_k, device=device,
                use_cache=True, logits_last_only=True,
            ))
            return 0

        print("명령: :val 실제 validation 문맥, :meta 메타데이터, :model 모델 변경, :quit 종료")
        while True:
            try:
                prompt = input("\nprompt> ")
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            command = prompt.strip().lower()
            if command in {":q", ":quit", "quit"}:
                return 0
            if command == ":model":
                break
            if command == ":meta":
                _metadata(record)
                continue
            if command == ":val":
                _validation_probe(
                    record, model, cfg, tokenizer, device, max_new=args.max_new,
                    temperature=args.temperature, top_k=args.top_k,
                )
                continue
            if not prompt.strip():
                continue
            generated = sample(
                model, cfg, tokenizer, prompt, max_new=args.max_new,
                temperature=args.temperature, top_k=args.top_k, device=device,
                use_cache=True, logits_last_only=True,
            )
            print(generated)
        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


if __name__ == "__main__":
    raise SystemExit(main())
