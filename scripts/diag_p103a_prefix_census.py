#!/usr/bin/env python3
"""P103A X1 exact serialized-token prefix census for public SFT only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
READY = ROOT / "HF" / "sft_ready"
TOKENIZERS = ROOT / "data_cache"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def scoped(path: Path, base: Path, suffix: str) -> Path:
    if path.is_symlink():
        raise ValueError(f"symlink is not allowed: {path}")
    real = path.resolve(strict=True)
    if real.parent != base.resolve() or not real.is_file() or not real.name.endswith(suffix):
        raise ValueError(f"expected {suffix} directly under {base}: {path}")
    return real


def common_prefix(a: list[int], b: list[int]) -> int:
    matched = 0
    for left, right in zip(a, b):
        if left != right:
            break
        matched += 1
    return matched


def census(token_rows: list[list[int]], *, min_prefix: int = 128,
           max_branches: int = 4) -> dict:
    if min_prefix < 1 or max_branches < 2:
        raise ValueError("invalid X1 prefix/branch settings")
    total = sum(len(row) for row in token_rows)
    buckets: dict[tuple[int, ...], list[list[int]]] = {}
    for row in token_rows:
        if len(row) >= min_prefix:
            buckets.setdefault(tuple(row[:min_prefix]), []).append(row)
    saved = groups = grouped_rows = 0
    for bucket in buckets.values():
        if len(bucket) < 2:
            continue
        ordered = sorted(bucket)
        for begin in range(0, len(ordered), max_branches):
            part = ordered[begin:begin + max_branches]
            if len(part) < 2:
                continue
            length = common_prefix(part[0], part[-1])
            if length >= min_prefix:
                saved += (len(part) - 1) * length
                groups += 1
                grouped_rows += len(part)
    return {"rows": len(token_rows), "serialized_tokens": total,
            "grouped_rows": grouped_rows, "groups": groups,
            "shareable_token_occurrences": saved,
            "hypothetical_token_work_reduction": (saved / total if total else 0.0),
            "min_prefix": min_prefix, "max_branches": max_branches}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path)
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--tokenizer", type=Path)
    ap.add_argument("--min-prefix", type=int, default=128)
    ap.add_argument("--max-branches", type=int, default=4)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        sample = census([[1, 2, 3, 4, 5], [1, 2, 3, 4, 6], [9, 8]],
                        min_prefix=3, max_branches=4)
        assert sample["shareable_token_occurrences"] == 4
        assert sample["groups"] == 1 and sample["rows"] == 3
        assert census([[1, 2], [1, 3]], min_prefix=3)["groups"] == 0
        print("[PASS] P103A exact-token prefix census fixture; model/GPU NOT_RUN")
        return 0
    if not args.input or not args.manifest or not args.tokenizer:
        ap.error("--input, --manifest and --tokenizer are required")
    source = scoped(args.input, READY, ".canonical.jsonl")
    manifest_path = scoped(args.manifest, READY, "_manifest.json")
    tokenizer_path = scoped(args.tokenizer, TOKENIZERS, ".json")
    if source.name.endswith("_train.canonical.jsonl"):
        split, prefix = "train", source.name.removesuffix("_train.canonical.jsonl")
    elif source.name.endswith("_val.canonical.jsonl"):
        split, prefix = "val", source.name.removesuffix("_val.canonical.jsonl")
    else:
        raise ValueError("input must be a canonical train or val split")
    if manifest_path.name != prefix + "_manifest.json":
        raise ValueError("manifest and canonical split prefix differ")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "TINYLM_PUBLIC_SFT_V1":
        raise ValueError("public SFT manifest schema differs")
    if manifest.get("output_sha256", {}).get(split) != file_sha256(source):
        raise ValueError("canonical split SHA256 differs from manifest")
    token_meta = manifest.get("token_filter", {})
    if token_meta.get("tokenizer_sha256") != file_sha256(tokenizer_path):
        raise ValueError("tokenizer SHA256 differs from manifest")
    from tokenizers import Tokenizer
    from tinylm.data.sft import encode_conversation, load_canonical
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    rows = load_canonical(source)
    token_rows = [encode_conversation(row, tokenizer, "chatml")[0] for row in rows]
    result = census(token_rows, min_prefix=args.min_prefix, max_branches=args.max_branches)
    result["corpus_sha256"] = manifest["output_sha256"][split]
    result["tokenizer_sha256"] = token_meta["tokenizer_sha256"]
    result["contamination_gate"] = manifest.get("contamination_gate", "NOT_RUN")
    result["claim"] = "CORPUS_STRUCTURE_ONLY_NOT_WALL_OR_TRAIN_READY"
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
