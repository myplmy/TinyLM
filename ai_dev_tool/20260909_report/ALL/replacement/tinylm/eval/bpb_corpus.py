"""A02: 고정 문서 집합과 오염 제외 manifest 계약."""
from __future__ import annotations
import json
from pathlib import Path
from .audit_io import digest_json, read_records


def load_documents(path, *, squad=False, limit=4000):
    if limit < 0:
        raise ValueError("limit은 0 이상")
    if squad:
        obj = json.loads(Path(path).read_text(encoding="utf-8"))
        texts = sorted({p["context"] for a in obj["data"] for p in a["paragraphs"]})
        rows = [{"id": "squad:" + digest_json(text), "text": text, "language": "en"}
                for text in texts]
    else:
        rows = read_records(path)
    out, seen = [], set()
    for row in rows[:limit] if limit else rows:
        if not isinstance(row.get("text"), str) or not row["text"]:
            raise ValueError("빈/누락 text")
        ident = str(row.get("id") or digest_json(row["text"]))
        if ident in seen:
            raise ValueError(f"중복 문서 id: {ident}")
        seen.add(ident)
        out.append(dict(row, id=ident, text_sha256=digest_json(row["text"])))
    if not out:
        raise ValueError("문서 0개")
    return out


def corpus_digest(docs):
    return digest_json([[d["id"], d["text_sha256"]] for d in docs])


def exclude_documents(docs, manifest):
    if manifest.get("schema") != "tinylm.bpb-exclusion.v1":
        raise ValueError("오염 제외 manifest schema 불일치")
    if manifest.get("corpus_sha256") != corpus_digest(docs):
        raise ValueError("오염 목록의 문서 집합/순서가 현재 corpus와 다름")
    if (type(manifest.get("document_count")) is not int
            or manifest["document_count"] != len(docs)):
        raise ValueError("오염 manifest의 문서 수 불일치")
    ids = manifest.get("excluded_ids")
    if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids) or len(ids) != len(set(ids)):
        raise ValueError("excluded_ids는 중복 없는 문자열 목록이어야 함")
    excluded = set(ids)
    known = {d["id"] for d in docs}
    if excluded - known:
        raise ValueError("오염 목록에 현재 corpus에 없는 ID가 있음")
    if manifest.get("scan_complete") is not True:
        raise ValueError("미완료 scan의 제외 목록을 clean 증거로 사용할 수 없음")
    kept = [d for d in docs if d["id"] not in excluded]
    if not kept:
        raise ValueError("제외 후 문서 0개")
    return kept


def merge_exclusions(docs, manifests, *, inputs):
    """각 tokenizer/stream 검사 결과의 제외 집합을 합쳐 공통 clean corpus를 만든다."""
    if len(manifests) < 2 or len(inputs) != len(manifests):
        raise ValueError("두 개 이상 manifest와 같은 수의 입력 provenance 필요")
    excluded = set()
    for manifest in manifests:
        exclude_documents(docs, manifest)
        excluded.update(manifest["excluded_ids"])
    merged = {"schema": "tinylm.bpb-exclusion.v1", "corpus_sha256": corpus_digest(docs),
              "document_count": len(docs), "excluded_ids": sorted(excluded),
              "scan_complete": True, "method": "union_of_complete_manifests",
              "inputs": [dict(source=source, manifest=manifest)
                         for source, manifest in zip(inputs, manifests)],
              "scope": "입력 manifest의 모든 제외 ID 합집합. 각 원 검사의 tokenizer/stream/ngram 범위만 보증."}
    exclude_documents(docs, merged)
    return merged
