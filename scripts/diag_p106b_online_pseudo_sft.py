#!/usr/bin/env python3
"""P106B Stage1bW: bounded, user-run online teacher-to-student pseudo SFT.

Only a functional 2-update pilot. Teacher translations are NEVER verified
P106 ACCEPT records, a production SFT corpus, or model-quality evidence.
Self-test is CPU-only; check-only reads pinned metadata without model loading.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.diag_p106_oasst2_teacher_ko_gate import (  # noqa: E402
    OUTPUT as SOURCE_CANDIDATES, MANIFEST as SOURCE_MANIFEST,
    DATASET_DIR,
    SOURCE, SOURCE_SHA256, MODEL, MODEL_SHA256, SERVER,
    TEACHER_CTX, MAX_OUTPUT_TOKENS, select_candidates, translation_prompt,
    parse_translation, asset_preflight,
)
from scripts.diag_p106_full_coload_accum import _compute_apps, _kill_group  # noqa: E402
from scripts.diag_p106_coload import _free_port, _http_json  # noqa: E402
from scripts.diag_p106_vram_sample import read_memory  # noqa: E402
from scripts.diag_p106_bonsai_assets import regular, sha256_file  # noqa: E402

STUDENT = ROOT / "runs/ckpt/m100R1c_ko-en_300M_p076_b3_ag2_mean_s1337.pt"
TOKENIZER = ROOT / "data_cache/tok-ko-en-32768.json"
TOKENIZER_SHA256 = "3A69001ECC28A5BDF1E951A1036B234C9BDCB847B310252C6D72CFC6C52C48E3"
RUN_TAG = "p106b_s1b_oasst2_ko_online_s1337"
PSEUDO_OUT = DATASET_DIR / "online_pseudo_targets.jsonl"
CANONICAL_OUT = DATASET_DIR / "online_train.canonical.jsonl"
INPUT_MANIFEST_OUT = DATASET_DIR / "online_input_manifest.json"
RESULT_MANIFEST_OUT = DATASET_DIR / "online_result_manifest.json"
OUTPUT_CKPT = ROOT / f"runs/ckpt/m100R1c_ko-en_300M_{RUN_TAG}.pt"
OUTPUT_META = ROOT / f"runs/logs/m100R1c_ko-en_300M_{RUN_TAG}.json"
SEQ = 1024
MICRO = 8
ACCUM = 16
UPDATES = 2
EXPOSURES = MICRO * ACCUM
MIN_UNIQUE = 8
MAX_WALL_SEC = 2400


def digest(path: Path) -> str:
    if not regular(path):
        raise FileNotFoundError(f"required regular input absent or linked: {path}")
    return sha256_file(path)


def load_source() -> tuple[list[dict], dict]:
    if not regular(SOURCE_CANDIDATES) or not regular(SOURCE_MANIFEST):
        raise FileNotFoundError("Stage1aW candidate JSONL/manifest absent or linked")
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("schema") != "P106_STAGE1AW_OASST2_KO_CANDIDATES_V1":
        raise ValueError("Stage1aW manifest schema mismatch")
    if manifest.get("source", {}).get("source_sha256") != SOURCE_SHA256:
        raise ValueError("Stage1aW source SHA lineage mismatch")
    if manifest.get("teacher_model_sha256") != MODEL_SHA256:
        raise ValueError("Stage1aW teacher model lineage mismatch")
    if manifest.get("human_review") != "NOT_RUN" or manifest.get("train_ready") is not False:
        raise ValueError("Stage1aW candidate manifest must remain review-only")
    if digest(SOURCE_CANDIDATES) != manifest.get("output_sha256"):
        raise ValueError("Stage1aW candidate JSONL SHA mismatch")
    if manifest.get("selected") != 16 or manifest.get("recorded") != 16:
        raise ValueError("Stage1aW must have all sixteen bounded candidates")
    if manifest.get("format_outcomes", {}).get("JSON_COMPLETE", 0) < 12:
        raise ValueError("Stage1aW format gate did not reach 12/16")
    selected, _ = select_candidates()
    rows = [json.loads(line) for line in SOURCE_CANDIDATES.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    if len(rows) != len(selected) or any(
            row.get("source_tree_id") != pair["tree_id"]
            or row.get("user_en") != pair["user_en"]
            or row.get("assistant_en") != pair["assistant_en"]
            or row.get("source_sha256") != SOURCE_SHA256
            or row.get("verifier_status") != "UNKNOWN"
            or row.get("accepted_for_training") is not False
            or row.get("target_text") != ""
            for row, pair in zip(rows, selected)):
        raise ValueError("Stage1aW candidate source/selection or UNKNOWN status differs")
    return selected, manifest


def automatic_filter(pair: dict, user_ko: str, answer_ko: str) -> str:
    """A conservative *screen*, not semantic or legal verification."""
    joined = " ".join((pair["user_en"], pair["assistant_en"], user_ko, answer_ko))
    if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", joined):
        return "EMAIL_PATTERN"
    if re.search(r"(?:\+?\d[ -]?){10,14}", joined):
        return "PHONE_PATTERN"
    if re.search(r"https?://", joined, re.IGNORECASE):
        return "URL_PATTERN"
    source_numbers = sorted(re.findall(r"\d+(?:[.,]\d+)*", pair["user_en"] + " " + pair["assistant_en"]))
    translated_numbers = sorted(re.findall(r"\d+(?:[.,]\d+)*", user_ko + " " + answer_ko))
    if source_numbers != translated_numbers:
        return "DIGIT_MISMATCH"
    if len(user_ko) + len(answer_ko) > 1800:
        return "LONG_TRANSLATION"
    return "AUTO_SCREEN_PASS"


def check_inputs(*, hash_model: bool) -> dict:
    selected, source_manifest = load_source()
    if not regular(STUDENT) or STUDENT.stat().st_size < 400_000_000:
        raise FileNotFoundError("trained P076 mean student checkpoint absent, linked or too small")
    if digest(TOKENIZER) != TOKENIZER_SHA256:
        raise ValueError("legacy tokenizer SHA differs")
    if DATASET_DIR.is_symlink() or any(
            path.exists() or path.is_symlink() for path in
            (PSEUDO_OUT, CANONICAL_OUT, INPUT_MANIFEST_OUT,
             RESULT_MANIFEST_OUT, OUTPUT_CKPT, OUTPUT_META)):
        raise FileExistsError("versioned pseudo dataset output already exists; use v2/new stage on retry")
    if digest(SOURCE) != SOURCE_SHA256:
        raise ValueError("original OASST2 source SHA differs")
    teacher = asset_preflight(hash_model=hash_model)
    return {"schema": "P106B_STAGE1BW_INPUT_V1",
            "tag": RUN_TAG,
            "source_candidate_sha256": source_manifest["output_sha256"],
            "source_selected": len(selected), "teacher": teacher,
            "student_path": STUDENT.relative_to(ROOT).as_posix(),
            "student_bytes": STUDENT.stat().st_size,
            "student_sha256": digest(STUDENT) if hash_model else "NOT_RUN",
            "tokenizer_sha256": TOKENIZER_SHA256,
            "micro_bs": MICRO, "accum": ACCUM, "activation_checkpoint": True,
            "max_seq": SEQ, "max_updates": UPDATES,
            "max_processed_positions": UPDATES * EXPOSURES * SEQ,
            "pseudo_labels": "UNVERIFIED_TEACHER_OUTPUT",
            "formal_train_ready": False, "checkpoint_write": False}


def student_model_and_optimizers():
    import torch
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.infer.generate import _strip
    from tinylm.train.muon import Muon, split_params
    from tinylm.train.optimizer_audit import matrix_decay_groups

    if not torch.cuda.is_available():
        raise RuntimeError("PyTorch CUDA unavailable")
    torch.set_num_threads(1)
    torch.manual_seed(1337)
    state = torch.load(STUDENT, map_location="cpu", weights_only=True)
    cfg = TMTConfig(**state["cfg"])
    if (cfg.vocab_size != 32768 or cfg.max_seq_len != SEQ
            or cfg.cla_group != 2 or cfg.attn_group != 2 or not cfg.tie_mlp):
        raise ValueError("P076 B3 student geometry/tokenizer differs from preregistered arm")
    cfg.grad_checkpoint = True
    base_model = TiedMLPTransformer(cfg).cuda()
    base_model.load_state_dict(_strip(state["model"]), strict=True)
    base_model.set_anneal(1.0)
    base_model.train()
    cache_dir = tempfile.mkdtemp(prefix="tinylm_p106b_stage1bw_")
    os.environ["TORCHINDUCTOR_CACHE_DIR"] = cache_dir
    model = torch.compile(base_model, mode="default")
    groups, _ = matrix_decay_groups(model, 1e-4, 0)
    matrices, _ = split_params(model)
    matrix_ids = {id(param) for param in matrices}
    others = []
    for group in groups:
        params = [param for param in group["params"] if id(param) not in matrix_ids]
        if params:
            others.append(dict(group, params=params))
    adamw = torch.optim.AdamW(others, betas=(0.9, 0.95), eps=1e-8)
    muon = Muon(matrices, lr=4e-4, scale_mode="rms", weight_decay=0)
    return torch, model, base_model, adamw, muon, cfg, state.get("step"), cache_dir


def train_updates(torch, model, adamw, muon, cfg, pairs: list[dict]) -> list[dict]:
    from tokenizers import Tokenizer
    from scripts.train_sft_p090 import encode_records, loss_sum

    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    pad_id = tokenizer.token_to_id("<pad>")
    if pad_id is None:
        raise ValueError("student tokenizer has no PAD token")
    rows = [{"messages": [{"role": "user", "content": pair["user_ko"]},
                          {"role": "assistant", "content": pair["assistant_ko"]}],
             "meta": {"source": "oasst2_teacher_pseudo", "source_id": pair["source_tree_id"]}}
            for pair in pairs]
    encoded = encode_records(rows, tokenizer, SEQ, cfg.vocab_size)
    if len(encoded) < MIN_UNIQUE:
        raise ValueError("too few unique pseudo-label records after tokenization")
    results = []
    for step in range(UPDATES):
        order = [i % len(encoded) for i in range(EXPOSURES)]
        random.Random(1337 + step).shuffle(order)
        target_count = sum(encoded[index][2] for index in order)
        if target_count <= 0:
            raise ValueError("assistant supervised target count is zero")
        adamw.zero_grad(set_to_none=True)
        muon.zero_grad(set_to_none=True)
        torch.cuda.reset_peak_memory_stats()
        begun = time.monotonic()
        loss_sum_value = 0.0
        for start in range(0, EXPOSURES, MICRO):
            block = [encoded[index] for index in order[start:start+MICRO]]
            part = loss_sum(model, block, pad_id, torch.device("cuda"), cfg.vocab_size, 2048)
            if not bool(torch.isfinite(part)):
                raise RuntimeError("nonfinite assistant-only SFT loss")
            (part / target_count).backward()
            loss_sum_value += float(part.detach())
        grad = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        if not math.isfinite(float(grad)):
            raise RuntimeError("nonfinite pseudo SFT gradient")
        adamw.step()
        muon.step()
        torch.cuda.synchronize()
        result = {"update": step + 1, "micro_bs": MICRO, "accum": ACCUM,
                  "conversation_exposures": EXPOSURES,
                  "unique_conversations": len(encoded),
                  "assistant_supervised_tokens": target_count,
                  "assistant_ce": round(loss_sum_value / target_count, 8),
                  "grad_norm_before_clip": round(float(grad), 6),
                  "wall_sec": round(time.monotonic() - begun, 3),
                  "peak_allocated_mib": torch.cuda.max_memory_allocated() // 2**20,
                  "peak_reserved_mib": torch.cuda.max_memory_reserved() // 2**20}
        results.append(result)
        print("[STUDENT_STEP] " + json.dumps(result, sort_keys=True), flush=True)
    return results


def diagnostic_metadata(report: dict, inputs: dict, canonical_sha: str,
                        updates: list[dict], param_count: int) -> dict:
    """P100-compatible pair, explicitly without a measured validation score."""
    return {
        "schema": "P106B_DIAGNOSTIC_TRAIN_METADATA_V1",
        "tag": OUTPUT_META.stem, "arch": "tied", "preset": "m100R1c",
        "data": "ko-en", "parent_train_budget": "300M",
        "steps": UPDATES,
        "tokens": sum(item["assistant_supervised_tokens"] for item in updates),
        "tokens_semantics": "assistant_only_supervised_tokens_not_parent_budget",
        "processed_positions_upper_bound": UPDATES * EXPOSURES * SEQ,
        "params": param_count,
        "final": {"val_loss": None}, "best_val": None,
        "checkpoint_sha256": report["checkpoint_sha256"],
        "parent_checkpoint_sha256": inputs["student_sha256"],
        "source_manifest_sha256": inputs["source_candidate_sha256"],
        "pseudo_target_sha256": canonical_sha,
        "label_status": "PSEUDO_UNVERIFIED",
        "quality": "NOT_RUN",
        "short_probe_exclude_wandb": True,
    }


def execute() -> int:
    from collections import Counter
    import torch

    inputs = check_inputs(hash_model=True)
    apps = _compute_apps()
    if apps:
        print("[HOLD] competing GPU compute process; no model started")
        return 8
    base_used, base_free = read_memory()
    if base_free < 14_000:
        print(f"[HOLD] GPU free {base_free}MiB below 14000MiB; no model started")
        return 8
    selected, _ = load_source()
    torch, model, base_model, adamw, muon, cfg, parent_step, cache_dir = student_model_and_optimizers()
    torch.cuda.synchronize()
    student_free = read_memory()[1]
    print(f"[STUDENT_READY] trained P076 mean step={parent_step} ckpt=ON compile=default "
          f"micro={MICRO} accum={ACCUM} free_mib={student_free} cache={cache_dir}", flush=True)
    port, key = _free_port(), os.urandom(24).hex()
    command = [str(SERVER), "--offline", "--model", str(MODEL),
               "--host", "127.0.0.1", "--port", str(port), "--api-key", key,
               "--no-webui", "--cors-origins", "localhost", "--no-cors-credentials",
               "--cache-ram", "0", "--verbosity", "4", "--ctx-size", str(TEACHER_CTX),
               "--batch-size", "64", "--ubatch-size", "64", "--threads", "8",
               "--no-warmup", "--fit", "off", "--no-op-offload", "--gpu-layers", "all",
               "--chat-template-kwargs", '{"reasoning_effort":"medium"}']
    server = None
    server_lines: list[str] = []
    stop = threading.Event()
    memory_samples = [base_used]
    sample_errors: list[str] = []
    begin = time.monotonic()
    try:
        server = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, errors="replace", bufsize=1,
                                  start_new_session=True)

        def drain() -> None:
            assert server is not None and server.stdout is not None
            for line in server.stdout:
                if any(token in line for token in ("fused Gated Delta Net", "error", "failed")):
                    server_lines.append(line.strip()[:500])
                    if len(server_lines) > 48:
                        del server_lines[:24]
        threading.Thread(target=drain, daemon=True).start()

        def sample() -> None:
            while not stop.wait(0.2):
                try:
                    used, free = read_memory()
                    memory_samples.append(used)
                    if free < 512:
                        sample_errors.append("FREE_LT_512")
                        return
                except (OSError, RuntimeError, ValueError, IndexError) as exc:
                    sample_errors.append(type(exc).__name__)
                    return
        threading.Thread(target=sample, daemon=True).start()
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError(f"teacher server exited before health rc={server.returncode}")
            try:
                _http_json(f"http://127.0.0.1:{port}/health", key, timeout=3)
                break
            except (OSError, HTTPError, URLError, ValueError):
                time.sleep(0.25)
        else:
            raise TimeoutError("teacher server health timeout")
        ready_used, ready_free = read_memory()
        if ready_free < 2048:
            print(f"[GATE NEGATIVE] combined free {ready_free}MiB below 2048MiB")
            return 8
        fusion_deadline = time.monotonic() + 5
        while time.monotonic() < fusion_deadline:
            if (any("fused Gated Delta Net (autoregressive) enabled" in s for s in server_lines)
                    and any("fused Gated Delta Net (chunked) enabled" in s for s in server_lines)):
                break
            time.sleep(0.1)
        else:
            print("[GATE NEGATIVE] teacher GDN fusion not observed at trace4 before student update")
            return 8
        accepted: list[dict] = []
        counts: Counter[str] = Counter()
        total_completion_tokens = 0
        usage_rows = 0
        teacher_begin = time.monotonic()
        DATASET_DIR.mkdir(parents=True, exist_ok=True)
        with PSEUDO_OUT.open("x", encoding="utf-8") as stream:
            for pair in selected:
                if time.monotonic() - begin >= MAX_WALL_SEC or sample_errors:
                    counts["TIME_OR_MEMORY_BUDGET"] += 1
                    break
                reply = _http_json(f"http://127.0.0.1:{port}/v1/chat/completions", key,
                                   {"messages": translation_prompt(pair), "temperature": 0,
                                    "max_tokens": MAX_OUTPUT_TOKENS,
                                    "reasoning_effort": "medium", "stream": False}, timeout=120)
                status, user_ko, answer_ko = parse_translation(reply)
                if status == "JSON_COMPLETE":
                    status = automatic_filter(pair, user_ko, answer_ko)
                counts[status] += 1
                usage = reply.get("usage") or {}
                observed_tokens = usage.get("completion_tokens")
                if type(observed_tokens) is int and observed_tokens >= 0:
                    total_completion_tokens += observed_tokens
                    usage_rows += 1
                else:
                    counts["USAGE_MISSING"] += 1
                row = {"source_tree_id": pair["tree_id"], "source_sha256": SOURCE_SHA256,
                       "user_en": pair["user_en"], "assistant_en": pair["assistant_en"],
                       "teacher_user_ko": user_ko, "teacher_assistant_ko": answer_ko,
                       "screen_status": status, "truth_status": "PSEUDO_UNVERIFIED",
                       "verified_p106_accept": False,
                       "auto_selected_for_pilot": status == "AUTO_SCREEN_PASS"}
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                if status == "AUTO_SCREEN_PASS":
                    accepted.append({"source_tree_id": pair["tree_id"],
                                     "user_ko": user_ko, "assistant_ko": answer_ko})
        teacher_elapsed = round(time.monotonic() - teacher_begin, 2)
        output_sha = digest(PSEUDO_OUT)
        sampled_free = base_free - (max(memory_samples) - base_used)
        if len(accepted) < MIN_UNIQUE or sample_errors or sampled_free < 2048:
            print(json.dumps({"schema": "P106B_STAGE1BW_PRETRAIN_GATE_V1",
                              "source_sha256": SOURCE_SHA256,
                              "pseudo_output_sha256": output_sha,
                              "teacher_format_and_screen": dict(counts),
                              "unique_accepted": len(accepted),
                              "completion_tokens_reported": (total_completion_tokens
                                                              if not counts["USAGE_MISSING"]
                                                              else "PARTIAL_OR_NOT_RUN"),
                              "usage_rows": usage_rows,
                              "sampled_free_mib": sampled_free,
                              "sample_errors": sample_errors,
                              "student_updates": 0, "train_ready": False}, sort_keys=True))
            print("[GATE NEGATIVE] too few screened pseudo pairs or inadequate sampled VRAM; updates=0")
            return 8
        from tinylm.chat.canonical import normalize, validate
        canonical_rows = []
        for pair in accepted:
            row = validate(normalize({"messages": [
                {"role": "user", "content": pair["user_ko"]},
                {"role": "assistant", "content": pair["assistant_ko"]},
            ], "meta": {"source": "p106b_oasst2_teacher_pseudo",
                        "source_id": pair["source_tree_id"],
                        "source_revision": "179dd21fc55192153d94adb0e0ce8f69e222bf75",
                        "source_license": "Apache-2.0_card_only",
                        "teacher_model_sha256": MODEL_SHA256,
                        "label_status": "PSEUDO_UNVERIFIED",
                        "language": "ko"}}))
            canonical_rows.append(row)
        with CANONICAL_OUT.open("x", encoding="utf-8") as stream:
            for row in canonical_rows:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        canonical_sha = digest(CANONICAL_OUT)
        input_manifest = {"schema": "P106B_ONLINE_PSEUDO_INPUT_V1",
                          "dataset_version": "p106b_teacher_sft/v1",
                          "source_sha256": SOURCE_SHA256,
                          "teacher_model_sha256": MODEL_SHA256,
                          "student_checkpoint_sha256": inputs["student_sha256"],
                          "tokenizer_sha256": TOKENIZER_SHA256,
                          "raw_teacher_sha256": output_sha,
                          "canonical_train_sha256": canonical_sha,
                          "canonical_train_rows": len(canonical_rows),
                          "auto_screen": dict(counts),
                          "human_quality_gate": "NOT_RUN",
                          "verifier_truth_gate": "NOT_RUN",
                          "benchmark_contamination_gate": "NOT_RUN",
                          "label_status": "PSEUDO_UNVERIFIED",
                          "formal_train_ready": False}
        with INPUT_MANIFEST_OUT.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(input_manifest, ensure_ascii=False, indent=2) + "\n")
        updates = train_updates(torch, model, adamw, muon, cfg, accepted)
        sampled_free = base_free - (max(memory_samples) - base_used)
        report = {"schema": "P106B_STAGE1BW_ONLINE_PSEUDO_SFT_V1",
                  "tag": RUN_TAG,
                  "teacher_model_sha256": MODEL_SHA256,
                  "student_checkpoint_sha256": inputs["student_sha256"],
                  "student_checkpoint_step": parent_step,
                  "tokenizer_sha256": TOKENIZER_SHA256,
                  "source_candidate_sha256": inputs["source_candidate_sha256"],
                  "pseudo_output_sha256": output_sha,
                  "canonical_train_sha256": canonical_sha,
                  "canonical_train_rows": len(canonical_rows),
                  "dataset_version": "p106b_teacher_sft/v1",
                  "teacher_format_and_screen": dict(counts),
                  "teacher_completion_tokens_reported": (total_completion_tokens
                                                         if not counts["USAGE_MISSING"]
                                                         else "PARTIAL_OR_NOT_RUN"),
                  "teacher_usage_rows": usage_rows,
                  "teacher_generation_elapsed_sec": teacher_elapsed,
                  "teacher_wall_sec_per_auto_selected_pair": round(teacher_elapsed / len(accepted), 3),
                  "teacher_completion_tokens_per_auto_selected_pair": (
                      round(total_completion_tokens / len(accepted), 3)
                      if not counts["USAGE_MISSING"] else "PARTIAL_OR_NOT_RUN"),
                  "whole_wall_sec": round(time.monotonic()-begin, 2),
                  "sampled_free_mib": sampled_free,
                  "sample_count": len(memory_samples),
                  "gdn_ar_enabled": any("fused Gated Delta Net (autoregressive) enabled" in s for s in server_lines),
                  "gdn_chunked_enabled": any("fused Gated Delta Net (chunked) enabled" in s for s in server_lines),
                  "student": {"arch": "m100R1c_tied_ag2_cla2_p076_mean", "micro_bs": MICRO,
                              "accum": ACCUM, "activation_checkpoint": True,
                              "optimizer": "Muon_RMS4_x4_plus_AdamW", "lr": 1e-4,
                              "updates": updates, "compiled": True},
                  "teacher_and_student_co_resident": True,
                  "pseudo_label_status": "UNVERIFIED_NOT_P106_ACCEPT",
                  "formal_train_ready": False, "checkpoint_written": False,
                  "quality": "NOT_RUN", "limits": "16 source pairs, repeated to 128 exposures/update, two updates; no generalization claim"}
        if sample_errors or sampled_free < 2048:
            print("[GATE NEGATIVE] sampled VRAM margin or sensor failed")
            return 8 if not sample_errors else 9
        # The server was co-resident for every student update. Stop it before
        # serializing the checkpoint; a partial write has no result manifest.
        stop.set()
        _kill_group(server)
        server = None
        checkpoint = {"model": base_model.state_dict(), "cfg": cfg.__dict__,
                      "step": (int(parent_step) if parent_step is not None else 0) + UPDATES,
                      "tokenizer_lineage": "legacy", "tokenizer_sha256": TOKENIZER_SHA256,
                      "p106b": {"source": "oasst2_en_terminal_single_turn",
                                "source_sha256": SOURCE_SHA256,
                                "teacher_model_sha256": MODEL_SHA256,
                                "parent_sha256": inputs["student_sha256"],
                                "pseudo_target_sha256": canonical_sha,
                                "label_status": "PSEUDO_UNVERIFIED",
                                "updates": UPDATES, "micro_bs": MICRO, "accum": ACCUM,
                                "activation_checkpoint": True}}
        with OUTPUT_CKPT.open("xb") as stream:
            torch.save(checkpoint, stream)
        report["checkpoint_written"] = True
        report["checkpoint_path"] = OUTPUT_CKPT.relative_to(ROOT).as_posix()
        report["checkpoint_sha256"] = digest(OUTPUT_CKPT)
        report["checkpoint_bytes"] = OUTPUT_CKPT.stat().st_size
        training_meta = diagnostic_metadata(
            report, inputs, canonical_sha, updates,
            sum(param.numel() for param in base_model.parameters()))
        with OUTPUT_META.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(training_meta, ensure_ascii=False, indent=2) + "\n")
        report["paired_training_metadata_path"] = OUTPUT_META.relative_to(ROOT).as_posix()
        report["paired_training_metadata_sha256"] = digest(OUTPUT_META)
        with RESULT_MANIFEST_OUT.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
        print("[PASS] bounded online teacher pseudo-label SFT checkpoint written; model quality NOT_RUN")
        return 0
    finally:
        stop.set()
        _kill_group(server)


def self_test() -> None:
    from tinylm.data.prepare import SyntheticTokenizer
    from scripts.train_sft_p090 import encode_records

    pair = {"user_en": "What is 2+2?", "assistant_en": "It is 4."}
    assert automatic_filter(pair, "2+2는 무엇인가요?", "4입니다.") == "AUTO_SCREEN_PASS"
    assert automatic_filter(pair, "2+3은 무엇인가요?", "4입니다.") == "DIGIT_MISMATCH"
    assert automatic_filter(pair, "메일은 a@b.com", "네") == "EMAIL_PATTERN"
    good = {"messages": [{"role": "user", "content": "안녕?"},
                         {"role": "assistant", "content": "안녕하세요."}]}
    records = encode_records([good], SyntheticTokenizer(), 1024, 32768)
    assert len(records) == 1 and records[0][2] > 0
    assert MICRO * ACCUM == 128 and UPDATES * MICRO * ACCUM * SEQ == 262144
    meta = diagnostic_metadata(
        {"checkpoint_sha256": "A"},
        {"student_sha256": "B", "source_candidate_sha256": "C"},
        "D", [{"assistant_supervised_tokens": 42},
              {"assistant_supervised_tokens": 43}], 100)
    assert meta["tokens"] == 85 and meta["final"]["val_loss"] is None
    assert meta["tag"] == OUTPUT_META.stem and meta["checkpoint_sha256"] == "A"
    print("[PASS] P106B pseudo-label filter, assistant-only target and micro8/accum16 fixture; GPU/model NOT_RUN")


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    if sum((args.self_test, args.check_only, args.execute)) != 1:
        ap.error("choose exactly one mode")
    try:
        if args.self_test:
            self_test()
            return 0
        try:
            report = check_inputs(hash_model=False)
        except FileNotFoundError as exc:
            print(f"[HOLD] {exc}; Stage1aW user result is required")
            return 8
        if args.check_only:
            print(json.dumps(report, sort_keys=True))
            print("[CHECK_ONLY] source/parent/tokenizer contract PASS; teacher/student/GPU NOT_RUN")
            return 0
        def time_limit(_signum, _frame):
            raise TimeoutError("P106B Stage1bW exceeded 2700s hard wall")
        prior = signal.signal(signal.SIGALRM, time_limit)
        signal.alarm(2700)
        try:
            return execute()
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, prior)
    except FileExistsError as exc:
        print(f"[STOP] {exc}", file=sys.stderr)
        return 9
    except MemoryError as exc:
        print(f"[GATE NEGATIVE] {exc}", file=sys.stderr)
        return 8
    except Exception as exc:  # noqa: BLE001 - bounded user-run entry reports exact tool failure
        print(f"[FAIL] P106B Stage1bW {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
