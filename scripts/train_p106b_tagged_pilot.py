#!/usr/bin/env python3
"""P106B Stage2gW: user-run offline-teacher -> two-update student SFT gate.

Consumes only the versioned Stage2dW canonical pilot and trained P076 mean
legacy parent. This tiny repeated-source functional test is not the requested
300M/600M training and makes no quality or verified-teacher claim. Teacher
reasoning sidecar is never tokenized as a model target.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.diag_p106_bonsai_assets import regular, sha256_file  # noqa: E402
from scripts.diag_p106b_online_pseudo_sft import (  # noqa: E402
    STUDENT, TOKENIZER, TOKENIZER_SHA256, MICRO, ACCUM, UPDATES,
    student_model_and_optimizers, train_updates,
)
from scripts.p106b_shards import verify  # noqa: E402
from tinylm.data.sft import conversation_split_key  # noqa: E402

V7_DIR = ROOT / "HF/sft_ready/p106b_teacher_sft/v7"
INPUT_MANIFEST = V7_DIR / "pilot_manifest.json"
TAG = "p106b_s2g_tagged_pilot_s1337"
OUTPUT_CKPT = ROOT / f"runs/ckpt/m100R1c_ko-en_300M_{TAG}.pt"
OUTPUT_META = ROOT / f"runs/logs/m100R1c_ko-en_300M_{TAG}.json"
OUTPUT_MANIFEST = V7_DIR / "pilot_train_result_manifest.json"


class PrerequisiteHold(ValueError):
    """A missing prior user gate, not a student training crash."""


def load_rows(split: str, top: dict) -> list[dict]:
    info = top.get("datasets", {}).get(split)
    if not isinstance(info, dict):
        raise ValueError(f"v7 {split} dataset entry absent")
    expected = V7_DIR / f"{split}_shards_manifest.json"
    if info.get("shards_manifest") != expected.relative_to(ROOT).as_posix() or not regular(expected):
        raise ValueError(f"v7 {split} shard manifest path differs")
    manifest = json.loads(expected.read_text(encoding="utf-8"))
    verify(V7_DIR, manifest)
    if (manifest.get("rows") != info.get("rows")
            or manifest.get("concat_sha256") != info.get("concat_sha256")):
        raise ValueError(f"v7 {split} shard SHA/count differs")
    rows = []
    for spec in manifest["shards"]:
        with (V7_DIR / spec["path"]).open(encoding="utf-8") as stream:
            rows.extend(json.loads(line) for line in stream if line.strip())
    return rows


def check_inputs() -> tuple[list[dict], list[dict], dict]:
    if not regular(INPUT_MANIFEST):
        raise PrerequisiteHold("Stage2dW v7 canonical pilot not yet available")
    top = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    if (top.get("schema") != "P106B_STAGE2DW_TAGGED_PILOT_V1"
            or top.get("tokenizer_sha256") != TOKENIZER_SHA256
            or top.get("teacher_truth_status") != "PSEUDO_UNVERIFIED"
            or top.get("formal_train_ready") is not False):
        raise ValueError("v7 corpus status or tokenizer contract differs")
    train, val = load_rows("train", top), load_rows("val", top)
    if len(train) < 10 or len(val) != 2:
        raise PrerequisiteHold("tiny pilot train/val count differs")
    train_keys = {conversation_split_key(row) for row in train}
    if len(train_keys) != len(train) or train_keys & {conversation_split_key(row) for row in val}:
        raise ValueError("v7 train/val prompt duplicate")
    if any(any(block.get("type") == "thinking" for message in row["messages"]
               for block in message["content"]) for row in train + val):
        raise ValueError("active canonical teacher thinking block is forbidden")
    if not regular(STUDENT) or not regular(TOKENIZER):
        raise PrerequisiteHold("trained P076 mean parent or legacy tokenizer absent")
    if sha256_file(TOKENIZER) != TOKENIZER_SHA256:
        raise ValueError("student tokenizer SHA differs")
    for path in (OUTPUT_CKPT, OUTPUT_META, OUTPUT_MANIFEST):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"new diagnostic output already exists: {path}")
    return train, val, {"v7_manifest_sha256": sha256_file(INPUT_MANIFEST),
                        "parent_sha256": sha256_file(STUDENT),
                        "tokenizer_sha256": TOKENIZER_SHA256,
                        "train_rows": len(train), "val_rows": len(val),
                        "micro_bs": MICRO, "accum": ACCUM, "updates": UPDATES,
                        "teacher_label_status": "PSEUDO_UNVERIFIED",
                        "student_model_gpu": "NOT_RUN_IN_CHECK_ONLY"}


def self_test() -> None:
    from tinylm.chat.canonical import normalize, validate
    from tinylm.data.prepare import SyntheticTokenizer
    from tinylm.data.sft import IGNORE, encode_conversation
    row = validate(normalize({"messages": [
        {"role": "user", "content": "질문"},
        {"role": "assistant", "content": "답변"}],
        "meta": {"source": "fixture", "source_id": "1", "language": "ko",
                 "teacher_reasoning_sidecar": "raw.jsonl#1"}}))
    ids, labels, text = encode_conversation(row, SyntheticTokenizer(), "chatml")
    assert len(ids) > 1 and any(item != IGNORE for item in labels)
    assert "raw.jsonl#1" not in text and "teacher_reasoning_sidecar" not in text
    assert MICRO * ACCUM == 128 and UPDATES == 2
    print("[PASS] canonical final-only targets and 2-update micro8xaccum16 pilot contract; GPU NOT_RUN")


def execute(train_rows: list[dict], val_rows: list[dict], inputs: dict) -> int:
    import torch
    from tokenizers import Tokenizer
    from scripts.train_sft_p090 import encode_records

    torch, model, base_model, adamw, muon, cfg, parent_step, cache_dir = student_model_and_optimizers()
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    pairs = []
    for row in train_rows:
        messages = row["messages"]
        if len(messages) != 2 or [m["role"] for m in messages] != ["user", "assistant"]:
            raise ValueError("Stage2dW tiny pilot must be one user/assistant turn")
        blocks = [message["content"] for message in messages]
        if any(len(group) != 1 or group[0].get("type") != "text" for group in blocks):
            raise ValueError("Stage2dW tiny pilot must contain only final text")
        pairs.append({"source_tree_id": row["meta"]["source_id"],
                      "user_ko": blocks[0][0]["text"],
                      "assistant_ko": blocks[1][0]["text"]})
    encoded = encode_records(train_rows, tokenizer, cfg.max_seq_len, cfg.vocab_size)
    processed_nonpadding = []
    for step in range(UPDATES):
        order = [index % len(encoded) for index in range(MICRO * ACCUM)]
        random.Random(1337 + step).shuffle(order)
        processed_nonpadding.append(sum(len(encoded[index][0]) + 1 for index in order))
    updates = train_updates(torch, model, adamw, muon, cfg, pairs)
    torch.cuda.synchronize()
    report = {"schema": "P106B_STAGE2GW_TAGGED_PILOT_SFT_V1",
              "tag": TAG, "input": inputs,
              "parent_step": parent_step, "student": "P076 mean legacy32",
              "teacher_co_resident": False, "compiled": True,
              "micro_bs": MICRO, "accum": ACCUM,
              "activation_checkpoint": True,
              "updates": updates,
              "processed_nonpadding_tokens_by_update": processed_nonpadding,
              "assistant_supervised_tokens": sum(item["assistant_supervised_tokens"] for item in updates),
              "pseudo_val_quality": "NOT_RUN", "base_full_val_forgetting": "NOT_RUN",
              "benchmark_accuracy": "NOT_RUN", "formal_train_ready": False,
              "limit": "at most 16 unique Korean source pairs repeated to 128 exposures/update; not 300M/600M"}
    state = {"model": base_model.state_dict(), "cfg": cfg.__dict__,
             "step": (int(parent_step) if parent_step is not None else 0) + UPDATES,
             "tokenizer_lineage": "legacy", "tokenizer_sha256": TOKENIZER_SHA256,
             "p106b": {"source": "stage2dw_tagged_pilot", "tag": TAG,
                       "v7_manifest_sha256": inputs["v7_manifest_sha256"],
                       "parent_sha256": inputs["parent_sha256"],
                       "label_status": "PSEUDO_UNVERIFIED", "updates": UPDATES}}
    with OUTPUT_CKPT.open("xb") as stream:
        torch.save(state, stream)
    report["checkpoint_path"] = OUTPUT_CKPT.relative_to(ROOT).as_posix()
    report["checkpoint_sha256"] = sha256_file(OUTPUT_CKPT)
    with OUTPUT_META.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps({"schema": "P106B_TAGGED_PILOT_METADATA_V1",
                                 "tag": OUTPUT_META.stem, "arch": "tied",
                                 "preset": "m100R1c", "data": "ko-en",
                                 "steps": UPDATES, "tokens": sum(processed_nonpadding),
                                 "final": {"val_loss": None}, "best_val": None,
                                 "quality": "NOT_RUN", "checkpoint_sha256": report["checkpoint_sha256"],
                                 "source_manifest_sha256": inputs["v7_manifest_sha256"]},
                                ensure_ascii=False, indent=2) + "\n")
    report["paired_metadata_sha256"] = sha256_file(OUTPUT_META)
    with OUTPUT_MANIFEST.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
    print("[PASS] tiny offline-teacher student wiring only; generalization/300M NOT_RUN")
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
        train, val, inputs = check_inputs()
        if args.check_only:
            print(json.dumps(inputs, sort_keys=True))
            print("[CHECK_ONLY] v7 corpus/parent/tokenizer lineage PASS; model/GPU NOT_RUN")
            return 0
        return execute(train, val, inputs)
    except PrerequisiteHold as exc:
        print(f"[HOLD] P106B Stage2gW {exc}", file=sys.stderr)
        return 8
    except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
        print(f"[FAIL] P106B Stage2gW {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
