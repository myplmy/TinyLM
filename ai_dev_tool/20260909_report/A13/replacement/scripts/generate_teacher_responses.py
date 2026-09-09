#!/usr/bin/env python3
"""A13: 로컬 HF 교사로 train prompt의 응답만 생성한다. 정답 검증은 별도다."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tinylm.chat.canonical import normalize, validate
from tinylm.audit_io import read_records, digest_json, sha256_file, tokenizer_digest, write_json_new


def training_prompt(record):
    if record.get("meta", {}).get("split") != "train":
        raise ValueError("교사 학습자료 생성은 meta.split=train만 허용")
    conv = validate(normalize(record))
    if conv["messages"][-1]["role"] != "assistant":
        raise ValueError("reference assistant 답으로 끝나는 canonical 필요")
    messages = []
    for message in conv["messages"][:-1]:
        if any(b.get("type") != "text" for b in message["content"]):
            raise ValueError("이 도구는 text-only teacher 생성만 지원")
        messages.append({"role": message["role"],
                         "content": "".join(b["text"] for b in message["content"])})
    if not messages or messages[-1]["role"] != "user":
        raise ValueError("교사에게 보낼 마지막 prompt는 user여야 함")
    return messages


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hf-model", required=True, help="config/tokenizer/weights가 있는 특정 로컬 snapshot")
    ap.add_argument("--train", required=True)
    ap.add_argument("--out-jsonl", required=True)
    ap.add_argument("--max-new", type=int, default=128)
    ap.add_argument("--max-input", type=int, default=1024)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--seed", type=int, default=99)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    if min(a.max_new, a.max_input) < 1 or a.limit < 0:
        ap.error("길이 양수, limit 비음수")
    out, folder = Path(a.out_jsonl), Path(a.hf_model)
    if out.exists() or out.with_suffix(".contract.json").exists():
        ap.error("새 출력 경로 필요")
    rows = read_records(a.train)
    if a.limit:
        rows = rows[:a.limit]
    seen = set()
    prompts = []
    for raw in rows:
        ident = str(raw.get("meta", {}).get("id") or "")
        if not ident or ident in seen:
            raise ValueError("train의 고유 meta.id 필요")
        seen.add(ident)
        prompts.append((ident, raw, training_prompt(raw)))
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    tok = AutoTokenizer.from_pretrained(str(folder), local_files_only=True,
                                        trust_remote_code=False, use_fast=True)
    if not tok.chat_template:
        raise ValueError("교사 native chat_template 없음. 임의 template로 instruct 교사인 것처럼 생성하지 않음")
    model = AutoModelForCausalLM.from_pretrained(
        str(folder), local_files_only=True, trust_remote_code=False,
        torch_dtype=torch.bfloat16 if a.device.startswith("cuda") else torch.float32).to(a.device).eval()
    torch.manual_seed(a.seed)
    weights = sorted(set(folder.glob("*.safetensors")) | set(folder.glob("pytorch_model*.bin")))
    if not weights:
        raise ValueError("가중치 shard 파일 없음")
    provenance = {"model": str(folder.resolve()), "config_sha256": sha256_file(folder / "config.json"),
                  "weights": {p.name: sha256_file(p) for p in weights},
                  "tokenizer_sha256": tokenizer_digest(tok), "torch_version": str(torch.__version__),
                  "chat_template_sha256": digest_json(tok.chat_template)}
    context_limit = int(getattr(model.config, "max_position_embeddings", a.max_input + a.max_new))
    out.parent.mkdir(parents=True, exist_ok=True)
    good, skipped = 0, 0
    with out.open("x", encoding="utf-8", newline="\n") as stream:
        for ident, raw, messages in prompts:
            encoded = tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                               enable_thinking=False, return_tensors="pt")
            n_input = encoded.shape[-1]
            base = {"id": ident, "teacher": provenance, "reference_sha256": digest_json(raw),
                    "generation_settings": {"do_sample": False, "max_new": a.max_new,
                                             "enable_thinking_requested": False},
                    "verified_correct": None}
            if n_input > a.max_input or n_input + a.max_new > context_limit:
                result = dict(base, status="skipped", response="", reason="context_overflow")
                skipped += 1
            else:
                encoded = encoded.to(a.device)
                with torch.inference_mode():
                    output = model.generate(encoded, attention_mask=torch.ones_like(encoded),
                                             do_sample=False, max_new_tokens=a.max_new,
                                             pad_token_id=tok.eos_token_id)
                new = output[0, n_input:].tolist()
                response = tok.decode(new, skip_special_tokens=True)
                eos_ids = model.generation_config.eos_token_id
                eos_ids = eos_ids if isinstance(eos_ids, list) else [eos_ids]
                ended = bool(new and new[-1] in eos_ids)
                result = dict(base, status="generated", response=response, response_sha256=digest_json(response),
                              input_tokens=n_input, generated_tokens=len(new),
                              truncated=not ended and len(new) >= a.max_new)
                good += 1
            stream.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
    write_json_new(out.with_suffix(".contract.json"),
                   {"command": vars(a), "provenance": provenance, "source_sha256": sha256_file(a.train),
                    "records_sha256": sha256_file(out), "generated": good, "skipped": skipped,
                    "note": "생성은 정답 검증이 아니다. A13 verification을 통과한 ID만 학습 후보."})
    return 0 if good and not skipped else 2


if __name__ == "__main__":
    raise SystemExit(main())
