#!/usr/bin/env python3
"""P106B Stage2aW: read-only teacher/SFT token-budget census, not a forecast.

Separate teacher completion (including reasoning), serialized student input,
assistant supervised tokens and repeated training positions. The pinned v4
sixteen Korean candidates are a small, biased cost sample, not accepted data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tinylm.data.sft import IGNORE, encode_conversation  # noqa: E402

SOURCE = ROOT / "HF/sft_ready/p106b_teacher_sft/v4/teacher_repair_full16_candidates.jsonl"
MANIFEST = SOURCE.parent / "teacher_repair_full16_manifest.json"
TOKENIZER = ROOT / "data_cache/tok-ko-en-32768.json"
SOURCE_SHA256 = "63E7F7A1E487F10E1A1214E2C2489AD9DDD754DEDE33CA5893242CEAE983CAFA"
TOKENIZER_SHA256 = "3A69001ECC28A5BDF1E951A1036B234C9BDCB847B310252C6D72CFC6C52C48E3"
TARGETS = (300_000_000, 600_000_000)


def digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError(f"pinned regular asset absent or linked: {path}")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest().upper()


def budget(whole: int, supervised: int, teacher_tokens: int, wall_sec: float) -> dict:
    if min(whole, supervised, teacher_tokens) <= 0 or wall_sec <= 0:
        raise ValueError("cost sample must have positive tokens and wall time")
    result = {}
    for target in TARGETS:
        result[str(target)] = {
            "nominal_steps_if_full_seq1024_micro8_accum16":
                (target + 131_072 - 1) // 131_072,
            "unique_student_canonical_tokens_if_one_epoch": target,
            "unique_student_canonical_tokens_if_four_epochs_at_least":
                (target + 3) // 4,
            "naive_teacher_days_for_unique_one_epoch_at_v4_ratio":
                round(target * wall_sec / whole / 86_400, 1),
            "naive_teacher_days_for_unique_four_epoch_floor_at_v4_ratio":
                round(((target + 3) // 4) * wall_sec / whole / 86_400, 1),
        }
    return {"student_canonical_sample": whole,
            "assistant_supervised_sample": supervised,
            "teacher_completion_sample": teacher_tokens,
            "teacher_wall_sample_sec": wall_sec,
            "teacher_completion_per_canonical": round(teacher_tokens / whole, 3),
            "assistant_supervised_fraction": round(supervised / whole, 4),
            "targets": result}


def self_test() -> None:
    value = budget(2_000, 1_000, 18_000, 280.0)
    assert value["targets"]["300000000"]["nominal_steps_if_full_seq1024_micro8_accum16"] == 2289
    assert value["targets"]["600000000"]["unique_student_canonical_tokens_if_four_epochs_at_least"] == 150_000_000
    assert value["teacher_completion_per_canonical"] == 9.0
    print("[PASS] four token denominators and 300M/600M arithmetic; model/GPU/data writes NOT_RUN")


def check_only() -> None:
    from tokenizers import Tokenizer

    if digest(SOURCE) != SOURCE_SHA256 or digest(TOKENIZER) != TOKENIZER_SHA256:
        raise ValueError("pinned v4 source or legacy student tokenizer SHA differs")
    if MANIFEST.is_symlink() or not MANIFEST.is_file():
        raise FileNotFoundError("v4 manifest absent or linked")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("raw_sha256") != SOURCE_SHA256 or manifest.get("rows") != 16:
        raise ValueError("v4 manifest source/count mismatch")
    rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != 16 or any(row.get("format_status") != "JSON_COMPLETE" for row in rows):
        raise ValueError("v4 expected sixteen structurally complete candidates")
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    whole = supervised = teacher_tokens = 0
    max_row = 0
    for row in rows:
        candidate = row["parsed_candidate"]
        conv = {"messages": [{"role": "user", "content": candidate["user_ko"]},
                             {"role": "assistant", "content": candidate["assistant_ko"]}]}
        ids, labels, _ = encode_conversation(conv, tokenizer, "chatml")
        whole += len(ids)
        supervised += sum(label != IGNORE for label in labels)
        max_row = max(max_row, len(ids))
        tokens = row.get("usage", {}).get("completion_tokens")
        if type(tokens) is not int or tokens < 0:
            raise ValueError("teacher usage incomplete")
        teacher_tokens += tokens
    elapsed = manifest.get("elapsed_sec")
    if not isinstance(elapsed, (int, float)):
        raise ValueError("teacher wall missing")
    report = {"schema": "P106B_STAGE2AW_SCALE_PREFLIGHT_V1",
              "source_sha256": SOURCE_SHA256,
              "student_tokenizer_sha256": TOKENIZER_SHA256,
              "sample_rows": len(rows), "sample_language": "ko_only",
              "sample_max_serialized_row_tokens": max_row,
              "sample_truth_status": "UNVERIFIED_WITH_KNOWN_DEFECTS",
              "english_sample": "NOT_RUN",
              "report": budget(whole, supervised, teacher_tokens, float(elapsed)),
              "warning": "V4 simple extrapolation is not a throughput forecast; format, batching, reasoning, English mix and reject rate differ. No unique 300M/600M corpus exists."}
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    print("[CHECK_ONLY] sampled denominators; teacher/large corpus/student GPU NOT_RUN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        check_only()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
