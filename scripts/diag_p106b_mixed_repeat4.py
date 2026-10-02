#!/usr/bin/env python3
"""User-owned 300M processed-token SFT after the mixed-public 75M gate.

Bounded-buffer language interleaving, micro8/accum16/checkpoint-on, four actual
passes. No teacher is resident. A token-deficient corpus never starts a model.
One resume checkpoint is published per epoch without overwriting earlier ones.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_mixed_scale import OUTPUT as PUBLIC, TOK_SHA, GOAL, digest, safe_repo_path
from scripts.p106b_shards import verify
from scripts.train_sft_p090 import encode_records, loss_sum

TAG = "p106b_s4_mixed300m_chat32_s1337"
OUTPUT = ROOT / "HF/sft_ready/p106b_mixed_student_v1"
FINAL = ROOT / f"runs/ckpt/m100s10_ko-en_300M_{TAG}.pt"
LOG = ROOT / f"runs/logs/m100s10_ko-en_300M_{TAG}.json"


def check(*, wire=False, balanced=False):
    from scripts.p106b_balanced_public import OUTPUT as BALANCED_PUBLIC
    public = BALANCED_PUBLIC if balanced else PUBLIC
    p = public / "report.json"
    for path in (p, OUTPUT, FINAL, LOG):
        safe_repo_path(path)
    digest(p)
    report = json.loads(p.read_text(encoding="utf-8"))
    if report.get("schema") != "P106B_MIXED_PUBLIC_C_V1" or report.get("tokenizer_sha256") != TOK_SHA:
        raise ValueError("mixed corpus identity/tokenizer mismatch")
    if not wire and report.get("token_target_ready") is not True:
        raise ValueError("75M source target incomplete; no student started: " + json.dumps(report.get("teacher_deficit_tokens")))
    if wire and (any(report.get("rows", {}).get("train:" + lang, 0) < 128 for lang in ("ko", "en"))
                 or sum(report.get("rows", {}).get("val:" + lang, 0) for lang in ("ko", "en")) < 8):
        raise ValueError("wire needs at least128 train rows per language and8 val rows")
    if not wire and any(not GOAL <= report.get("nonpadding_tokens", {}).get("train:" + lang, 0) < GOAL + 1024 for lang in ("ko", "en")):
        raise ValueError("nonpadding language quota is not 37.5M each")
    specs = {}
    for split in ("train", "val"):
        file = public / f"{split}_shards_manifest.json"
        digest(file)
        specs[split] = json.loads(file.read_text(encoding="utf-8"))
        verify(public, specs[split])
        if specs[split]["concat_sha256"] != report.get(split + "_concat_sha256"):
            raise ValueError("mixed corpus concat SHA differs")
    if balanced and not wire:
        wire_file = ROOT / "HF/sft_ready/p106b_mixed_student_wire_v2_balanced/report.json"
        safe_repo_path(wire_file)
        digest(wire_file)
        require_wire_report(json.loads(wire_file.read_text(encoding="utf-8")),
                            specs["train"]["concat_sha256"], specs["val"]["concat_sha256"])
    output = ROOT / "HF/sft_ready/p106b_mixed_student_wire_v1" if wire else OUTPUT
    final = output / "student.pt" if wire else FINAL
    log = output / "student.json" if wire else LOG
    if balanced:
        output = ROOT / ("HF/sft_ready/p106b_mixed_student_wire_v2_balanced" if wire else "HF/sft_ready/p106b_mixed_student_v2_balanced")
        final = output / "student.pt" if wire else ROOT / "runs/ckpt/m100s10_ko-en_300M_p106b_s4_mixed300m_balanced_chat32_s1337.pt"
        log = output / "student.json" if wire else ROOT / "runs/logs/m100s10_ko-en_300M_p106b_s4_mixed300m_balanced_chat32_s1337.json"
    for path in (output, final, log):
        safe_repo_path(path)
        if path.is_symlink():
            raise ValueError("linked student output refused")
    if final.exists() or log.exists() or (output / "report.json").exists():
        raise FileExistsError("completed outputs preserved; use a new stage")
    return report, specs, {"corpus_report_sha256": digest(p), "tokenizer_sha256": TOK_SHA,
                           "public_directory": str(public.relative_to(ROOT)),
                           "measurement_contract": "MIXED_COUNTS_VALIDATION_V2",
                           "train_concat_sha256": specs["train"]["concat_sha256"],
                           "val_concat_sha256": specs["val"]["concat_sha256"],
                           "micro": 8, "accum": 16, "grad_checkpoint": True, "epochs": 1 if wire else 4,
                           "scope": "WIRE_TWO_UPDATES_NOT_300M" if wire else "FOUR_REAL_EPOCHS",
                           "output": str(output.relative_to(ROOT)), "final": str(final.relative_to(ROOT)),
                           "log": str(log.relative_to(ROOT)),
                           "lr": 1e-4, "muon_lr": 4e-4, "matrix_weight_decay": 0,
                           "buffer_rows_per_language": 4096, "seed": 1337,
                           "shuffle": "bounded buffer, not a uniform global permutation",
                           "formal_train_ready": False, "quality": "NOT_REVIEWED"}


def rows(spec, language=None, *, directory=PUBLIC):
    for shard in spec["shards"]:
        with (directory / shard["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if language is None or row["meta"]["language"] == language:
                    yield row


def buffered_shuffle(values, rng, limit=4096):
    pool = []
    for value in values:
        if len(pool) < limit:
            pool.append(value)
            continue
        index = rng.randrange(len(pool))
        yield pool[index]
        pool[index] = value
    rng.shuffle(pool)
    yield from pool


def interleave_streams(streams, size, *, on_group=None):
    consumed, alive, block, languages = {k: 0 for k in streams}, set(streams), [], []
    while alive:
        language = min(alive, key=lambda k: (consumed[k], k))
        try:
            item = next(streams[language])
        except StopIteration:
            alive.remove(language)
            continue
        consumed[language] += len(item[0])
        block.append(item)
        languages.append(language)
        if len(block) == size:
            if on_group is not None:
                on_group(block, languages)
            yield block
            block, languages = [], []
    if block:
        if on_group is not None:
            on_group(block, languages)
        yield block


def validation_rows(values, per_language=16):
    """Same fixed token-count-independent hash ranking, with both languages present."""
    buckets = {lang: [] for lang in ("ko", "en")}
    for row in values:
        lang = row["meta"]["language"]
        key = hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        pool = buckets[lang]
        pool.append((key, row))
        pool.sort(key=lambda item: item[0])
        del pool[per_language:]
    if any(len(pool) < per_language for pool in buckets.values()):
        raise ValueError("wire validation requires16 rows per language")
    return [item[1] for lang in ("ko", "en") for item in buckets[lang]]


def require_wire_report(report, train_sha, val_sha):
    inputs = report.get("input", {})
    if (report.get("status") != "WIRE_COMPLETE" or report.get("optimizer_updates") != 2
            or inputs.get("measurement_contract") != "MIXED_COUNTS_VALIDATION_V2"
            or inputs.get("train_concat_sha256") != train_sha
            or inputs.get("val_concat_sha256") != val_sha
            or report.get("processed_train_row_exposures") != 256):
        raise ValueError("balanced full training requires the matching successful two-update wire")


def publish_checkpoint(path, state):
    import torch
    partial = path.with_name(path.name + ".partial")
    if path.exists() or partial.exists() or path.is_symlink() or partial.is_symlink():
        raise FileExistsError("checkpoint/partial preserved for inspection")
    partial.parent.mkdir(parents=True, exist_ok=True)
    torch.save(state, partial)
    os.link(partial, path)  # No overwrite, even if another writer races.
    partial.unlink()  # Only the just-created private temporary inode is removed.


def execute(report, specs, info, *, resume=False, wire=False):
    from scripts.p106b_education_followup import load_student, ARMS, answers
    from scripts.paired_eval import full_val_losses
    import torch
    from scripts.p106b_gate_runtime import idle_before_gpu
    from scripts.p106b_report_domains import separated_report
    idle_before_gpu()  # Teacher/other compute must be down before student allocation.
    output = ROOT / info["output"]
    public = ROOT / info["public_directory"]
    final, log = ROOT / info["final"], ROOT / info["log"]
    safe_repo_path(output)
    output.mkdir(parents=True, exist_ok=True)
    progress = sorted(output.glob("epoch_[1-4].pt"))
    if progress and not resume:
        raise FileExistsError("progress exists; explicit --mode resume is required")
    if resume and not progress:
        raise ValueError("no complete epoch resume checkpoint")
    if __import__('shutil').disk_usage(output).free < 8 * (1 << 30):
        raise ValueError("at least8GiB free disk required before training")
    began = time.perf_counter()
    torch.manual_seed(1337)
    torch_mod, model, base, cfg, tok, adam, muon = load_student("b", training=True)
    if not cfg.grad_checkpoint:
        raise ValueError("checkpoint-on required")
    input_identity = {**info, "parent_sha256": ARMS["b"]["sha"]}
    pad_id = tok.token_to_id("<pad>")
    if pad_id is None:
        raise ValueError("student pad token missing")
    def encoded(language, epoch):
        raw = buffered_shuffle(rows(specs["train"], language, directory=public), random.Random(1337 + epoch * 2 + (language == "ko")))
        for row in raw:
            item = encode_records([row], tok, 1024, 32768)[0]
            if len(item[0]) != row["meta"]["processed_x_tokens"] or item[2] != row["meta"]["assistant_targets"]:
                raise ValueError("stored token accounting differs from current encoder")
            yield item
    history, first_epoch, updates, total_tokens, grad_peak = [], 1, 0, 0, 0.0
    import itertools
    validation = validation_rows(rows(specs["val"], directory=public)) if wire else list(rows(specs["val"], directory=public))
    val_records = [encode_records([row], tok, 1024, 32768)[0] for row in validation]
    from collections import Counter
    validation_info = {"rows": len(validation), "languages": dict(Counter(r["meta"]["language"] for r in validation)),
                       "sha256": hashlib.sha256(json.dumps(validation, ensure_ascii=False, sort_keys=True).encode()).hexdigest().upper(),
                       "selection": "hash lowest16 per language" if wire else "all validation rows"}
    def val_ce():
        model.eval()
        base.freeze_quant()
        total, targets = 0.0, 0
        with torch.no_grad():
            for start in range(0, len(val_records), 8):
                chunk = val_records[start:start + 8]
                total += float(loss_sum(model, chunk, pad_id, "cuda", 32768, 1024))
                targets += sum(r[2] for r in chunk)
        base.clear_quant()
        model.train()
        if not targets or not math.isfinite(total):
            raise ValueError("empty/nonfinite SFT validation")
        return total / targets
    if progress:
        saved = torch.load(progress[-1], map_location="cpu", weights_only=True)
        if saved["input"] != input_identity:
            raise ValueError("resume source/config identity differs")
        base.load_state_dict(saved["model"], strict=True)
        adam.load_state_dict(saved["adam"])
        muon.load_state_dict(saved["muon"])
        history, updates, total_tokens = saved["history"], saved["updates"], saved["processed_tokens"]
        grad_peak = saved.get("grad_peak", 0.0)
        first_epoch = saved["epoch"] + 1
        baseline = saved["baseline"]
        torch.set_rng_state(saved["rng_cpu"])
        torch.cuda.set_rng_state_all(saved["rng_cuda"])
    else:
        model.eval()
        native, count = full_val_losses(base, cfg, ROOT / ARMS["b"]["cache"], 1024, 4, "cuda")
        baseline = {"native_ce": sum(native) / len(native), "native_tokens": count,
                    "sft_ce": val_ce(), "answers": answers(base, cfg, tok, output, "parent")}
    for epoch in range(first_epoch, 2 if wire else 5):
        t0, loss_total, target_total, epoch_tokens = time.perf_counter(), 0.0, 0, 0
        from collections import Counter
        counts = Counter()
        def account(group, languages):
            for item, language in zip(group, languages):
                counts[language + "_rows"] += 1
                counts[language + "_x_tokens"] += len(item[0])
                counts[language + "_assistant_targets"] += item[2]
        model.train()
        streams = {lang: iter(encoded(lang, epoch)) for lang in ("ko", "en")}
        groups = interleave_streams(streams, 128, on_group=account)
        if wire:
            groups = itertools.islice(groups, 2)
        for group in groups:
            targets = sum(item[2] for item in group)
            adam.zero_grad(set_to_none=True)
            muon.zero_grad(set_to_none=True)
            for start in range(0, len(group), 8):
                micro = group[start:start + 8]
                part = loss_sum(model, micro, pad_id, "cuda", 32768, 1024)
                if not torch.isfinite(part):
                    raise ValueError("nonfinite training loss")
                (part / targets).backward()
                loss_total += float(part.detach())
                epoch_tokens += sum(len(r[0]) for r in micro)
            grad = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            if not torch.isfinite(grad):
                raise ValueError("nonfinite gradient")
            grad_peak = max(grad_peak, float(grad))
            adam.step()
            muon.step()
            target_total += targets
            updates += 1
        expected = sum(report["nonpadding_tokens"]["train:" + lang] for lang in ("ko", "en"))
        if not wire and epoch_tokens != expected:
            raise ValueError("actual epoch token sum differs; never claim300M")
        total_tokens += epoch_tokens
        item = {"epoch": epoch, "updates": updates, "processed_tokens": epoch_tokens,
                "processed_rows": sum(counts[lang + "_rows"] for lang in ("ko", "en")),
                "language_counts": dict(counts), "epoch_complete": not wire,
                "assistant_targets": target_total, "train_ce": loss_total / target_total,
                "sft_val_ce": val_ce(), "wall_sec": time.perf_counter() - t0}
        history.append(item)
        state = {"model": {k: v.detach().cpu() for k, v in base.state_dict().items()},
                 "cfg": cfg.__dict__, "step": 2289 + updates, "input": input_identity,
                 "adam": adam.state_dict(), "muon": muon.state_dict(), "epoch": epoch,
                 "processed_tokens": total_tokens, "updates": updates, "history": history,
                 "grad_peak": grad_peak,
                 "baseline": baseline, "rng_cpu": torch.get_rng_state(), "rng_cuda": torch.cuda.get_rng_state_all()}
        publish_checkpoint(output / f"epoch_{epoch}.pt", state)
        print("[MIXED_EPOCH] " + json.dumps(item), flush=True)
    model.eval()
    native, count = full_val_losses(base, cfg, ROOT / ARMS["b"]["cache"], 1024, 4, "cuda")
    if wire and updates != 2:
        raise ValueError("wire did not execute exactly2 optimizer updates")
    evidence = {"schema": "P106B_MIXED_300M_EXPERIMENT_V1", "status": "WIRE_COMPLETE" if wire else "EDUCATION_COMPLETE",
                "scope": info["scope"], "input": input_identity,
                "sft_validation": validation_info,
                "history": history, "processed_conversation_tokens": total_tokens,
                "optimizer_updates": updates, "baseline": baseline,
                "grad_norm_peak_preclip": grad_peak,
                "peak_allocated_mib": torch.cuda.max_memory_allocated() / 2**20,
                "peak_reserved_mib": torch.cuda.max_memory_reserved() / 2**20,
                "memory_measurement_scope": "current process; not earlier resumed processes",
                "native_ce_after": sum(native) / len(native), "native_tokens_after": count,
                "answers_after": answers(base, cfg, tok, output, "student"),
                "whole_wall_sec": time.perf_counter() - began,
                "whole_wall_scope": "current process; resumed earlier processes and interrupted work are not included",
                "successful_epoch_wall_sum_sec": sum(item["wall_sec"] for item in history),
                "formal_train_ready": False,
                "semantic_truth": "NOT_REVIEWED", "teacher_resident": False}
    evidence.update(student_answers=evidence["answers_after"], parent_answers=baseline["answers"],
                    base_full_val_delta=evidence["native_ce_after"] - baseline["native_ce"],
                    student_conversation_tokens=total_tokens,
                    assistant_targets=sum(item["assistant_targets"] for item in history),
                    available_train_rows=specs["train"]["rows"],
                    processed_train_row_exposures=sum(item["processed_rows"] for item in history),
                    selected_rows=sum(item["processed_rows"] for item in history), selected_concat_sha256=specs["train"]["concat_sha256"],
                    teacher_completion_tokens=0)
    evidence["report_domains"] = separated_report(evidence)
    evidence["report_domains"]["corpus"]["label_status"] = "PUBLIC_SOURCE_UNVERIFIED"
    publish_checkpoint(final, {"model": base.state_dict(), "cfg": cfg.__dict__, "step": 2289 + updates,
                               "tokenizer_sha256": TOK_SHA, "tokenizer_lineage": "chat32", "sft": evidence})
    for path in (output / "report.json", log):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print("[MIXED_300M_SUMMARY] " + json.dumps(evidence), flush=True)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    ap.add_argument("--mode", choices=("new", "resume", "wire", "new-balanced", "resume-balanced", "wire-balanced"), default="new")
    args = ap.parse_args()
    try:
        report, specs, info = check(wire=args.mode.startswith("wire"), balanced=args.mode.endswith("-balanced"))
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        print(f"[HOLD] input prerequisite: {exc}", file=sys.stderr)
        return 8
    if args.check_only:
        print(json.dumps(info, ensure_ascii=False))
        return 0
    return execute(report, specs, info, resume=args.mode.startswith("resume"), wire=args.mode.startswith("wire"))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("[INTERRUPTED] complete epoch checkpoints and original inputs preserved", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        if type(exc).__name__ == "OutOfMemoryError":
            print("[RESOURCE_OOM_NEGATIVE] no memory-fit or quality claim", file=sys.stderr)
            raise SystemExit(8)
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(9)
