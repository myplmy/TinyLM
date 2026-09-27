#!/usr/bin/env python3
"""P106B Stage2dW: versioned tagged-teacher -> canonical SFT pilot materializer.

Only the pinned Stage2cW sixteen-case paired format panel is accepted here.
The teacher raw file is immutable and remains separate. Canonical records
contain final question/answer plus a SHA-bound reasoning sidecar reference,
never an active thinking block. Split, dedup, tokenize and <=20MB sharding are
code-owned. This is a tiny pilot dataset, not the 300M/600M corpus.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.diag_p106_bonsai_assets import regular, sha256_file  # noqa: E402
from scripts.diag_p106_oasst2_teacher_ko_gate import MODEL_SHA256  # noqa: E402
from scripts.diag_p106b_teacher_tagged_pair import OUTPUT as V6_RAW, MANIFEST as V6_MANIFEST, V4_SHA256  # noqa: E402
from scripts.p106b_shards import ShardWriter, verify  # noqa: E402
from scripts.p106b_teacher_wrapper import wrap_turns  # noqa: E402
from tinylm.data.sft import IGNORE, conversation_split_key, encode_conversation  # noqa: E402

V7_DIR = ROOT / "HF/sft_ready/p106b_teacher_sft/v7"
OUTPUT_MANIFEST = V7_DIR / "pilot_manifest.json"
LEGACY = ROOT / "data_cache/tok-ko-en-32768.json"
LEGACY_SHA = "3A69001ECC28A5BDF1E951A1036B234C9BDCB847B310252C6D72CFC6C52C48E3"
VAL_CASES = {2, 15}


class PrerequisiteHold(ValueError):
    """Correctly formed but insufficient teacher output, not a tool crash."""


def source_rows() -> tuple[list[dict], dict]:
    if not regular(V6_RAW) or not regular(V6_MANIFEST):
        raise PrerequisiteHold("Stage2cW v6 raw/manifest not yet available")
    manifest = json.loads(V6_MANIFEST.read_text(encoding="utf-8"))
    raw_sha = sha256_file(V6_RAW)
    if (manifest.get("schema") != "P106B_STAGE2CW_TAGGED_JSON_PAIR_V1"
            or manifest.get("cases") != 16 or manifest.get("requests") != 32
            or manifest.get("source", {}).get("v4_sha256") != V4_SHA256
            or manifest.get("teacher_model_sha256") != MODEL_SHA256
            or manifest.get("raw_sha256") != raw_sha):
        raise ValueError("v6 paired raw/source/teacher lineage differs")
    rows = [json.loads(line) for line in V6_RAW.read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != 32:
        raise PrerequisiteHold("v6 paired output is incomplete")
    tagged = {}
    for row in rows:
        case = row.get("case")
        if type(case) is not int or case not in range(1, 17):
            raise ValueError("v6 case index differs")
        if row.get("output_format") == "tagged":
            if case in tagged:
                raise ValueError("duplicate tagged case")
            tagged[case] = row
    if set(tagged) != set(range(1, 17)):
        raise ValueError("v6 tagged case set differs")
    valid = [tagged[case] for case in range(1, 17)
             if tagged[case].get("canonical_wrapper_ok") is True
             and tagged[case].get("teacher", {}).get("format_status") == "TAGGED_COMPLETE"]
    if len(valid) < 12 or any(case not in {row["case"] for row in valid} for case in VAL_CASES):
        raise PrerequisiteHold("tagged candidates below 12/16 or fixed val cases absent")
    return valid, {"v6_raw_sha256": raw_sha,
                   "v6_manifest_sha256": sha256_file(V6_MANIFEST),
                   "v4_source_sha256": V4_SHA256,
                   "teacher_model_sha256": MODEL_SHA256}


def normalized_prompt_hashes(rows: list[dict]) -> None:
    seen = set()
    for row in rows:
        key = conversation_split_key(row)
        if key in seen:
            raise ValueError("duplicate normalized first user prompt across pilot splits")
        seen.add(key)


def self_test() -> None:
    assert VAL_CASES == {2, 15}
    row = wrap_turns([{"user_text": "기억할 단어는 별빛", "assistant_text": "별빛을 기억합니다."}],
                     source_id="fixture:1", source_sha256="A" * 64,
                     teacher_model_sha256="B" * 64, language="ko",
                     source_license="fixture-only", generation_id="fixture",
                     reasoning_ref="HF/sft_ready/fixture/raw.jsonl#1", reasoning_sha256="C" * 64)
    normalized_prompt_hashes([row])
    assert row["meta"]["teacher_reasoning_sidecar"].endswith("#1")
    from tinylm.data.prepare import SyntheticTokenizer
    ids, labels, text = encode_conversation(row, SyntheticTokenizer(), "chatml")
    assert any(label != IGNORE for label in labels)
    assert "teacher_reasoning_sidecar" not in text
    print("[PASS] fixed val split, question dedup, sidecar-only reasoning and assistant mask; dataset/model NOT_RUN")


def execute(valid: list[dict], source: dict) -> int:
    from tokenizers import Tokenizer

    if V7_DIR.is_symlink() or (V7_DIR.exists() and any(V7_DIR.iterdir())):
        raise FileExistsError("v7 pilot output already exists; use a new stage/version")
    if not regular(LEGACY) or sha256_file(LEGACY) != LEGACY_SHA:
        raise ValueError("legacy student tokenizer absent, linked or changed")
    tok = Tokenizer.from_file(str(LEGACY))
    canonical = []
    for row in valid:
        case = row["case"]
        fields = row["teacher"]["parsed_content"]
        if not isinstance(fields, dict):
            raise ValueError("tagged parsed content absent")
        conv = wrap_turns([{"user_text": fields["user_text"],
                            "assistant_text": fields["assistant_text"]}],
                          source_id=row["source_tree_id"],
                          source_sha256=source["v4_source_sha256"],
                          teacher_model_sha256=source["teacher_model_sha256"],
                          language="ko", source_license="Apache-2.0_card_only",
                          generation_id=f"stage2cw:case{case}:tagged",
                          correction_note=fields["correction_note"],
                          reasoning_ref=f"{V6_RAW.relative_to(ROOT).as_posix()}#case{case}:tagged",
                          reasoning_sha256=source["v6_raw_sha256"])
        ids, labels, _ = encode_conversation(conv, tok, "chatml")
        supervised = sum(label != IGNORE for label in labels)
        if len(ids) < 2 or len(ids) - 1 > 1024 or supervised == 0:
            raise PrerequisiteHold(f"case {case} exceeds student context or has no supervised token")
        canonical.append((case, conv, len(ids), supervised))
    normalized_prompt_hashes([item[1] for item in canonical])
    train = [item for item in canonical if item[0] not in VAL_CASES]
    val = [item for item in canonical if item[0] in VAL_CASES]
    if not train or len(val) != 2:
        raise PrerequisiteHold("pilot train/val split is empty")
    V7_DIR.mkdir(parents=True, exist_ok=True)
    datasets = {}
    for split, rows in (("train", train), ("val", val)):
        writer = ShardWriter(V7_DIR, split)
        for _, row, _, _ in rows:
            writer.append(row)
        manifest = writer.close(lineage=source | {"split": split})
        verify(V7_DIR, manifest)
        datasets[split] = {"rows": len(rows),
                           "canonical_tokens": sum(item[2] for item in rows),
                           "assistant_supervised_tokens": sum(item[3] for item in rows),
                           "shards_manifest": writer.manifest_path.relative_to(ROOT).as_posix(),
                           "concat_sha256": manifest["concat_sha256"]}
    report = {"schema": "P106B_STAGE2DW_TAGGED_PILOT_V1", "source": source,
              "language": "ko_only", "tokenizer_sha256": LEGACY_SHA,
              "teacher_truth_status": "PSEUDO_UNVERIFIED",
              "formal_train_ready": False, "student_training": "NOT_RUN",
              "teacher_reasoning": "raw v6 sidecar only, not an active canonical thinking block",
              "datasets": datasets, "max_shard_bytes": 20_000_000,
              "limit": "tiny format/wrapper pilot only; not 300M/600M, no English or multi-turn corpus"}
    with OUTPUT_MANIFEST.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
    print("[PASS] versioned tagged pilot canonical/ChatML wrapper; student/model GPU NOT_RUN")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            return 0
        valid, source = source_rows()
        if args.check_only:
            print(json.dumps({"source": source, "valid_tagged": len(valid),
                              "fixed_val_cases": sorted(VAL_CASES),
                              "new_output": V7_DIR.relative_to(ROOT).as_posix(),
                              "student_training": "NOT_RUN", "model_gpu": "NOT_RUN"},
                             sort_keys=True))
            print("[CHECK_ONLY] pinned v6 format/val prerequisites PASS; output/student NOT_RUN")
            return 0
        return execute(valid, source)
    except PrerequisiteHold as exc:
        print(f"[HOLD] P106B Stage2dW {exc}", file=sys.stderr)
        return 8
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        print(f"[FAIL] P106B Stage2dW {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
