#!/usr/bin/env python3
"""A02: tokenizer/학습 stream별 오염 제외 manifest를 공통 제외 집합으로 병합한다."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tinylm.eval.audit_io import sha256_file, write_json_new
from tinylm.eval.bpb_corpus import load_documents, merge_exclusions


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifests", nargs="+", required=True)
    ap.add_argument("--squad", default=str(ROOT / "datasets/squad/train-v2.0.json"))
    ap.add_argument("--text-jsonl")
    ap.add_argument("--max-docs", type=int, default=4000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    paths = [Path(p).resolve() for p in a.manifests]
    if len(paths) < 2 or len(paths) != len(set(paths)):
        ap.error("서로 다른 manifest 두 개 이상 필요")
    if Path(a.out).exists():
        ap.error("새 출력 경로 필요")
    docs = load_documents(a.text_jsonl or a.squad, squad=not bool(a.text_jsonl), limit=a.max_docs)
    manifests = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    inputs = [{"path": str(p), "sha256": sha256_file(p)} for p in paths]
    result = merge_exclusions(docs, manifests, inputs=inputs)
    write_json_new(a.out, result)
    print(f"입력 {len(paths)}개, 제외 합집합 {len(result['excluded_ids'])}/{len(docs)} -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
