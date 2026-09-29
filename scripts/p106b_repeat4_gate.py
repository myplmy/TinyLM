#!/usr/bin/env python3
"""User-run C4 pilot: concept-disjoint v17 split, exact four passes, saved quality evidence."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_gate_runtime import (read_v17, student_inputs, new_directory,
    idle_before_gpu, write_report, disposition, STUDENT, STUDENT_SHA256,
    TOKENIZER, TOKENIZER_SHA256, PrerequisiteHold, wall_limit, code_contract, require_report)
from scripts.diag_p106_bonsai_assets import sha256_file, regular
from scripts.p106b_shards import ShardWriter, verify
from tinylm.data.sft import conversation_split_key

DIRECTORY = ROOT / "HF/sft_ready/p106b_teacher_sft/v19_repeat4_v17_pilot"
TAG = "p106b_s3c_repeat4_s1337"
CHECKPOINT = ROOT / f"runs/ckpt/m100R1c_ko-en_300M_{TAG}.pt"
META = ROOT / f"runs/logs/m100R1c_ko-en_300M_{TAG}.json"
BASE_CACHE = ROOT / "data_cache/ko-en_600000000"
EPOCHS = 4
FOLLOWUP = False
PROBES = [
    ("arithmetic_ko", "2 더하기 3의 값만 숫자로 답하세요."),
    ("arithmetic_en", "What is 7 minus 4? Answer with one digit."),
    ("format_ko", "한국어 과일 두 개를 쉼표로 구분해서만 쓰세요."),
    ("format_en", "Return only JSON with key result and integer value 5."),
    ("knowledge_ko", "물이 얼면 무엇이 되나요? 한 문장으로 답하세요."),
    ("knowledge_en", "Name the planet humans live on, in one word."),
    ("memory_ko", "내가 정한 비밀 단어는 별빛입니다. 비밀 단어만 다시 쓰세요."),
    ("logic_en", "All red boxes are heavy. This box is red. Is it heavy? Answer yes or no."),
]


def group_split(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Merge same concepts AND same normalized prompt before pilot split."""
    parents = list(range(len(rows)))
    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index
    owners = {}
    for index, row in enumerate(rows):
        concept = row["meta"].get("parent_concept_id")
        if not isinstance(concept, str) or len(concept) != 64:
            raise ValueError("full parent concept ID required")
        for key in (("concept", concept), ("prompt", conversation_split_key(row))):
            if key in owners:
                parents[find(index)] = find(owners[key])
            else:
                owners[key] = index
    groups = {}
    for index in range(len(rows)):
        groups.setdefault(find(index), []).append(index)
    if len(groups) < 10:
        raise PrerequisiteHold("fewer than 10 independent concept/prompt groups")
    ordered = sorted(groups.values(), key=lambda indices: hashlib.sha256(
        ("p106b-C4:" + "|".join(sorted(rows[i]["meta"]["parent_concept_id"] for i in indices))).encode()).hexdigest())
    val_indices = {i for group in ordered[:max(2, len(ordered) // 5)] for i in group}
    train, val = [], []
    for index, row in enumerate(rows):
        copy = json.loads(json.dumps(row))
        split = "val" if index in val_indices else "train"
        copy["meta"].update(pilot_split=split, student_training="NOT_RUN_NEW_C4",
                            used_in_prior_throughput_gate=True)
        (val if split == "val" else train).append(copy)
    if not train or not val:
        raise ValueError("empty C4 split")
    if ({r["meta"]["parent_concept_id"] for r in train}
            & {r["meta"]["parent_concept_id"] for r in val}
            or {conversation_split_key(r) for r in train} & {conversation_split_key(r) for r in val}):
        raise ValueError("C4 concept/prompt leakage")
    return train, val


def source_rows():
    if not FOLLOWUP:
        rows, report = read_v17()
        report_path = ROOT / "HF/sft_ready/p106b_teacher_sft/v17_online_public1_low/online_public1_low_manifest.json"
        return rows, report["canonical_concat_sha256"], report_path
    directory = ROOT / "HF/sft_ready/p106b_teacher_sft/v24_integrated1_low"
    report_path = directory / "gate_manifest.json"
    report = require_report(report_path, "P106B_INTEGRATED_GATE_V1", "INTEGRATED_ONE_UPDATE_PASSED")
    if report["input"]["code_sha256"] != code_contract("diag_p106b_integrated_gate.py"):
        raise PrerequisiteHold("integrated code evidence stale")
    path = directory / "training_shards_manifest.json"
    if not regular(path):
        raise ValueError("integrated training corpus absent/linked")
    spec = json.loads(path.read_text(encoding="utf-8"))
    verify(directory, spec)
    if spec["concat_sha256"] != report["training_concat_sha256"] or spec["rows"] != 128:
        raise ValueError("integrated saved corpus changed")
    rows = [json.loads(line) for shard in spec["shards"]
            for line in (directory / shard["path"]).read_text(encoding="utf-8").splitlines()]
    return rows, spec["concat_sha256"], report_path


def preview() -> tuple[list[dict], list[dict], dict]:
    rows, concat, report_path = source_rows()
    inputs = student_inputs()
    train, val = group_split(rows)
    for path in (CHECKPOINT, META):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"new SFT output already exists: {path.name}")
    from tokenizers import Tokenizer
    from scripts.train_sft_p090 import encode_records
    tok = Tokenizer.from_file(str(TOKENIZER))
    encoded = encode_records(train, tok, 1024, 32768)
    va = encode_records(val, tok, 1024, 32768)
    return train, val, {**inputs, "code_sha256": code_contract("p106b_repeat4_gate.py"),
        "source_manifest": report_path.relative_to(ROOT).as_posix(),
        "source_manifest_sha256": sha256_file(report_path), "followup_after_integrated": FOLLOWUP,
        "source_concat_sha256": concat,
        "train_rows": len(train), "val_rows": len(val), "epochs": 4,
        "unique_train_conversation_tokens": sum(len(r[0]) for r in encoded),
        "train_processed_tokens_4epochs": 4 * sum(len(r[0]) for r in encoded),
        "train_assistant_tokens_4epochs": 4 * sum(r[2] for r in encoded),
        "val_conversation_tokens": sum(len(r[0]) for r in va),
        "micro": 8, "accum": 16, "updates_expected": 4 * math.ceil(len(train) / 128),
        "limit": "short final group is not padded with repeated conversations; exact each row four times",
        "formal_train_ready": False, "teacher_truth": "PSEUDO_UNVERIFIED"}


def prepare() -> int:
    train, val, inputs = preview()
    new_directory(DIRECTORY)
    DIRECTORY.mkdir(parents=True, exist_ok=False)
    for name, rows in (("train", train), ("val", val)):
        writer = ShardWriter(DIRECTORY, name)
        for row in rows:
            writer.append(row)
        verify(DIRECTORY, writer.close(lineage=inputs))
    write_report(DIRECTORY / "source_manifest.json", {"schema": "P106B_REPEAT4_SOURCE_V1", **inputs})
    print("[PASS] new concept/prompt-disjoint C4 corpus only; model/GPU NOT_RUN")
    return 0


def inputs_for_train() -> tuple[list[dict], list[dict], dict]:
    report_path = DIRECTORY / "source_manifest.json"
    if not regular(report_path):
        raise PrerequisiteHold("C4 CPU source prepare not completed")
    info = json.loads(report_path.read_text(encoding="utf-8"))
    _, _, expected = preview()
    if info != {"schema": "P106B_REPEAT4_SOURCE_V1", **expected}:
        raise ValueError("C4 source/tokenizer/parent contract changed")
    splits = []
    for name in ("train", "val"):
        path = DIRECTORY / f"{name}_shards_manifest.json"
        if not regular(path):
            raise ValueError("C4 shard manifest absent/linked")
        spec = json.loads(path.read_text(encoding="utf-8"))
        verify(DIRECTORY, spec)
        splits.append([json.loads(line) for shard in spec["shards"]
                       for line in (DIRECTORY / shard["path"]).read_text(encoding="utf-8").splitlines()])
    fresh_train, fresh_val = group_split(source_rows()[0])
    if splits != [fresh_train, fresh_val]:
        raise ValueError("C4 exact split content changed")
    for path in (CHECKPOINT, META, DIRECTORY / "repeat4_result.json", DIRECTORY / "answers_shards_manifest.json"):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"preserve existing C4 output: {path}")
    for path in (BASE_CACHE / "meta.json", BASE_CACHE / "val.bin"):
        if not regular(path) or BASE_CACHE.is_symlink():
            raise PrerequisiteHold("public base validation cache missing/linked")
    cache_meta = json.loads((BASE_CACHE / "meta.json").read_text(encoding="utf-8"))
    if cache_meta.get("vocab") != 32768 or cache_meta.get("data") != "ko-en":
        raise ValueError("public base validation cache geometry differs")
    info.update(base_val_sha256=sha256_file(BASE_CACHE / "val.bin"),
                base_cache_meta_sha256=sha256_file(BASE_CACHE / "meta.json"))
    return splits[0], splits[1], info


def _execute(train_rows: list[dict], val_rows: list[dict], inputs: dict) -> int:
    idle_before_gpu()
    started = time.monotonic()
    from tokenizers import Tokenizer
    from scripts.diag_p106b_online_pseudo_sft import student_model_and_optimizers
    from scripts.train_sft_p090 import encode_records, micro_groups, loss_sum
    from scripts.paired_eval import full_val_losses, paired_stats
    from tinylm.infer.generate import sample
    from tinylm.chat.serialize import serialize
    torch, model, base, adam, muon, cfg, parent_step, _cache = student_model_and_optimizers()
    tok = Tokenizer.from_file(str(TOKENIZER))
    pad = tok.token_to_id("<pad>")
    if pad is None:
        raise ValueError("student tokenizer PAD id absent")
    tr = encode_records(train_rows, tok, 1024, cfg.vocab_size)
    va = encode_records(val_rows, tok, 1024, cfg.vocab_size)
    answers = ShardWriter(DIRECTORY, "answers")
    def probes(label):
        base.eval()
        for ident, text in PROBES:
            prompt = serialize({"messages": [{"role": "user", "content": text}]},
                               "chatml", add_generation_prompt=True)
            decoded, meta = sample(base, cfg, tok, prompt, max_new=80, temperature=0,
                top_k=1, device="cuda", logits_last_only=True, return_metadata=True)
            prefix = tok.decode(tok.encode(prompt).ids)
            answers.append({"model": label, "id": ident, "prompt": prompt,
                "decoded_full_text": decoded, "answer_text": decoded[len(prefix):] if decoded.startswith(prefix) else None,
                "generation": meta, "semantic_score": "MANUAL_REQUIRED"})
        base.train()
    def val_ce():
        base.eval()
        with torch.no_grad():
            losses = [float(loss_sum(base, va[i:i+8], pad, torch.device("cuda"), cfg.vocab_size, 2048))
                      for i in range(0, len(va), 8)]
        base.train()
        return sum(losses) / sum(r[2] for r in va)
    before_base, used = full_val_losses(base, cfg, BASE_CACHE, 1024, 8, "cuda")
    before_sft = val_ce()
    probes("parent")
    history = []
    applied = 0
    for epoch in range(1, 5):
        order = list(range(len(tr)))
        random.Random(1337 + epoch).shuffle(order)
        total_loss = total_targets = 0
        t0 = time.monotonic()
        for blocks in micro_groups(tr, order, 8, 16):
            targets = sum(r[2] for block in blocks for r in block)
            adam.zero_grad(set_to_none=True)
            muon.zero_grad(set_to_none=True)
            for block in blocks:
                part = loss_sum(model, block, pad, torch.device("cuda"), cfg.vocab_size, 2048)
                if not bool(torch.isfinite(part)):
                    raise RuntimeError("C4 nonfinite assistant loss")
                total_loss += float(part.detach())
                (part / targets).backward()
            grad = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            if not math.isfinite(float(grad)):
                raise RuntimeError("C4 nonfinite gradient")
            adam.step()
            muon.step()
            total_targets += targets
            applied += 1
        torch.cuda.synchronize()
        history.append({"epoch": epoch, "updates_total": applied,
            "train_ce": total_loss / total_targets, "sft_val_ce": val_ce(),
            "assistant_train_tokens": total_targets,
            "processed_conversation_tokens": sum(len(r[0]) for r in tr),
            "wall_sec": round(time.monotonic() - t0, 3)})
        print("[REPEAT4_EPOCH] " + json.dumps(history[-1]), flush=True)
    after_base, _ = full_val_losses(base, cfg, BASE_CACHE, 1024, 8, "cuda")
    probes("student_4epoch")
    verify(DIRECTORY, answers.close(lineage=inputs))
    forgetting = sum(after_base) / len(after_base) - sum(before_base) / len(before_base)
    state = {"model": base.state_dict(), "cfg": cfg.__dict__, "step": int(parent_step) + applied,
        "tokenizer_lineage": "legacy", "tokenizer_sha256": TOKENIZER_SHA256,
        "p106b": {"tag": TAG, "label_status": "PSEUDO_UNVERIFIED", "input": inputs,
                   "epochs": 4, "updates": applied}}
    with CHECKPOINT.open("xb") as stream:
        torch.save(state, stream)
    ckpt_sha = sha256_file(CHECKPOINT)
    safe = (forgetting <= 0.1 and history[-1]["sft_val_ce"] <= before_sft + 0.1)
    report = {"schema": "P106B_REPEAT4_RESULT_V1", "status": "PILOT_SAFETY_PASSED" if safe else "GATE_NEGATIVE",
        "input": inputs, "history": history, "before_sft_val_ce": before_sft,
        "base_full_val_delta": forgetting, "base_full_val_crops": len(before_base),
        "base_before_ce": sum(before_base)/len(before_base),
        "base_after_ce": sum(after_base)/len(after_base),
        "base_full_val_tokens": used, "paired_base_before_minus_after": paired_stats(before_base, after_base),
        "processed_conversation_tokens": 4 * sum(len(r[0]) for r in tr),
        "checkpoint_sha256": ckpt_sha, "checkpoint": CHECKPOINT.relative_to(ROOT).as_posix(),
        "whole_wall_sec": round(time.monotonic() - started, 3), "formal_train_ready": False,
        "timer_scope": "model prepare, validation/probes/train/checkpoint hash; input preflight/metadata write excluded",
        "safety_threshold_note": "0.1 nats is operational pilot stop only, not intelligence adoption/ruler",
        "quality": "MANUAL_RAW_ANSWERS_REVIEW_REQUIRED"}
    write_report(DIRECTORY / "repeat4_result.json", report)
    write_report(META, {**report, "tag": TAG, "arch": "tied", "preset": "m100R1c", "data": "ko-en",
        "steps": applied, "tokens": report["processed_conversation_tokens"],
        "final": {"val_loss": report["base_after_ce"], "sft_val_ce": history[-1]["sft_val_ce"],
                  "val_source": "fixed public base full-val"}, "best_val": None})
    print("[REPEAT4_SUMMARY] " + json.dumps(report), flush=True)
    return 0 if safe else 8


def execute(train_rows, val_rows, inputs):
    try:
        with wall_limit(7200):
            return _execute(train_rows, val_rows, inputs)
    except (Exception, KeyboardInterrupt) as exc:
        status, rc = disposition(exc)
        failure = DIRECTORY / "repeat4_failure.json"
        if not failure.exists() and not failure.is_symlink():
            write_report(failure, {"schema": "P106B_REPEAT4_FAILURE_V1", "status": status,
                "exit_code": rc, "input": inputs, "error": f"{type(exc).__name__}: {str(exc)[:250]}",
                "updates": "PARTIAL_OR_UNKNOWN_SEE_RUNLOG", "formal_train_ready": False,
                "claim": "no completed four-epoch/quality claim; original corpus and parent unchanged"})
        raise


def self_test():
    from tinylm.chat.canonical import normalize
    rows = [normalize({"messages": [{"role": "user", "content": f"Question {i//2}"},
              {"role": "assistant", "content": f"answer {i}"}],
              "meta": {"parent_concept_id": f"{i//2:064X}", "source": "fixture", "source_id": str(i)}})
            for i in range(40)]
    train, val = group_split(rows)
    assert len(train) + len(val) == 40
    assert not ({r["meta"]["parent_concept_id"] for r in train} & {r["meta"]["parent_concept_id"] for r in val})
    assert EPOCHS == 4 and len(PROBES) == 8
    print("[PASS] C4 group split/exact four passes/no artificial row refill; GPU NOT_RUN")


def main():
    global FOLLOWUP, DIRECTORY, TAG, CHECKPOINT, META
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--check-only", action="store_true")
    modes.add_argument("--execute", action="store_true")
    parser.add_argument("--mode", choices=("prepare", "train", "prepare-followup", "train-followup"), default="prepare")
    args = parser.parse_args()
    FOLLOWUP = args.mode.endswith("-followup")
    if FOLLOWUP:
        DIRECTORY = ROOT / "HF/sft_ready/p106b_teacher_sft/v25_followup4_integrated_pilot"
        TAG = "p106b_s3g_followup4_s1337"
        CHECKPOINT = ROOT / f"runs/ckpt/m100R1c_ko-en_300M_{TAG}.pt"
        META = ROOT / f"runs/logs/m100R1c_ko-en_300M_{TAG}.json"
    try:
        if args.self_test:
            self_test()
            return 0
        if args.mode.startswith("prepare"):
            new_directory(DIRECTORY)
            if args.check_only:
                print(json.dumps(preview()[2]))
                return 0
            return prepare()
        train, val, info = inputs_for_train()
        if args.check_only:
            print(json.dumps(info))
            return 0
        return execute(train, val, info)
    except (Exception, KeyboardInterrupt) as exc:
        status, code = disposition(exc)
        print(f"[{status}] {type(exc).__name__}: {str(exc)[:250]}", file=sys.stderr)
        return code


if __name__ == "__main__":
    raise SystemExit(main())
