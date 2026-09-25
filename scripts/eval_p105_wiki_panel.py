#!/usr/bin/env python3
"""P105 fixed wiki/URL generation panel; user runs model, never trains/downloads."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "runs" / "bench"
PROMPTS = {
    "general": (
        "대한민국의 수도를 한 문장으로 답하세요.",
        "사과와 배의 색을 한 문장씩 비교하세요.",
        "물은 섭씨 몇 도에서 끓나요? 짧게 답하세요.",
        "친구에게 내일 약속 시간을 확인하는 짧은 답을 쓰세요.",
        "What is two plus three? Answer in one sentence."),
    "wiki": (
        "세종대왕은 어떤 일을 했나요? 두 문장으로 답하세요.",
        "한글 창제의 목적을 설명하세요.",
        "서울의 위치를 간단히 설명하세요.",
        "조선의 과학사에서 장영실을 소개하세요.",
        "What was the Industrial Revolution? Answer briefly."),
    "url_request": (
        "위키백과 서울 문서의 공식 URL을 하나 알려 주세요.",
        "한국어 위키백과의 첫 화면 주소를 URL로 답하세요.",
        "프로젝트의 공식 웹사이트를 확인할 수 없다면 모른다고 답하세요.",
        "Give the URL of the English Wikipedia home page.",
        "확인 가능한 링크가 없다면 링크를 꾸며내지 말고 모른다고 답하세요."),
    "provided_context": (
        "문서: 파란 상자의 암호는 417입니다. 질문: 암호만 답하고 링크는 쓰지 마세요.",
        "문서: 자료 A는 3개, 자료 B는 5개입니다. 질문: 합계만 답하세요.",
        "문서에 https://example.invalid/test가 있습니다. 질문: URL을 반복하지 말고 링크 유무만 답하세요.",
        "문서: 회의는 화요일 오전 10시입니다. 질문: 요일과 시간을 짧게 답하세요.",
        "Note: the box code is moon-47. Question: answer with only the code."),
}
CASES = tuple((f"{group[0].upper()}{i}", group, prompt, group == "url_request", False)
              for group, prompts in PROMPTS.items() for i, prompt in enumerate(prompts, 1))
DECODES = (("greedy", 0.0, 1), ("sample_t07", 0.7, 40))


def parse_spec(raw: str) -> tuple[str, str, str, str, str, str]:
    cells = raw.split(",")
    if len(cells) == 5:
        cells.append("legacy")
    if len(cells) != 6 or cells[2] not in ("dense", "tied") or cells[5] not in ("legacy", "chat32"):
        raise ValueError("model=tag,data,arch,preset,tokens[,legacy|chat32]")
    if not all(re.fullmatch(r"[A-Za-z0-9_-]+", cell) for cell in cells):
        raise ValueError("unsafe model specification")
    return tuple(cells)


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1048576), b""):
            sha.update(part)
    return sha.hexdigest().upper()


def metadata(spec) -> dict:
    from tinylm.data.prepare import chat_tokenizer_path, tokenizer_path
    tag, data, arch, preset, tokens, lineage = spec
    stem = f"{preset}_{data}_{tokens}_{tag}"
    ckpt = ROOT / "runs" / "ckpt" / f"{stem}.pt"
    run_json = ROOT / "runs" / "logs" / f"{stem}.json"
    tokenizer = chat_tokenizer_path(data) if lineage == "chat32" else tokenizer_path(data)
    if not all(p.is_file() and not p.is_symlink() for p in (ckpt, run_json, tokenizer)):
        raise FileNotFoundError(f"checkpoint/JSON/tokenizer absent: {stem}")
    meta = json.loads(run_json.read_text(encoding="utf-8"))
    if (meta.get("tag") != stem or meta.get("data") != data or meta.get("arch") != arch
            or meta.get("preset") not in (None, preset) or not meta.get("final")):
        raise ValueError(f"model metadata mismatch: {stem}")
    if lineage == "chat32" and (meta.get("tokenizer_lineage") != "chat32"
                                or meta.get("tokenizer_sha256", "").upper() != digest(tokenizer)):
        raise ValueError(f"chat32 tokenizer SHA mismatch: {stem}")
    return {"tag": tag, "data": data, "arch": arch, "preset": preset, "tokens": tokens,
            "lineage": lineage, "checkpoint": ckpt, "tokenizer": tokenizer, "meta": meta}


def evaluate(items, out: Path, seed: int, max_new: int, record_termination: bool = False) -> None:
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model, sample

    partial = out.with_suffix(out.suffix + ".partial")
    if out.exists() or out.is_symlink() or partial.exists() or partial.is_symlink():
        raise FileExistsError("output or partial exists; never overwrite")
    out.parent.mkdir(parents=True, exist_ok=True)
    with partial.open("x", encoding="utf-8") as stream:
        for item in items:
            model, cfg, device = load_model(item["arch"], str(item["checkpoint"]))
            tokenizer = Tokenizer.from_file(str(item["tokenizer"]))
            model_sha, tok_sha = digest(item["checkpoint"]), digest(item["tokenizer"])
            for case_id, stratum, prompt, url_requested, heading_requested in CASES:
                for decode, temperature, top_k in DECODES:
                    local_seed = seed + int(hashlib.sha256(
                        f"{item['tag']}:{case_id}:{decode}".encode()).hexdigest()[:8], 16)
                    torch.manual_seed(local_seed)
                    generated = sample(model, cfg, tokenizer, prompt, max_new=max_new,
                                  temperature=temperature, top_k=top_k, device=device,
                                  use_cache=True, stop_at_eos=True, logits_last_only=True,
                                  return_metadata=record_termination)
                    full, termination = generated if record_termination else (generated, {})
                    if not full.startswith(prompt):
                        raise ValueError(f"prompt prefix changed: {item['tag']} {case_id}")
                    row = {"schema": "P105_WIKI_PANEL_V1", "model": item["tag"],
                           "data": item["data"], "arch": item["arch"],
                           "preset": item["preset"], "tokens": item["tokens"],
                           "tokenizer_lineage": item["lineage"],
                           "checkpoint_sha256": model_sha, "tokenizer_sha256": tok_sha,
                           "case_id": case_id, "stratum": stratum, "prompt": prompt,
                           "full_output": full, "decode": decode, "seed": local_seed,
                           "temperature": temperature, "top_k": top_k,
                           "stop_at_eos": True, "finish_reason": "NOT_MEASURED",
                           "url_requested": url_requested, "heading_requested": heading_requested}
                    if record_termination:
                        row.update(termination)
                        row["termination_schema"] = "P105_TERMINATION_V1"
                    stream.write(json.dumps(row, ensure_ascii=False) + chr(10))
                    stream.flush()
                    print(f"[ANSWER] {item['tag']} {case_id} {decode}: {full[len(prompt):]!r}", flush=True)
            del model
            if str(device) == "cuda":
                torch.cuda.empty_cache()
    partial.rename(out)
    print(f"[PASS] {len(items) * len(CASES) * len(DECODES)} raw answers saved: {out.relative_to(ROOT)}")
    print("[LIMIT] source causality and semantic quality NOT_RUN; "
          + ("actual EOS reason MEASURED" if record_termination else "actual EOS reason NOT_MEASURED"))


def self_test() -> None:
    assert len(CASES) == 20 and len({c[0] for c in CASES}) == 20
    assert {c[1] for c in CASES} == set(PROMPTS)
    assert parse_spec("a,ko-en,dense,m100s10,300M")[-1] == "legacy"
    assert parse_spec("b,ko-en,dense,m100s10,300M,chat32")[-1] == "chat32"
    for bad in ("a,ko-en,dense", "a,ko-en,dense,m100s10,300M,bad",
                "x,../bad,dense,m100s10,300M"):
        try:
            parse_spec(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe spec accepted")
    print("[PASS] P105 20 cases/4 strata/2 decodes and lineage parser; model/GPU NOT_RUN")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--record-termination", action="store_true")
    ap.add_argument("--model", action="append", default=[])
    ap.add_argument("--out")
    ap.add_argument("--seed", type=int, default=20260925)
    ap.add_argument("--max-new", type=int, default=80)
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.model or not args.out or not 16 <= args.max_new <= 256:
        ap.error("models, out and max-new 16..256 required")
    specs = [parse_spec(raw) for raw in args.model]
    if len({(s[0], s[1], s[3], s[4]) for s in specs}) != len(specs):
        ap.error("duplicate model spec")
    out = (ROOT / args.out).resolve()
    if not out.is_relative_to(OUT_DIR) or out.suffix != ".jsonl":
        ap.error("output must be JSONL under runs/bench")
    if out.exists() or out.with_suffix(out.suffix + ".partial").exists():
        raise FileExistsError("output or partial exists")
    items = [metadata(spec) for spec in specs]
    if args.check_only:
        for item in items:
            print(f"[CHECK] {item['tag']} lineage={item['lineage']} final_val={item['meta']['final']['val_loss']}")
        print(f"[PASS] {len(items)} model/JSON/tokenizer pairs; model/GPU NOT_RUN")
        return 0
    evaluate(items, out, args.seed, args.max_new, args.record_termination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
