#!/usr/bin/env python3
"""P037 Stage0W: read-only real-cache common-val and stream-order census.

No source download, cache creation, model loading, or protected TinyDataset access.
The 600M cache's existing val is a *candidate* for B/A, not adopted here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CACHE = ROOT / "data_cache"
NAMES = ("ko-en_300000000", "ko-en_600000000")
CHUNK = 1_000_000


def exact_cache(name: str) -> tuple[Path, dict]:
    if name not in NAMES:
        raise ValueError("cache name outside preregistered 300M/600M control")
    directory = CACHE / name
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"cache directory missing or linked: {name}")
    for leaf in ("meta.json", "train.bin", "val.bin"):
        path = directory / leaf
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"cache input missing or linked: {name}/{leaf}")
    meta = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
    requested = int(name.rsplit("_", 1)[-1])
    if (meta.get("data") != "ko-en" or meta.get("tokens") != requested
            or meta.get("train", -1) + meta.get("val", -1) != requested):
        raise ValueError(f"metadata token/data mismatch: {name}")
    for leaf, field in (("train.bin", "train"), ("val.bin", "val")):
        if (directory / leaf).stat().st_size != int(meta[field]) * 2:
            raise ValueError(f"uint16 byte count mismatch: {name}/{leaf}")
    return directory, meta


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def doc_spans(arr: np.ndarray, eos: int):
    start = 0
    for offset in range(0, len(arr), CHUNK):
        block = np.asarray(arr[offset:offset + CHUNK])
        for local in np.flatnonzero(block == eos):
            end = offset + int(local) + 1
            if end - start >= 2:
                yield start, end
            start = end
    if len(arr) - start >= 2:
        yield start, len(arr)


def doc_hashes(arr: np.ndarray, eos: int) -> tuple[set[bytes], int, int]:
    hashes: set[bytes] = set()
    count = 0
    maximum = 0
    for start, end in doc_spans(arr, eos):
        hashes.add(hashlib.sha256(arr[start:end].tobytes()).digest())
        maximum = max(maximum, end - start)
        count += 1
    return hashes, count, maximum


def count_overlap(arr: np.ndarray, eos: int, reference: set[bytes]) -> tuple[int, int]:
    matched = count = 0
    for start, end in doc_spans(arr, eos):
        matched += hashlib.sha256(arr[start:end].tobytes()).digest() in reference
        count += 1
    return matched, count


def unigram(arr: np.ndarray) -> np.ndarray:
    counts = np.bincount(np.asarray(arr, dtype=np.int64), minlength=32768).astype(np.float64)
    return counts / max(counts.sum(), 1.0)


def js_nats(left: np.ndarray, right: np.ndarray) -> float:
    midpoint = (left + right) / 2.0
    def kl(part):
        mask = part > 0
        return float(np.sum(part[mask] * np.log(part[mask] / midpoint[mask])))
    return (kl(left) + kl(right)) / 2.0


def self_test() -> None:
    arr = np.array([1, 2, 7, 3, 4, 7, 9, 8], dtype=np.uint16)
    assert list(doc_spans(arr, 7)) == [(0, 3), (3, 6), (6, 8)]
    reference, count, maximum = doc_hashes(arr[:6], 7)
    assert count == 2 and maximum == 3
    assert count_overlap(arr, 7, reference) == (2, 3)
    a = unigram(arr)
    b = unigram(np.array([1, 1, 1], dtype=np.uint16))
    assert math.isclose(js_nats(a, a), 0.0, abs_tol=1e-12)
    assert js_nats(a, b) > 0
    print("[PASS] P037 document-boundary/hash/JS and invalid-cache contracts; real caches NOT_RUN")


def audit_caches() -> int:
    entries = [exact_cache(name) for name in NAMES]
    from tinylm.data import load_tokenizer, tokenizer_path
    tok_path = tokenizer_path("ko-en")
    if tok_path.is_symlink() or not tok_path.is_file():
        raise ValueError("legacy ko-en tokenizer absent or linked")
    tokenizer = load_tokenizer("ko-en")
    eos = tokenizer.token_to_id("<eos>")
    if eos is None:
        raise ValueError("legacy tokenizer has no eos token")
    arrays = [
        (np.memmap(directory / "train.bin", dtype=np.uint16, mode="r"),
         np.memmap(directory / "val.bin", dtype=np.uint16, mode="r"))
        for directory, _ in entries
    ]
    common_val_hashes, common_count, common_max = doc_hashes(arrays[1][1], eos)
    val_hist = [unigram(pair[1]) for pair in arrays]
    rows = []
    for (directory, meta), (train, val) in zip(entries, arrays):
        overlap, scanned = count_overlap(train, eos, common_val_hashes)
        head = unigram(train[:min(len(train), CHUNK)])
        tail = unigram(train[-min(len(train), CHUNK):])
        rows.append({
            "cache": directory.name, "tokens": meta["tokens"],
            "train_tokens": meta["train"], "val_tokens": meta["val"],
            "val_sha256": sha256_file(directory / "val.bin"),
            "common_val_doc_overlap_in_train": overlap,
            "train_docs_scanned": scanned,
            "train_head_tail_js_nats": js_nats(head, tail),
            "train_tail_vs_own_val_js_nats": js_nats(tail, val_hist[len(rows)]),
        })
    result = {
        "schema": "P037_STAGE0W_CACHE_AUDIT_V1",
        "eos_id": eos, "tokenizer_sha256": sha256_file(tok_path),
        "common_val_source": NAMES[1], "common_val_docs": common_count,
        "common_val_max_doc_fraction": common_max / max(len(arrays[1][1]), 1),
        "val_300_vs_600_js_nats": js_nats(*val_hist),
        "val_byte_identical": rows[0]["val_sha256"] == rows[1]["val_sha256"],
        "rows": rows,
        "limit": "same token IDs only; JS is distribution diagnostic, not model quality or source-language ratio",
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if any(row["common_val_doc_overlap_in_train"] for row in rows):
        print("[GATE NEGATIVE] common val overlaps current train; B/A builders must exclude these documents")
        return 8
    print("[MEASURED] cache contracts valid; B common-val-only and A shuffle builder can be designed without assuming source balance")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    try:
        if args.check_only:
            rows = [dict(cache=name, meta=exact_cache(name)[1]) for name in NAMES]
            print(json.dumps({"schema": "P037_STAGE0W_PREFLIGHT_V1", "rows": rows},
                             ensure_ascii=False, sort_keys=True))
            return 0
        return audit_caches()
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"[FAIL] P037 cache audit: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
