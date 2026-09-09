"""A02: 모든 평가 문서의 n-gram을 train.bin 전체와 대조해 제외 ID를 저장한다."""
from __future__ import annotations
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tinylm.eval.audit_io import sha256_file, tokenizer_digest, write_json_new
from tinylm.eval.bpb_corpus import load_documents, corpus_digest


def rolling_hashes(tokens, width):
    mask, base = (1 << 64) - 1, 1000003
    if len(tokens) < width:
        return
    high = pow(base, width - 1, 1 << 64)
    value = 0
    for t in tokens[:width]:
        value = (value * base + int(t) + 1) & mask
    yield value, 0
    for i in range(width, len(tokens)):
        value = ((value - (int(tokens[i - width]) + 1) * high) * base
                 + int(tokens[i]) + 1) & mask
        yield value, i - width + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--squad", default=str(ROOT / "datasets/squad/train-v2.0.json"))
    ap.add_argument("--text-jsonl", default=None)
    ap.add_argument("--max-docs", type=int, default=4000)
    ap.add_argument("--train-bin", nargs="+", required=True)
    ap.add_argument("--tokenizer", required=True, help="train.bin을 만든 실제 tokenizer.json")
    ap.add_argument("--ngram", type=int, default=13)
    ap.add_argument("--chunk-tokens", type=int, default=262144)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.ngram < 2 or a.chunk_tokens < a.ngram:
        ap.error("ngram/chunk 범위 오류")
    if Path(a.out).exists():
        ap.error("출력 파일이 존재함")
    import numpy as np
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(a.tokenizer)
    docs = load_documents(a.text_jsonl or a.squad, squad=not bool(a.text_jsonl),
                          limit=a.max_docs)
    targets = defaultdict(list)
    short = []
    for doc in docs:
        ids = tok.encode(doc["text"], add_special_tokens=False).ids
        if len(ids) < a.ngram:
            short.append(doc["id"])
        for key, start in rolling_hashes(ids, a.ngram):
            targets[key].append((doc["id"], tuple(ids[start:start + a.ngram])))
    if not targets:
        raise ValueError("비교할 n-gram이 없음")
    keys = np.array(sorted(targets), dtype=np.uint64)
    excluded, matches, streams = set(), [], []
    for name in a.train_bin:
        path = Path(name)
        meta_path = path.parent / "meta.json"
        if not meta_path.is_file():
            raise ValueError(f"{meta_path}: token_dtype를 추정하지 않음")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        dtype = np.dtype(meta.get("token_dtype", "uint16"))
        if dtype.kind != "u" or dtype.itemsize not in (2, 4):
            raise ValueError(f"지원하지 않는 token dtype: {dtype}")
        if path.stat().st_size % dtype.itemsize:
            raise ValueError(f"깨진 token stream 크기: {path}")
        stream = np.memmap(path, dtype=dtype, mode="r")
        if len(stream) < a.ngram:
            raise ValueError(f"train stream이 n-gram보다 짧음: {path}")
        scanned = 0
        for start in range(0, len(stream) - a.ngram + 1, a.chunk_tokens):
            count = min(a.chunk_tokens, len(stream) - a.ngram + 1 - start)
            # 청크 경계 너머 width-1개를 읽어 경계 n-gram도 빠짐없이 검사한다.
            block = np.asarray(stream[start:start + count + a.ngram - 1], dtype=np.uint64)
            hashes = np.zeros(count, dtype=np.uint64)
            with np.errstate(over="ignore"):
                for k in range(a.ngram):
                    hashes = hashes * np.uint64(1000003) + block[k:k + count] + np.uint64(1)
            positions = np.searchsorted(keys, hashes)
            bounded = np.minimum(positions, len(keys) - 1)
            hits = np.flatnonzero((positions < len(keys)) & (keys[bounded] == hashes))
            for pos in hits:
                window = tuple(int(x) for x in block[pos:pos + a.ngram])
                for ident, target in targets[int(hashes[pos])]:
                    if ident not in excluded and window == target:
                        excluded.add(ident)
                        matches.append({"id": ident, "stream": str(path.resolve()),
                                        "token_offset": start + int(pos)})
            scanned += count
        streams.append({"path": str(path.resolve()), "sha256": sha256_file(path),
                        "meta_sha256": sha256_file(meta_path), "dtype": dtype.name,
                        "tokens": len(stream), "windows_scanned": scanned})
        del stream
    result = {"schema": "tinylm.bpb-exclusion.v1", "corpus_sha256": corpus_digest(docs),
              "document_count": len(docs), "excluded_ids": sorted(excluded),
              "matches": matches, "scan_complete": True, "streams": streams,
              "tokenizer_sha256": tokenizer_digest(tok), "ngram": a.ngram,
              "too_short_ids": short, "method": "all token n-grams, verified exact after hash",
              "scope": "lexical token overlap for explicitly supplied streams; not semantic leakage proof"}
    write_json_new(a.out, result)
    print(f"문서 {len(docs)}, 제외 {len(excluded)}, 짧아서 n-gram 불가 {len(short)} -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
