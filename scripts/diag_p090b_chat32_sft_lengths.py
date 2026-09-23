#!/usr/bin/env python3
"""P090B chat32 re-encoding length census for pinned public SFT; no raw text."""
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


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            sha.update(block)
    return sha.hexdigest().upper()


def measure(lengths: list[int], *, max_seq: int) -> dict:
    if max_seq < 1 or not lengths:
        raise ValueError("invalid chat32 SFT length census")
    too_long = sum(length < 2 or length - 1 > max_seq for length in lengths)
    return {"records": len(lengths), "max_tokens": max(lengths),
            "too_long": too_long, "max_seq": max_seq}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--tokenizer", type=Path)
    ap.add_argument("--max-seq", type=int, default=1024)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        assert measure([2, 1025], max_seq=1024)["too_long"] == 0
        assert measure([2, 1026], max_seq=1024)["too_long"] == 1
        print("[PASS] chat32 SFT length boundary fixture; data/model/GPU NOT_RUN")
        return 0
    if not args.manifest or not args.tokenizer:
        ap.error("--manifest and --tokenizer are required")
    manifest_path = args.manifest.resolve(strict=True)
    tokenizer_path = args.tokenizer.resolve(strict=True)
    if (args.manifest.is_symlink() or args.tokenizer.is_symlink()
            or manifest_path.parent != READY.resolve()
            or tokenizer_path.parent != TOKENIZERS.resolve()
            or not manifest_path.name.endswith("_manifest.json")
            or not tokenizer_path.name.endswith("-chat32.json")):
        raise ValueError("chat32 SFT input scope or suffix is invalid")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "TINYLM_PUBLIC_SFT_V1":
        raise ValueError("manifest schema mismatch")
    from tokenizers import Tokenizer
    from tinylm.data.prepare import verify_chat_tokenizer
    from tinylm.data.sft import encode_conversation, load_canonical
    tok = Tokenizer.from_file(str(tokenizer_path))
    verify_chat_tokenizer(tok, 32768)
    prefix = manifest_path.name.removesuffix("_manifest.json")
    reports = {}
    for split in ("train", "val"):
        candidate = READY / f"{prefix}_{split}.canonical.jsonl"
        if candidate.is_symlink() or not candidate.is_file():
            raise ValueError(f"{split} canonical input missing or linked")
        if manifest.get("output_sha256", {}).get(split) != digest(candidate):
            raise ValueError(f"{split} canonical SHA256 mismatch")
        rows = load_canonical(candidate)
        lengths = [len(encode_conversation(row, tok, "chatml")[0]) for row in rows]
        reports[split] = measure(lengths, max_seq=args.max_seq)
    result = {"schema": "P090B_CHAT32_LENGTH_V1",
              "tokenizer_sha256": digest(tokenizer_path),
              "train": reports["train"], "val": reports["val"],
              "contamination_gate": manifest.get("contamination_gate", "NOT_RUN"),
              "claim": "LENGTH_ONLY_NOT_TRAIN_READY"}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if reports["train"]["too_long"] or reports["val"]["too_long"]:
        print("[GATE NEGATIVE] same canonical corpus does not fit chat32 context")
        return 8
    print("[PASS] chat32 length only; corpus quality and parent model NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
