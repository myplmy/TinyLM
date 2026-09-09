"""A02 교체본: 문서별 모든 target token을 한 번씩 채점하는 원문 bpb.
기존 concatenate/floor-chunk bpb와 수치 규약이 다르므로 새 profile로 기록한다.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tinylm.eval.audit_io import sha256_file, write_json_new
from tinylm.eval.bpb_corpus import load_documents, corpus_digest, exclude_documents
from tinylm.eval.model_adapter import load_local_model, parse_map, prefix_ids

SQUAD = ROOT / "datasets" / "squad" / "train-v2.0.json"


def load_squad_contexts(path=SQUAD, limit=None):
    # 기존 진단 도구가 import하는 함수의 반환형을 유지한다.
    return [d["text"] for d in load_documents(path, squad=True, limit=limit or 0)]


def document_nll(model, tok, text, *, device, seq, stride, micro_bs, ce_chunk, prefix_id=None):
    import torch
    import torch.nn.functional as F
    try:
        encoded = tok.encode(text, add_special_tokens=False)
    except TypeError:
        encoded = tok.encode(text)
    targets = encoded.ids
    if not targets:
        raise ValueError("빈 token 문서")
    prefix, prefix_kind = prefix_ids(tok, prefix_id)
    ids = prefix + targets
    windows = []
    for start in range(0, len(targets), stride):
        stop = min(len(targets), start + stride)
        end = len(prefix) + stop - 1
        left = max(0, end - seq)
        first = len(prefix) + start - 1 - left
        x = ids[left:end]
        if first < 0 or not x:
            raise ValueError("잘못된 scoring window")
        windows.append((x, first, targets[start:stop]))
    total, scored = 0.0, 0
    dev_type = torch.device(device).type
    with torch.inference_mode():
        for start in range(0, len(windows), micro_bs):
            batch = windows[start:start + micro_bs]
            width = max(len(x) for x, _, _ in batch)
            x = torch.full((len(batch), width), prefix[0], dtype=torch.long, device=device)
            for i, (tokens, _, _) in enumerate(batch):
                x[i, :len(tokens)] = torch.tensor(tokens, device=device)
            with torch.autocast(dev_type, dtype=torch.bfloat16, enabled=dev_type == "cuda"):
                logits = model(x)
            for i, (_, offset, truth) in enumerate(batch):
                for j in range(0, len(truth), ce_chunk):
                    labels = torch.tensor(truth[j:j + ce_chunk], dtype=torch.long, device=device)
                    pred = logits[i, offset + j:offset + j + len(labels)].float()
                    total += float(F.cross_entropy(pred, labels, reduction="sum"))
                    scored += len(labels)
    if scored != len(targets) or not math.isfinite(total):
        raise ValueError("모든 target의 정확히 한 번 채점에 실패")
    return {"nll_sum": total, "scored_tokens": scored, "text_tokens": len(targets),
            "scored_bytes": len(text.encode("utf-8")), "prefix": prefix_kind,
            "prefix_tokens_not_scored": len(prefix), "tail_tokens_omitted": 0}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--data", nargs="+", default=None)
    ap.add_argument("--data-default", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--preset", default="m100")
    ap.add_argument("--arch", nargs="+", default=None, help="호환 인자. 실제 구조는 checkpoint cfg에서 읽음")
    ap.add_argument("--max-docs", type=int, default=4000)
    ap.add_argument("--squad", default=str(SQUAD))
    ap.add_argument("--text-jsonl")
    ap.add_argument("--seq", type=int, default=1024)
    ap.add_argument("--stride", type=int, default=256)
    ap.add_argument("--micro-bs", type=int, default=1)
    ap.add_argument("--ce-chunk", type=int, default=256)
    ap.add_argument("--prefix-id", type=int)
    ap.add_argument("--device", default=None)
    ap.add_argument("--drop-contaminated", action="store_true")
    ap.add_argument("--contamination-manifest")
    ap.add_argument("--tokenizer-hf", nargs="*")
    ap.add_argument("--tokenizer", nargs="*")
    ap.add_argument("--checkpoint", nargs="*")
    ap.add_argument("--hf-model", nargs="*")
    ap.add_argument("--out-jsonl", required=True)
    a = ap.parse_args()
    if not (1 <= a.stride <= a.seq and a.micro_bs >= 1):
        ap.error("1 <= stride <= seq, micro-bs >= 1 필요")
    if a.drop_contaminated != bool(a.contamination_manifest):
        ap.error("--drop-contaminated와 --contamination-manifest를 함께 지정")
    if a.ce_chunk <= 0:
        a.ce_chunk = a.seq
    docs = load_documents(a.text_jsonl or a.squad, squad=not bool(a.text_jsonl), limit=a.max_docs)
    before, manifest_sha = len(docs), None
    full_digest = corpus_digest(docs)
    if a.drop_contaminated:
        manifest = json.loads(Path(a.contamination_manifest).read_text(encoding="utf-8"))
        docs = exclude_documents(docs, manifest)
        manifest_sha = sha256_file(a.contamination_manifest)
    clean_digest = corpus_digest(docs)
    datas = a.data or [a.data_default]
    if len(datas) == 1:
        datas *= len(a.models)
    if len(datas) != len(a.models) or len(set(a.models)) != len(a.models):
        ap.error("모델별 data 개수/중복 tag 확인")
    if a.arch and len(a.arch) not in (1, len(a.models)):
        ap.error("--arch 개수 확인")
    ckmap, hfmap = parse_map(a.checkpoint), parse_map(a.hf_model)
    tokmap, thmap = parse_map(a.tokenizer), parse_map(a.tokenizer_hf)
    if (set(ckmap) | set(hfmap) | set(tokmap) | set(thmap)) - set(a.models):
        ap.error("모델 목록에 없는 TAG 옵션")
    if set(ckmap) & set(hfmap):
        ap.error("한 tag에 TinyLM/HF 동시 지정")
    out = Path(a.out_jsonl)
    if out.exists() or out.with_suffix(".summary.json").exists():
        ap.error("출력 파일이 이미 있음")
    out.parent.mkdir(parents=True, exist_ok=True)
    import torch
    from tinylm import paths
    device = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    summaries = {}
    with out.open("x", encoding="utf-8", newline="\n") as stream:
        for tag, data in zip(a.models, datas):
            ck = None if tag in hfmap else ckmap.get(tag) or paths.resolve_ckpt(
                a.preset, data, a.tokens, tag)
            model, tok, meta = load_local_model(tag, checkpoint=ck, hf_path=hfmap.get(tag),
                                                data=data, tokenizer_path=tokmap.get(tag),
                                                tokenizer_hf=thmap.get(tag), device=device)
            seq = min(a.seq, meta["max_seq_len"])
            if a.stride > seq:
                raise ValueError("stride가 모델 context를 초과")
            total, byte_count, tokens = 0.0, 0, 0
            language = defaultdict(lambda: [0.0, 0])
            for doc in docs:
                r = document_nll(model, tok, doc["text"], device=device, seq=seq,
                                 stride=a.stride, micro_bs=a.micro_bs,
                                 ce_chunk=a.ce_chunk, prefix_id=a.prefix_id)
                r.update(id=doc["id"], model=tag, task="common_bpb",
                         text_sha256=doc["text_sha256"], status="ok",
                         language=doc.get("language", "unspecified"),
                         bpb=r["nll_sum"] / math.log(2) / r["scored_bytes"],
                         model_provenance=meta, corpus_sha256=clean_digest,
                         item_sha256=doc["text_sha256"], dataset_sha256=clean_digest,
                         scoring_profile=f"document_all_targets_bpb.v1.seq{seq}.stride{a.stride}")
                stream.write(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n")
                stream.flush()
                total += r["nll_sum"]
                byte_count += r["scored_bytes"]
                tokens += r["scored_tokens"]
                language[r["language"]][0] += r["nll_sum"]
                language[r["language"]][1] += r["scored_bytes"]
            summaries[tag] = {"bpb": total / math.log(2) / byte_count,
                              "nll_sum": total, "bytes": byte_count, "tokens": tokens,
                              "documents": len(docs), "before_exclusion": before,
                              "corpus_before_sha256": full_digest,
                              "corpus_after_sha256": clean_digest,
                              "exclusion_manifest_sha256": manifest_sha,
                              "language_bpb": {k: v[0] / math.log(2) / v[1]
                                               for k, v in language.items()},
                              "scoring_profile": "document_all_targets_bpb.v1",
                              "scope": "fixed raw bytes; tokenizer-dependent token context windows"}
            print(tag, json.dumps(summaries[tag], ensure_ascii=False))
            del model
            if str(device).startswith("cuda"):
                torch.cuda.empty_cache()
    write_json_new(out.with_suffix(".summary.json"), {"models": summaries, "command": vars(a),
                                                       "records_sha256": sha256_file(out)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
