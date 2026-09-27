#!/usr/bin/env python3
"""P037 Stage0Wb: build an isolated 300M common-val cache from existing public caches.

This is a user-run CPU/data task. It never downloads, edits legacy caches, or
reads protected TinyDataset. It does not establish model quality or SFT readiness.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from diag_p037_common_val import CACHE, exact_cache, sha256_file


SOURCE = "ko-en_300000000"
VAL_SOURCE = "ko-en_600000000"
OUTPUT_NAME = "ko-en-commonval-v1"
OUTPUT = CACHE / f"{OUTPUT_NAME}_300000000"
TOKENIZER_SOURCE = CACHE / "tok-ko-en-32768.json"
TOKENIZER_OUTPUT = CACHE / f"tok-{OUTPUT_NAME}-32768.json"
PINNED_VAL_SHA = "1AE1C68DE18402CE1FFC44EA54D68DD5768B9F7082FA2EEE8E8F2F433BC4FF0B"
PINNED_TOKENIZER_SHA = "3A69001ECC28A5BDF1E951A1036B234C9BDCB847B310252C6D72CFC6C52C48E3"
TARGET_TRAIN = 297_000_000
TARGET_VAL = 3_000_000
CHUNK = 1_000_000


def regular_file(path: Path) -> None:
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode) or path.stat().st_nlink != 1:
        raise ValueError(f"input is not an independent regular file: {path}")


def all_doc_spans(arr: np.ndarray, eos: int):
    """Unlike the historical census, retain even one-token EOS documents."""
    start = 0
    for offset in range(0, len(arr), CHUNK):
        for local in np.flatnonzero(np.asarray(arr[offset:offset + CHUNK]) == eos):
            end = offset + int(local) + 1
            yield start, end
            start = end
    if start < len(arr):
        yield start, len(arr)


def digest_span(arr: np.ndarray, start: int, end: int) -> bytes:
    digest = hashlib.sha256()
    for offset in range(start, end, CHUNK):
        digest.update(np.asarray(arr[offset:min(offset + CHUNK, end)]).tobytes())
    return digest.digest()


def occurs_in_val(fragment: np.ndarray, val: np.ndarray) -> bool:
    """Check the one possible cut document for exact substring leakage."""
    width = len(fragment)
    if not width or width > len(val):
        return False
    first = int(fragment[0])
    for offset in range(0, len(val) - width + 1, CHUNK):
        limit = min(offset + CHUNK, len(val) - width + 1)
        for local in np.flatnonzero(np.asarray(val[offset:limit]) == first):
            start = offset + int(local)
            if np.array_equal(val[start:start + width], fragment):
                return True
    return False


def select_train(train: np.ndarray, val: np.ndarray, eos: int,
                 target: int) -> tuple[list[tuple[int, int]], dict]:
    reference = {digest_span(val, start, end) for start, end in all_doc_spans(val, eos)}
    selected: list[tuple[int, int]] = []
    written = removed_docs = removed_tokens = truncated = 0
    scanned = 0
    for start, end in all_doc_spans(train, eos):
        scanned += 1
        if digest_span(train, start, end) in reference:
            removed_docs += 1
            removed_tokens += end - start
            continue
        remaining = target - written
        if remaining == 0:
            break
        take = min(end - start, remaining)
        if take < end - start:
            # A truncated terminal document is not covered by full-doc hashes.
            # Pick a later document if this exact fragment occurs anywhere in val.
            if occurs_in_val(train[start:start + take], val):
                continue
            truncated = 1
        selected.append((start, start + take))
        written += take
        if written == target:
            break
    if written != target:
        raise ValueError(f"insufficient disjoint train tokens: {written} < {target}")
    # Exhaustive count rather than only the selected prefix: it documents the
    # source overlap that motivates this branch without changing legacy data.
    all_removed = all_removed_tokens = all_scanned = 0
    for start, end in all_doc_spans(train, eos):
        all_scanned += 1
        if digest_span(train, start, end) in reference:
            all_removed += 1
            all_removed_tokens += end - start
    return selected, {
        "source_docs": all_scanned, "selected_scan_docs": scanned,
        "source_overlap_docs": all_removed,
        "source_overlap_tokens": all_removed_tokens,
        "selected_overlap_docs": removed_docs,
        "selected_overlap_tokens": removed_tokens,
        "terminal_truncated_doc": truncated,
        "selected_train_tokens": written,
    }


def copy_tokens(arr: np.ndarray, spans: list[tuple[int, int]], path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("xb") as stream:
        for start, end in spans:
            for offset in range(start, end, CHUNK):
                block = np.asarray(arr[offset:min(offset + CHUNK, end)]).tobytes()
                stream.write(block)
                digest.update(block)
        stream.flush()
        os.fsync(stream.fileno())
    return digest.hexdigest().upper()


def preflight() -> tuple[Path, Path, dict, dict, int]:
    source_dir, source_meta = exact_cache(SOURCE)
    val_dir, val_meta = exact_cache(VAL_SOURCE)
    for path in (TOKENIZER_SOURCE, source_dir / "train.bin", val_dir / "val.bin"):
        regular_file(path)
    if source_meta.get("train") != 298_500_000 or val_meta.get("val") != TARGET_VAL:
        raise ValueError("legacy train/common-val size drifted from preregistration")
    if not isinstance(val_meta.get("bytes_per_token"), (int, float)) or val_meta["bytes_per_token"] <= 0:
        raise ValueError("common-val bytes_per_token missing")
    if sha256_file(TOKENIZER_SOURCE) != PINNED_TOKENIZER_SHA:
        raise ValueError("legacy tokenizer SHA differs from Stage0W evidence")
    if sha256_file(val_dir / "val.bin") != PINNED_VAL_SHA:
        raise ValueError("common val SHA differs from Stage0W evidence")
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError(f"write-once output exists, inspect it without overwriting: {OUTPUT}")
    if TOKENIZER_OUTPUT.exists() or TOKENIZER_OUTPUT.is_symlink():
        raise FileExistsError(f"write-once tokenizer exists, inspect it without overwriting: {TOKENIZER_OUTPUT}")
    if shutil.disk_usage(CACHE).free < 2 * 1024**3:
        raise OSError("less than 2 GiB free for isolated 300M uint16 cache")
    from tinylm.data import load_tokenizer
    eos = load_tokenizer("ko-en").token_to_id("<eos>")
    if eos is None:
        raise ValueError("legacy tokenizer has no EOS id")
    return source_dir, val_dir, source_meta, val_meta, int(eos)


def build() -> None:
    source_dir, val_dir, source_meta, val_meta, eos = preflight()
    train_path = source_dir / "train.bin"
    val_path = val_dir / "val.bin"
    train_sha_before = sha256_file(train_path)
    train = np.memmap(train_path, dtype=np.uint16, mode="r")
    val = np.memmap(val_path, dtype=np.uint16, mode="r")
    selected, census = select_train(train, val, eos, TARGET_TRAIN)
    print(json.dumps({"schema": "P037_STAGE0WB_PLAN_V1", "census": census,
                      "output": str(OUTPUT), "source_train_sha256": train_sha_before,
                      "common_val_sha256": PINNED_VAL_SHA}, sort_keys=True), flush=True)
    OUTPUT.mkdir(exist_ok=False)
    out_train_sha = copy_tokens(train, selected, OUTPUT / "train.bin")
    out_val_sha = copy_tokens(val, [(0, len(val))], OUTPUT / "val.bin")
    if out_val_sha != PINNED_VAL_SHA or sha256_file(train_path) != train_sha_before:
        raise ValueError("source drift during copy; partial output is intentionally retained")
    out_train = np.memmap(OUTPUT / "train.bin", dtype=np.uint16, mode="r")
    reference = {digest_span(val, start, end) for start, end in all_doc_spans(val, eos)}
    after_overlap = sum(digest_span(out_train, start, end) in reference
                        for start, end in all_doc_spans(out_train, eos))
    if (after_overlap or len(out_train) != TARGET_TRAIN or len(val) != TARGET_VAL
            or sha256_file(OUTPUT / "train.bin") != out_train_sha):
        raise ValueError("output verification failed; partial output is intentionally retained")
    with TOKENIZER_SOURCE.open("rb") as reader, TOKENIZER_OUTPUT.open("xb") as writer:
        shutil.copyfileobj(reader, writer)
        writer.flush()
        os.fsync(writer.fileno())
    if sha256_file(TOKENIZER_OUTPUT) != PINNED_TOKENIZER_SHA:
        raise ValueError("tokenizer copy mismatch; partial output is intentionally retained")
    meta = {
        "data": OUTPUT_NAME, "tokens": TARGET_TRAIN + TARGET_VAL,
        "train": TARGET_TRAIN, "val": TARGET_VAL, "vocab": 32768,
        "token_dtype": "uint16", "dir": str(OUTPUT),
        "bytes_per_token": val_meta["bytes_per_token"],
        "p037_contract": "Stage0Wb common-val exact-document disjoint; terminal fragment exact-substring checked",
        "p037_source_train": SOURCE, "p037_source_val": VAL_SOURCE,
        "p037_source_train_sha256": train_sha_before,
        "p037_source_val_sha256": PINNED_VAL_SHA,
        "p037_tokenizer_sha256": PINNED_TOKENIZER_SHA,
        "p037_output_train_sha256": out_train_sha,
        "p037_output_val_sha256": out_val_sha,
        "p037_output_full_doc_overlap": after_overlap,
        "p037_census": census,
    }
    # meta.json last: prepare(exact=True) treats its presence as a complete cache.
    with (OUTPUT / "meta.json").open("x", encoding="utf-8") as stream:
        json.dump(meta, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"schema": "P037_STAGE0WB_CACHE_V1", "output": str(OUTPUT),
                      "train_tokens": TARGET_TRAIN, "val_tokens": TARGET_VAL,
                      "full_doc_overlap": after_overlap, "census": census,
                      "train_sha256": out_train_sha, "val_sha256": out_val_sha,
                      "tokenizer_sha256": PINNED_TOKENIZER_SHA,
                      "limit": "cache construction only; SFT/multiturn training and quality NOT_RUN"},
                     sort_keys=True))


def self_test() -> None:
    # In-memory fixture only: never opens or creates a real cache.
    train = np.array([1, 2, 9, 3, 4, 9, 5, 6, 9, 7, 8, 9], dtype=np.uint16)
    val = np.array([3, 4, 9, 10, 11, 9], dtype=np.uint16)
    selected, census = select_train(train, val, 9, 8)
    output = np.concatenate([train[start:end] for start, end in selected])
    assert output.tolist() == [1, 2, 9, 5, 6, 9, 7, 8]
    assert census["source_overlap_docs"] == 1 and census["selected_train_tokens"] == 8
    assert occurs_in_val(np.array([3, 4], dtype=np.uint16), val)
    assert not occurs_in_val(np.array([7, 8], dtype=np.uint16), val)
    # Full documents differ, but the first candidate's truncated prefix occurs
    # inside val. The selector must skip it and use a later safe fragment.
    train2 = np.array([1, 2, 9, 3, 4, 5, 9, 6, 7, 9], dtype=np.uint16)
    val2 = np.array([0, 3, 4, 8, 9], dtype=np.uint16)
    spans2, census2 = select_train(train2, val2, 9, 5)
    assert np.concatenate([train2[start:end] for start, end in spans2]).tolist() == [1, 2, 9, 6, 7]
    assert census2["terminal_truncated_doc"] == 1
    try:
        select_train(train2, val2, 9, 11)
    except ValueError as exc:
        assert "insufficient" in str(exc)
    else:
        raise AssertionError("insufficient source tokens were accepted")
    print("[PASS] P037 Stage0Wb in-memory exclusion/copy plan; real cache NOT_RUN")


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
        elif args.check_only:
            source_dir, val_dir, source_meta, val_meta, eos = preflight()
            print(json.dumps({"schema": "P037_STAGE0WB_PREFLIGHT_V1",
                              "source": source_dir.name, "source_train": source_meta["train"],
                              "val_source": val_dir.name, "val_tokens": val_meta["val"],
                              "eos_id": eos, "output": str(OUTPUT),
                              "note": "no cache written; train exclusion capacity unverified"}, sort_keys=True))
        else:
            build()
        return 0
    except (AssertionError, FileExistsError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"[STOP] P037 Stage0Wb: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
