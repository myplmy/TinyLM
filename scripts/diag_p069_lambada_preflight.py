#!/usr/bin/env python3
"""P069 Stage0bW: read-only, exact two-seed LAMBADA input contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from check_run_registry import IDENTITY

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets" / "bench" / "lambada.jsonl"
OUTPUT = ROOT / "runs" / "bench" / "p069_stage0bw_lambada_s2_s3.jsonl"
TAGS = ("mC_initonly_s2", "mC_initonly_s3")
SEEDS = (2024, 777)
STEM = "m100R1c_ko-en_300M_"
EXPECTED_ROWS = 5153


def exact_regular(path: Path) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"missing, linked or non-regular input: {path.relative_to(ROOT)}")
    real = path.resolve(strict=True)
    if not real.is_relative_to(ROOT):
        raise ValueError("input leaves repository")
    return real


def check_pair(first: dict, second: dict) -> None:
    required = {
        "preset": "m100R1c", "data": "ko-en", "arch": "tied",
        "steps": 2289, "micro_bs": 8, "accum": 16, "seq": 1024,
        "pool_tokens": 600000000, "kd": False, "grad_ckpt": False,
        "sched": "wsd", "anneal_end": 0.8,
    }
    for item, seed in ((first, SEEDS[0]), (second, SEEDS[1])):
        for key, value in required.items():
            if item.get(key) != value:
                raise ValueError(f"non-matched or unexpected {key}: {item.get(key)!r}")
        if item.get("seed") != seed or not isinstance(item.get("final"), dict):
            raise ValueError("seed or final metadata invalid")
        if item.get("tokens") != item["steps"] * item["micro_bs"] * item["accum"] * item["seq"]:
            raise ValueError("actual training draw formula mismatch")
    mismatches = [key for key in IDENTITY if first.get(key) != second.get(key)]
    if mismatches:
        raise ValueError("two-seed identity mismatch: " + ",".join(mismatches))
    if first.get("seed") == second.get("seed"):
        raise ValueError("seed panel reused one seed")


def census(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    count = 0
    with exact_regular(path).open("rb") as stream:
        for raw in stream:
            digest.update(raw)
            value = json.loads(raw)
            body = value.get("text") if isinstance(value, dict) else None
            if not isinstance(body, str) or " " not in body.strip():
                raise ValueError(f"LAMBADA row {count}: non-text or no final word")
            count += 1
    if count != EXPECTED_ROWS:
        raise ValueError(f"LAMBADA rows {count} != {EXPECTED_ROWS}")
    return count, digest.hexdigest().upper()


def self_test() -> None:
    base = {"preset": "m100R1c", "data": "ko-en", "arch": "tied",
            "steps": 2289, "micro_bs": 8, "accum": 16, "seq": 1024,
            "tokens": 300023808, "pool_tokens": 600000000,
            "kd": False, "grad_ckpt": False, "sched": "wsd",
            "anneal_end": 0.8, "seed": 2024, "final": {}}
    other = dict(base, seed=777)
    check_pair(base, other)
    for variant in (dict(other, grad_ckpt=True), dict(other, steps=763),
                    dict(other, seed=2024)):
        try:
            check_pair(base, variant)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid LAMBADA seed pair accepted")
    print("[PASS] P069 LAMBADA matched-seed and mismatch fixtures; model NOT_RUN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            return 0
        if OUTPUT.exists() or OUTPUT.is_symlink():
            raise FileExistsError(f"write-once output exists: {OUTPUT.relative_to(ROOT)}")
        rows = []
        for tag in TAGS:
            stem = STEM + tag
            exact_regular(ROOT / "runs" / "ckpt" / (stem + ".pt"))
            record = ROOT / "runs" / "logs" / (stem + ".json")
            rows.append(json.loads(exact_regular(record).read_text(encoding="utf-8")))
            if rows[-1].get("tag") != stem:
                raise ValueError(f"run JSON tag mismatch: {tag}")
        check_pair(*rows)
        count, digest = census(DATA)
        print(f"[PASS] P069 LAMBADA asset rows={count} sha256={digest}")
        print("[PASS] s2/s3 fixed preset/pool/draw/tokenizer family/parent/grad-ckpt; only seed differs")
        print("[LIMIT] historical mC_initonly/s2 is not a seed-only pair; model/GPU NOT_RUN")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[FAIL] P069 preflight: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
