#!/usr/bin/env python3
"""P100 Stage0: save raw bilingual answers, not an intelligence score."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASES = (
    ("KO_FACT", "knowledge", "대한민국의 수도는 어디인가요?", "서울"),
    ("EN_FACT", "knowledge", "What is the capital of South Korea?", "Seoul"),
    ("KO_CONTEXT", "context", "문서: 파란 상자의 암호는 417입니다. 질문: 파란 상자의 암호는 무엇인가요?", "417"),
    ("EN_CONTEXT", "context", "Note: The blue box code is 417. Question: What is the blue box code?", "417"),
    ("KO_FORMAT", "format", "도시와 나라를 JSON 두 키 city,country로만 쓰세요. 대상은 서울, 대한민국입니다.", "valid JSON with exactly city,country"),
    ("KO_MULTI", "short_memory", "사용자: 비밀 코드명은 달빛-47입니다. 어시스턴트: 확인했습니다. 사용자: 날씨 이야기는 무시하고 코드명만 말해 주세요. 어시스턴트:", "달빛-47"),
    ("EN_MULTI", "short_memory", "User: The code name is moon-47. Assistant: Noted. User: Ignore the weather and repeat only the code name. Assistant:", "moon-47"),
    ("KO_LOGIC", "logic", "규칙: A이면 B, B이면 C입니다. A가 참일 때 C가 참인지 한 문장으로 답하세요.", "C is true"),
    ("KO_NEGATION", "negation", "사과는 빨갛고 배는 노랗습니다. 빨갛지 않은 과일은 무엇인가요?", "배"),
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1048576), b""):
            digest.update(part)
    return digest.hexdigest()


def parse_model(raw, preset, tokens):
    cells = raw.split(",")
    if len(cells) != 3 or cells[2] not in ("dense", "tied"):
        raise ValueError("model must be tag,data,dense|tied")
    tag, data, arch = cells
    stem = f"{preset}_{data}_{tokens}_{tag}"
    checkpoint = ROOT / "runs/ckpt" / f"{stem}.pt"
    metadata = ROOT / "runs/logs" / f"{stem}.json"
    if not checkpoint.is_file() or not metadata.is_file():
        raise FileNotFoundError(f"paired checkpoint/JSON missing: {stem}")
    meta = json.loads(metadata.read_text(encoding="utf-8"))
    if meta.get("tag") != stem or meta.get("arch") != arch or "final" not in meta:
        raise ValueError(f"model metadata does not match: {stem}")
    return tag, data, arch, checkpoint, meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", required=True)
    parser.add_argument("--preset", default="m100s10")
    parser.add_argument("--tokens", default="300M")
    parser.add_argument("--out", required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--max-new", type=int, default=80)
    args = parser.parse_args()
    if args.max_new < 8 or args.max_new > 256:
        parser.error("max-new must be 8..256")
    output = ROOT / args.out
    if not output.resolve().is_relative_to((ROOT / "runs/bench").resolve()):
        parser.error("output must be under runs/bench")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"refusing existing output: {output}")
    models = [parse_model(raw, args.preset, args.tokens) for raw in args.model]
    if len({tag for tag, *_ in models}) != len(models):
        parser.error("model tags must be unique")
    if args.check_only:
        print(f"[PASS] {len(models)} checkpoint/JSON pairs; {len(CASES)} cases; model/GPU NOT_RUN")
        return 0

    from tinylm.data import load_tokenizer, tokenizer_path
    from tinylm.infer.generate import load_model, sample
    import torch

    rows = []
    for tag, data, arch, checkpoint, meta in models:
        model, cfg, device = load_model(arch, str(checkpoint))
        tok = load_tokenizer(data)
        tokenizer_hash = sha256(tokenizer_path(data))
        checkpoint_hash = sha256(checkpoint)
        for case_id, ability, prompt, rubric in CASES:
            for form, text in (("base", prompt),
                               ("qa", "Question: " + prompt + " Answer:")):
                full = sample(model, cfg, tok, text, max_new=args.max_new,
                              temperature=0, top_k=1, device=device,
                              use_cache=True, logits_last_only=True)
                rows.append(dict(model=tag, data=data, arch=arch,
                                 checkpoint_sha256=checkpoint_hash,
                                 tokenizer_sha256=tokenizer_hash,
                                 final_val=meta["final"]["val_loss"],
                                 case_id=case_id, ability=ability, form=form,
                                 prompt=text, rubric=rubric, full_output=full))
                print(f"[ANSWER] {tag} {case_id} {form}: {full!r}", flush=True)
        del model
        if str(device) == "cuda":
            torch.cuda.empty_cache()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + chr(10))
    print(f"[PASS] saved {len(rows)} raw answers at {output.relative_to(ROOT)}")
    print("[LIMIT] qualitative panel only; no score, no causal dataset or SFT claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
