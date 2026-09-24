#!/usr/bin/env python3
"""P106 verifier/provenance contract; never generates teacher output or trains a model."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PROTECTED = ROOT / "datasets" / "TinyDataset"
SPLITS = frozenset({"train", "curriculum_probe", "dev", "sealed_test"})
STATUSES = frozenset({"ACCEPT", "REJECT", "UNKNOWN"})
INDEPENDENT_ORIGINS = frozenset({"independent_program", "human_review"})


def _text(row: dict, key: str, *, required: bool = True) -> str:
    value = row.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be text, never token IDs")
    if required and not value.strip():
        raise ValueError(f"{key} is empty")
    return value


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _assistant_span(prompt: str, target: str) -> None:
    from tinylm.chat.serialize import loss_spans, serialize
    conv = {"messages": [{"role": "user", "content": prompt},
                         {"role": "assistant", "content": target}],
            "meta": {"canonical_version": 1}}
    rendered = serialize(conv, "chatml")
    spans = loss_spans(conv, "chatml")
    if len(spans) != 1 or not target or target not in rendered[spans[0][0]:spans[0][1]]:
        raise ValueError("assistant target not covered by exactly one loss span")
    if spans[0][0] <= rendered.index("<|im_end|>"):
        raise ValueError("user prompt leaked into supervised span")


def audit(rows) -> dict:
    counts = Counter()
    by_id = set()
    ancestor_split = {}
    prompt_split = {}
    for row_number, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"row {row_number}: object required")
        if any(key in row for key in ("target_token_ids", "teacher_token_ids", "student_token_ids")):
            raise ValueError(f"row {row_number}: token-ID target forbidden across tokenizer lineages")
        sample_id = _text(row, "sample_id")
        family = _text(row, "family_id")
        ancestor = _text(row, "ancestor_id")
        prompt = _text(row, "prompt_text")
        teacher = _text(row, "teacher_answer_text", required=False)
        split = row.get("split")
        status = row.get("verifier_status")
        if split not in SPLITS or status not in STATUSES:
            raise ValueError(f"row {row_number}: invalid split or verifier_status")
        if sample_id in by_id:
            raise ValueError(f"row {row_number}: duplicate sample_id")
        by_id.add(sample_id)
        group = (family, ancestor)
        prompt_sha = hashlib.sha256(_normalized(prompt).encode("utf-8")).hexdigest()
        for registry, key, label in ((ancestor_split, group, "family/ancestor"),
                                     (prompt_split, prompt_sha, "normalized prompt")):
            old = registry.setdefault(key, split)
            if old != split:
                raise ValueError(f"row {row_number}: {label} crosses {old}/{split} splits")
        accepted = row.get("accepted_for_training")
        if not isinstance(accepted, bool):
            raise ValueError(f"row {row_number}: accepted_for_training must be boolean")
        target = row.get("target_text")
        if target is not None and not isinstance(target, str):
            raise ValueError(f"row {row_number}: target must be text, never token IDs")
        target = target or ""
        counts[status] += 1
        counts[f"split_{split}"] += 1
        if status != "ACCEPT":
            if target or accepted:
                raise ValueError(f"row {row_number}: rejected/unknown sample has learning target")
            continue
        origin = _text(row, "verifier_origin")
        evidence = _text(row, "verifier_evidence_id")
        verified = _text(row, "verified_answer_text")
        if origin not in INDEPENDENT_ORIGINS or not teacher.strip():
            raise ValueError(f"row {row_number}: accepted answer lacks independent claimed verifier/teacher")
        if target != verified:
            raise ValueError(f"row {row_number}: student target differs from verified answer text")
        if accepted and split != "train":
            raise ValueError(f"row {row_number}: non-train split cannot enter student loss")
        if accepted:
            if row.get("loss_mask_source") != "canonical_assistant_only":
                raise ValueError(f"row {row_number}: supervised mask provenance missing")
            _assistant_span(prompt, target)
            counts["student_supervised"] += 1
        else:
            counts["verified_not_supervised"] += 1
        if not evidence.strip():
            raise ValueError(f"row {row_number}: verifier evidence missing")
    if not by_id:
        raise ValueError("zero teacher records")
    return {"schema": "P106_VERIFIED_TEACHER_CONTRACT_V1", "counts": dict(counts),
            "split_groups": len(ancestor_split), "unique_prompts": len(prompt_split),
            "claim": "PROVENANCE_STRUCTURE_ONLY_VERIFIER_TRUTH_AND_LICENSE_NOT_RUN"}


def scoped_rows(raw: str):
    path = Path(raw)
    if path.is_symlink():
        raise ValueError("symlink input refused")
    real = path.resolve(strict=True)
    if not real.is_file() or not real.is_relative_to(ROOT) or real.is_relative_to(PROTECTED):
        raise ValueError("input must be a non-protected regular file inside repository")
    with real.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"JSONL row {number}: invalid JSON") from exc


def self_test() -> None:
    good = {"sample_id": "fixture-1", "family_id": "arithmetic", "ancestor_id": "a-1",
            "split": "train", "prompt_text": "2+2는?", "teacher_answer_text": "4",
            "verifier_status": "ACCEPT", "verifier_origin": "independent_program",
            "verifier_evidence_id": "calculator:fixture-1", "verified_answer_text": "4",
            "target_text": "4", "accepted_for_training": True,
            "loss_mask_source": "canonical_assistant_only"}
    result = audit([good])
    assert result["counts"]["student_supervised"] == 1
    rejects = [dict(good, sample_id="r", verifier_status="REJECT",
                    target_text="", accepted_for_training=False),
               dict(good, sample_id="u", verifier_status="UNKNOWN",
                    target_text="", accepted_for_training=False)]
    assert audit(rejects)["counts"].get("student_supervised", 0) == 0
    bad_cases = [dict(good, verifier_origin="teacher_self"),
                 dict(good, verifier_status="UNKNOWN"),
                 dict(good, target_text=[1, 2]),
                 dict(good, split="sealed_test"),
                 dict(good, target_text="5"),
                 dict(good, target_token_ids=[1, 2])]
    for bad in bad_cases:
        try:
            audit([bad])
        except ValueError:
            pass
        else:
            raise AssertionError("invalid verified-teacher record was accepted")
    try:
        audit([good, dict(good, sample_id="other", split="dev")])
    except ValueError:
        pass
    else:
        raise AssertionError("cross-split ancestor was accepted")
    print("[FIXTURE] accepted=1 reject=1 unknown=1; negative_cases=6, cross_split_leak=1 rejected")
    print("[PASS] P106 reject/unknown, split, text target, assistant loss provenance; teacher/model/GPU NOT_RUN")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--input-jsonl", help="read-only pre-generated teacher candidate records")
    args = ap.parse_args()
    if args.self_test == bool(args.input_jsonl):
        ap.error("choose exactly one of --self-test or --input-jsonl")
    try:
        if args.self_test:
            self_test()
            return 0
        print(json.dumps(audit(scoped_rows(args.input_jsonl)), ensure_ascii=False, sort_keys=True))
        return 0
    except (ValueError, OSError) as exc:
        print(f"[FAIL] P106 contract: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
