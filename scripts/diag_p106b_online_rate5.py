#!/usr/bin/env python3
"""P106B Stage2iW: five *real* online optimizer updates, no checkpoint.

One fresh teacher answer is requested for each of the eight conversations in
every microbatch.  Thus five complete updates require 5*16*8=640 accepted
teacher answers.  This is a throughput/resource pilot, NOT a quality result or
permission to scale the run to 300M tokens.  Every attempted response and every
student target is written once to a new, <=20MB-sharded HF version.  The
teacher's reasoning is kept only in the raw sidecar, never in the SFT target.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_p106b_job_deck import OUTPUT as JOB_DIR, OUTPUT_MANIFEST  # noqa: E402
from scripts.diag_p106_bonsai_assets import sha256_file  # noqa: E402
from scripts.diag_p106_coload import _free_port, _http_json  # noqa: E402
from scripts.diag_p106_full_coload_accum import _compute_apps, _kill_group  # noqa: E402
from scripts.diag_p106_oasst2_teacher_ko_gate import MODEL, MODEL_SHA256, SERVER, asset_preflight  # noqa: E402
from scripts.diag_p106_vram_sample import read_memory  # noqa: E402
from scripts.diag_p106b_online_pseudo_sft import (  # noqa: E402
    ACCUM, MICRO, SEQ, STUDENT, TOKENIZER, TOKENIZER_SHA256,
    student_model_and_optimizers,
)
from scripts.diag_p106b_teacher_answer_repair import SAMPLER  # noqa: E402
from scripts.p106b_shards import ShardWriter, verify  # noqa: E402
from scripts.p106b_teacher_format import parse_reply, teacher_prompt  # noqa: E402
from scripts.p106b_teacher_wrapper import wrap_turns  # noqa: E402
from scripts.p106b_http_errors import capture_http_error  # noqa: E402
from scripts.train_sft_p090 import encode_records, loss_sum  # noqa: E402

UPDATES = 5
MAX_WALL_SEC = 6 * 3600
MAX_ATTEMPTS_PER_LANGUAGE = 365
STUDENT_SHA256 = "41036721CEAAE3EACA568BF45FA5079745EBAE85B42033D28ECC9709F5D00A71"
OUTPUT_BASE = ROOT / "HF/sft_ready/p106b_teacher_sft"
PUBLIC_V3_MANIFEST = ROOT / "HF/sft_ready/p090_public_v3_manifest.json"
BILINGUAL_REPORT = ROOT / "HF/sft_ready/p106b_bilingual_v2/teacher_recovery/recovery_manifest.json"
THINKING_SAMPLER = {k: v for k, v in SAMPLER.items() if k != "reasoning_effort"}
# PrismML GGUF model card, "Generation Parameters" (read 2026-09-28).
# The earlier Stage2hW none arm used the thinking sampler, so its none timing
# is only a setup baseline and is NOT a paired estimate for this card profile.
INSTRUCT_SAMPLER = {"temperature": 0.7, "top_p": 0.80, "top_k": 20,
                    "min_p": 0.0, "presence_penalty": 1.5,
                    "repeat_penalty": 1.0, "stream": False}
MODEL_CARD = "https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf"
EFFORT_CONFIG = {
    "none": (1536, 1024),
    "low": (3072, 2048),
    "medium": (6144, 4096),
}


class GateNegative(Exception):
    """Valid partial/negative resource or format result, not an implementation PASS."""


class PrerequisiteHold(ValueError):
    """An upstream experiment is absent or negative; block student GPU loading."""


class ToolFailure(Exception):
    """Unknown backend/API failure; never report as a scientific negative."""


def require_bilingual_panel(source: dict) -> dict:
    if BILINGUAL_REPORT.is_symlink() or not BILINGUAL_REPORT.is_file():
        raise PrerequisiteHold("Stage2fWb bilingual recovery report absent; online GPU blocked")
    report = json.loads(BILINGUAL_REPORT.read_text(encoding="utf-8"))
    counts = report.get("combined_format_and_screen", {})
    if (report.get("schema") != "P106B_STAGE2FWB_BILINGUAL_RECOVERY_V1"
            or report.get("source", {}).get("job_deck_sha256") != source["job_deck_sha256"]
            or report.get("tool_error")
            or min(counts.get("ko:CANDIDATE", 0), counts.get("en:CANDIDATE", 0)) < 12):
        raise PrerequisiteHold("Stage2fWb bilingual format/lineage gate not passed")
    relative = report.get("new_raw_manifest")
    if not isinstance(relative, str) or not relative.startswith(
            "HF/sft_ready/p106b_bilingual_v2/teacher_recovery/"):
        raise ValueError("Stage2fWb raw manifest path invalid")
    manifest = ROOT / relative
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError("Stage2fWb raw manifest absent or linked")
    record = json.loads(manifest.read_text(encoding="utf-8"))
    verify(manifest.parent, record)
    if record.get("concat_sha256") != report.get("new_raw_concat_sha256"):
        raise ValueError("Stage2fWb raw SHA differs from recovery report")
    return {"recovery_manifest_sha256": sha256_file(BILINGUAL_REPORT),
            "candidate_counts": {lang: counts[f"{lang}:CANDIDATE"] for lang in ("ko", "en")}}


def source_jobs() -> tuple[dict[str, list[dict]], dict]:
    if OUTPUT_MANIFEST.is_symlink() or not OUTPUT_MANIFEST.is_file():
        raise FileNotFoundError("finite public-v3 job deck missing; run Stage2eW first")
    manifest = json.loads(OUTPUT_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("schema") != "P106B_STAGE2EW_JOB_DECK_V1":
        raise ValueError("job-deck schema differs")
    shard_manifest = JOB_DIR / "train_shards_manifest.json"
    if shard_manifest.is_symlink() or not shard_manifest.is_file():
        raise FileNotFoundError("job deck train shard manifest missing or linked")
    spec = json.loads(shard_manifest.read_text(encoding="utf-8"))
    if (spec.get("concat_sha256") != manifest.get("splits", {}).get("train", {}).get("concat_sha256")
            or spec.get("rows") != manifest.get("splits", {}).get("train", {}).get("rows")):
        raise ValueError("job deck train lineage differs")
    verify(JOB_DIR, spec)
    jobs: dict[str, dict[str, dict]] = {"ko": {}, "en": {}}
    for shard in spec["shards"]:
        with (JOB_DIR / shard["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                language = row["target_language"]
                if (row["source"] != "oasst" or row["source_language"] != "en"
                        or row["split"] != "train" or len(row["source_turns"]) != 1
                        or row["task"] != ("translate" if language == "ko" else "repair")):
                    continue
                turn = row["source_turns"][0]
                if (len(turn["user_text"]) > 1200 or len(turn["assistant_text"]) > 1200):
                    continue
                if row["concept_id"] in jobs[language]:
                    raise ValueError("duplicate public source concept in language")
                jobs[language][row["concept_id"]] = row
    paired = sorted(set(jobs["ko"]) & set(jobs["en"]),
                    key=lambda value: hashlib.sha256(("p106b_online5:" + value).encode()).hexdigest())
    if len(paired) < 320:
        raise ValueError("fewer than 320 paired bounded OASST1 source concepts")
    if (PUBLIC_V3_MANIFEST.is_symlink() or not PUBLIC_V3_MANIFEST.is_file()
            or sha256_file(PUBLIC_V3_MANIFEST) != manifest["source"]["public_manifest_sha256"]):
        raise ValueError("public v3 exact manifest lineage differs")
    public = json.loads(PUBLIC_V3_MANIFEST.read_text(encoding="utf-8"))
    if public.get("sources", {}).get("oasst", {}).get("repo") != "OpenAssistant/oasst1":
        raise ValueError("public v3 oasst source is not pinned OASST1")
    selected = {language: [jobs[language][key] for key in paired]
                for language in ("ko", "en")}
    return selected, {"job_deck_sha256": sha256_file(OUTPUT_MANIFEST),
                      "train_jobs_sha256": spec["concat_sha256"],
                      "paired_concepts": len(paired),
                      "source_sha256": manifest["source"]["source_sha256"]["train"],
                      "source_card_licenses": manifest["source"]["source_card_licenses"],
                      "source_repos": {key: {"repo": value["repo"], "revision": value["revision"]}
                                       for key, value in public["sources"].items()},
                      "policy": "OASST1-only 320 paired concepts, one fresh response per language/job; same concepts across languages, no within-language reuse"}


def paths(effort: str, variant: str = "initial") -> tuple[Path, Path]:
    if variant == "initial":
        directory = OUTPUT_BASE / f"v10_online_rate5_{effort}"
        report_name = "online_rate5_manifest.json"
    elif variant == "backend1" and effort == "low":
        directory = OUTPUT_BASE / "v13_online_rate1_low_backend"
        report_name = "online_rate1_manifest.json"
    else:
        raise ValueError("unknown online output variant/effort")
    return directory, directory / report_name


def check_only(effort: str, variant: str = "initial") -> dict:
    jobs, source = source_jobs()
    bilingual = require_bilingual_panel(source)
    if STUDENT.is_symlink() or not STUDENT.is_file() or STUDENT.stat().st_size < 400_000_000:
        raise FileNotFoundError("P076 B3 student parent missing or linked")
    if sha256_file(TOKENIZER) != TOKENIZER_SHA256:
        raise ValueError("legacy tokenizer SHA differs")
    if sha256_file(STUDENT) != STUDENT_SHA256:
        raise ValueError("P076 mean student parent SHA differs")
    directory, manifest = paths(effort, variant)
    if directory.exists() or directory.is_symlink() or manifest.exists():
        raise FileExistsError("online output version already exists")
    target_updates = 1 if variant == "backend1" else UPDATES
    return {"schema": ("P106B_STAGE2IWD_ONLINE_RATE1_INPUT_V1" if variant == "backend1"
                       else "P106B_STAGE2IW_ONLINE_RATE5_INPUT_V1"), "effort": effort,
            "ctx_and_cap": EFFORT_CONFIG[effort], "updates": target_updates,
            "micro": MICRO, "accum": ACCUM,
            "needed_accepted_answers": target_updates * MICRO * ACCUM,
            "candidate_jobs_per_language": {k: len(v) for k, v in jobs.items()},
            "source": source, "bilingual_gate": bilingual,
            "student_parent": STUDENT.relative_to(ROOT).as_posix(),
            "model_gpu": "NOT_RUN", "quality": "NOT_RUN"}


def self_test() -> None:
    assert MICRO == 8 and ACCUM == 16 and UPDATES == 5
    assert UPDATES * MICRO * ACCUM == 640
    assert {"none", "low", "medium"} == set(EFFORT_CONFIG)
    assert all(context >= maximum for context, maximum in EFFORT_CONFIG.values())
    assert INSTRUCT_SAMPLER["temperature"] == 0.7
    assert THINKING_SAMPLER["temperature"] == 1.0
    assert paths("low", "backend1")[1].name == "online_rate1_manifest.json"
    assert paths("low", "initial")[1].name == "online_rate5_manifest.json"
    print("[PASS] five updates require 640 accepted fresh teacher answers; no repeats/ckpt; GPU NOT_RUN")


def execute(effort: str, wall_limit: int, variant: str = "initial") -> int:
    from tokenizers import Tokenizer
    import torch

    inputs = check_only(effort, variant)
    if _compute_apps():
        print("[HOLD] competing GPU compute app; no student/teacher started")
        return 8
    if read_memory()[1] < 14_000:
        print("[HOLD] GPU free below 14000MiB; no student/teacher started")
        return 8
    teacher_assets = asset_preflight(hash_model=True)
    jobs, source = source_jobs()
    directory, manifest_path = paths(effort, variant)
    target_updates = inputs["updates"]
    context, max_tokens = EFFORT_CONFIG[effort]
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    pad_id = tokenizer.token_to_id("<pad>")
    if pad_id is None:
        raise ValueError("student tokenizer has no PAD token")
    torch, model, _base, adamw, muon, cfg, parent_step, cache_dir = student_model_and_optimizers()
    torch.cuda.synchronize()
    print(f"[STUDENT_READY] parent_step={parent_step} compile=default ckpt=ON "
          f"micro={MICRO} accum={ACCUM} free_mib={read_memory()[1]} cache={cache_dir}", flush=True)
    port, key = _free_port(), os.urandom(24).hex()
    command = [str(SERVER), "--offline", "--model", str(MODEL),
               "--host", "127.0.0.1", "--port", str(port), "--api-key", key,
               "--no-webui", "--cors-origins", "localhost", "--no-cors-credentials",
               "--cache-ram", "0", "--verbosity", "4", "--ctx-size", str(context),
               "--batch-size", "64", "--ubatch-size", "64", "--threads", "8",
               "--no-warmup", "--fit", "off", "--no-op-offload", "--gpu-layers", "all",
               "--reasoning", "auto"]
    server = None
    stop = threading.Event()
    samples: list[int] = []
    sample_errors: list[str] = []
    server_lines: list[str] = []
    counts: Counter[str] = Counter()
    updates: list[dict] = []
    all_seen: set[str] = set()
    used = {"ko": 0, "en": 0}
    started = time.monotonic()
    status, reason = "PARTIAL", "not_started"
    raw_writer = canonical_writer = None
    accepted_total = 0
    tool_failure = False
    try:
        server = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, errors="replace", bufsize=1,
                                  start_new_session=True)

        def drain() -> None:
            assert server is not None and server.stdout is not None
            for line in server.stdout:
                if "fused Gated Delta Net" in line or "error" in line or "failed" in line:
                    server_lines.append(line.replace(key, "<redacted-api-key>").strip()[:400])
                    if len(server_lines) > 48:
                        del server_lines[:24]

        def sample() -> None:
            while not stop.wait(0.2):
                try:
                    used_mib, free_mib = read_memory()
                    samples.append(used_mib)
                    if free_mib < 512:
                        sample_errors.append("FREE_LT_512")
                        return
                except (OSError, RuntimeError, ValueError, IndexError) as exc:
                    sample_errors.append(type(exc).__name__)
                    return

        threading.Thread(target=drain, daemon=True).start()
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
        if read_memory()[1] < 2048:
            raise GateNegative("co-resident free VRAM below 2048MiB")
        directory.mkdir(parents=True, exist_ok=False)
        raw_writer = ShardWriter(directory, "raw")
        canonical_writer = ShardWriter(directory, "canonical")
        for update_index in range(1, target_updates + 1):
            adamw.zero_grad(set_to_none=True)
            muon.zero_grad(set_to_none=True)
            torch.cuda.reset_peak_memory_stats()
            update_started = time.monotonic()
            teacher_wall = student_wall = 0.0
            completion_tokens = processed_tokens = supervised_tokens = 0
            language_tokens = {"ko": 0, "en": 0}
            update_generation_ids: list[str] = []
            for micro_index in range(1, ACCUM + 1):
                language = "ko" if micro_index % 2 else "en"
                batch = []
                while len(batch) < MICRO:
                    if sample_errors:
                        raise GateNegative("GPU memory sampler failed or free<512MiB")
                    if time.monotonic() - started >= wall_limit:
                        raise GateNegative("authorized online wall limit reached before five updates")
                    cursor = used[language]
                    if cursor >= min(len(jobs[language]), MAX_ATTEMPTS_PER_LANGUAGE):
                        raise GateNegative(f"{language} finite source pool exhausted before five updates")
                    job = jobs[language][cursor]
                    used[language] += 1
                    turn = job["source_turns"][0]
                    source_payload = {"user_en": turn["user_text"],
                                      "original_assistant_en": turn["assistant_text"]}
                    prompt = teacher_prompt(job["task"], language, source_payload)
                    seed = 20260928 + cursor
                    sampler = (INSTRUCT_SAMPLER if effort == "none" else THINKING_SAMPLER)
                    payload = {"messages": prompt, **sampler,
                               "max_tokens": max_tokens, "reasoning_effort": effort,
                               "seed": seed}
                    t0 = time.monotonic()
                    try:
                        reply = _http_json(f"http://127.0.0.1:{port}/v1/chat/completions",
                                           key, payload, timeout=120)
                        parsed = parse_reply(reply, language=language)
                        backend = None
                    except HTTPError as exc:
                        parsed = None
                        backend = capture_http_error(exc, key)
                    except (URLError, TimeoutError, OSError) as exc:
                        parsed = None
                        backend = {"http_status": None, "error_type": type(exc).__name__,
                                   "classification": "UNKNOWN_BACKEND_ERROR",
                                   "message": str(exc)[:400]}
                    elapsed = time.monotonic() - t0
                    teacher_wall += elapsed
                    usage = parsed["usage"].get("completion_tokens") if parsed else None
                    if type(usage) is int and usage >= 0:
                        completion_tokens += usage
                    elif parsed is not None:
                        counts["USAGE_MISSING"] += 1
                    generation_id = f"u{update_index:02d}m{micro_index:02d}a{cursor:03d}{language}"
                    record = {"schema": "P106B_STAGE2IW_RAW_ATTEMPT_V1",
                              "generation_id": generation_id, "job_id": job["job_id"],
                              "concept_id": job["concept_id"], "language": language,
                              "source": source_payload, "effort": effort,
                              "seed": seed, "request_wall_sec": round(elapsed, 3),
                              "teacher": parsed, "backend_error": backend,
                              "planned_update": update_index,
                              "planned_microbatch": micro_index,
                              "accepted_for_training": False,
                              "selected_for_pilot_microbatch": False}
                    content = parsed.get("parsed_content") if parsed else None
                    encoded = None
                    if backend is not None:
                        record["screen_status"] = backend["classification"]
                    elif content is None:
                        record["screen_status"] = parsed["format_status"]
                    else:
                        text_key = hashlib.sha256((content["user_text"] + "\0"
                                                   + content["assistant_text"]).encode()).hexdigest().upper()
                        if text_key in all_seen:
                            record["screen_status"] = "EXACT_DUPLICATE"
                        else:
                            try:
                                reasoning = parsed["teacher_reasoning_content"]
                                reasoning_sha = hashlib.sha256(reasoning.encode()).hexdigest().upper() if reasoning else ""
                                canonical = wrap_turns(
                                    [{"user_text": content["user_text"],
                                      "assistant_text": content["assistant_text"]}],
                                    source_id=job["source_id"],
                                    source_sha256=source["source_sha256"],
                                    teacher_model_sha256=MODEL_SHA256,
                                    language=language, source_license=job["source_license"],
                                    generation_id=generation_id,
                                    correction_note=content["correction_note"],
                                    reasoning_ref=(f"{directory.relative_to(ROOT).as_posix()}/"
                                                   f"raw_shards_manifest.json#{generation_id}") if reasoning else "",
                                    reasoning_sha256=reasoning_sha,
                                    student_training_status="PILOT_TARGET_PENDING")
                                encoded = encode_records([canonical], tokenizer, SEQ, cfg.vocab_size)[0]
                            except ValueError as exc:
                                record["screen_status"] = f"WRAP_OR_TOKENIZE:{str(exc)[:180]}"
                            else:
                                record["screen_status"] = "PSEUDO_FORMAT_READY"
                                record["selected_for_pilot_microbatch"] = True
                                all_seen.add(text_key)
                                canonical_writer.append(canonical)
                                batch.append(encoded)
                                update_generation_ids.append(generation_id)
                                accepted_total += 1
                                processed_tokens += len(encoded[0])
                                supervised_tokens += encoded[2]
                                language_tokens[language] += len(encoded[0])
                    counts[record["screen_status"]] += 1
                    raw_writer.append(record)
                    if backend is not None:
                        print("[TEACHER_BACKEND_ERROR] " + json.dumps({
                            "generation_id": generation_id,
                            "classification": backend["classification"],
                            "http_status": backend.get("http_status"),
                            "body_sha256": backend.get("body_sha256", "")},
                            sort_keys=True), flush=True)
                        if backend["classification"] != "PEG_NATIVE_MISMATCH":
                            raise ToolFailure("unknown teacher backend/API failure; see versioned raw")
                t1 = time.monotonic()
                part = loss_sum(model, batch, pad_id, torch.device("cuda"), cfg.vocab_size, 2048)
                if not bool(torch.isfinite(part)):
                    raise GateNegative("nonfinite student assistant-only loss")
                part.backward()  # normalize accumulated gradients by the *actual* target count below
                torch.cuda.synchronize()
                student_wall += time.monotonic() - t1
            if supervised_tokens <= 0:
                raise GateNegative("zero student assistant target tokens")
            for parameter in model.parameters():
                if parameter.grad is not None:
                    parameter.grad.div_(supervised_tokens)
            grad = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            if not math.isfinite(float(grad)):
                raise GateNegative("nonfinite student gradient")
            t2 = time.monotonic()
            adamw.step()
            muon.step()
            torch.cuda.synchronize()
            student_wall += time.monotonic() - t2
            step = {"update": update_index, "teacher_request_wall_sec": round(teacher_wall, 3),
                    "student_compute_wall_sec": round(student_wall, 3),
                    "whole_update_wall_sec": round(time.monotonic() - update_started, 3),
                    "micro": MICRO, "accum": ACCUM, "fresh_accepted": MICRO * ACCUM,
                    "processed_nonpadding_conversation_tokens": processed_tokens,
                    "assistant_supervised_tokens": supervised_tokens,
                    "language_nonpadding_tokens": language_tokens,
                    "teacher_completion_tokens": completion_tokens,
                    "trained_generation_ids": update_generation_ids,
                    "grad_norm_before_clip": round(float(grad), 6),
                    "student_peak_reserved_mib": torch.cuda.max_memory_reserved() // 2**20,
                    "sampled_global_used_peak_mib": max(samples) if samples else None}
            updates.append(step)
            print("[ONLINE_UPDATE] " + json.dumps(step, ensure_ascii=False, sort_keys=True), flush=True)
        status, reason = ("ONE_UPDATE_COMPLETE" if target_updates == 1 else "FIVE_UPDATES_COMPLETE",
                          "throughput/resource pilot only")
    except GateNegative as exc:
        status, reason = "GATE_NEGATIVE_PARTIAL", str(exc)
        print(f"[GATE NEGATIVE] {reason}; completed optimizer updates={len(updates)}", flush=True)
    except ToolFailure as exc:
        status, reason = "TOOL_FAILURE_PARTIAL", str(exc)
        tool_failure = True
        print(f"[TOOL FAIL] {reason}; completed optimizer updates={len(updates)}", flush=True)
    finally:
        stop.set()
        _kill_group(server)
        if raw_writer is not None and canonical_writer is not None and not counts:
            with manifest_path.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps({"schema": "P106B_STAGE2IW_ONLINE_RATE5_V1",
                                         "status": status, "reason": reason,
                                         "effort": effort, "updates_completed": len(updates),
                                         "teacher_attempts": 0,
                                         "student_checkpoint_written": False,
                                         "quality": "NOT_RUN"}, ensure_ascii=False, indent=2) + "\n")
        if raw_writer is not None and canonical_writer is not None and counts:
            raw_manifest = raw_writer.close(lineage=source | {"effort": effort, "kind": "raw"})
            canonical_manifest = (canonical_writer.close(lineage=source | {"effort": effort,
                                                                                 "kind": "canonical"})
                                  if accepted_total else None)
            verify(directory, raw_manifest)
            if canonical_manifest is not None:
                verify(directory, canonical_manifest)
            report = {"schema": ("P106B_STAGE2IWD_ONLINE_RATE1_V1" if variant == "backend1"
                                  else "P106B_STAGE2IW_ONLINE_RATE5_V1"),
                      "status": status, "reason": reason, "effort": effort,
                      "variant": variant, "target_updates": target_updates,
                      "inputs": inputs, "teacher_assets": teacher_assets,
                      "teacher_model_sha256": MODEL_SHA256,
                      "student_parent_sha256": STUDENT_SHA256,
                      "student_parent_step": parent_step,
                      "teacher_ctx": context, "teacher_max_tokens": max_tokens,
                      "sampler": INSTRUCT_SAMPLER if effort == "none" else THINKING_SAMPLER,
                      "model_card": MODEL_CARD,
                      "model_card_effort_note": "model card says low is unsupported/near xhigh; local Stage2hW timing is empirical only",
                      "updates_completed": len(updates),
                      "updates": updates, "raw_counts": dict(counts),
                      "source_jobs_used": used, "raw_shards_manifest": "raw_shards_manifest.json",
                      "canonical_shards_manifest": "canonical_shards_manifest.json" if accepted_total else None,
                      "raw_concat_sha256": raw_manifest["concat_sha256"],
                      "canonical_concat_sha256": (canonical_manifest["concat_sha256"]
                                                  if canonical_manifest is not None else None),
                      "whole_wall_sec": round(time.monotonic() - started, 3),
                      "sampled_global_peak_mib": max(samples) if samples else None,
                      "sample_errors": sample_errors,
                      "server_error_tail": server_lines[-20:],
                      "gdn_ar_enabled": any("fused Gated Delta Net (autoregressive) enabled" in line for line in server_lines),
                      "gdn_chunked_enabled": any("fused Gated Delta Net (chunked) enabled" in line for line in server_lines),
                      "student_checkpoint_written": False,
                      "formal_train_ready": False, "quality": "NOT_RUN",
                      "limits": "OASST1 public-v3 short single-turn source subset, same concepts reused across ko/en; no held-out evaluation"}
            with manifest_path.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            print("[ONLINE_SUMMARY] " + json.dumps({k: report[k] for k in (
                "status", "reason", "effort", "updates_completed", "source_jobs_used",
                "raw_counts", "whole_wall_sec", "student_checkpoint_written", "quality")},
                ensure_ascii=False, sort_keys=True), flush=True)
    return 9 if tool_failure else 0 if status in {"ONE_UPDATE_COMPLETE", "FIVE_UPDATES_COMPLETE"} else 8


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    parser.add_argument("--effort", choices=sorted(EFFORT_CONFIG), default="low")
    parser.add_argument("--max-wall-sec", type=int, default=MAX_WALL_SEC)
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
        elif args.check_only:
            print(json.dumps(check_only(args.effort), ensure_ascii=False, sort_keys=True))
            print("[CHECK_ONLY] source/tokenizer/parent PASS; GPU/student updates NOT_RUN")
        else:
            if not 60 <= args.max_wall_sec <= MAX_WALL_SEC:
                raise ValueError("wall cap must be 60..21600 seconds")
            def time_limit(_signum, _frame):
                raise TimeoutError("online five-step hard wall exceeded")
            old = signal.signal(signal.SIGALRM, time_limit)
            signal.alarm(args.max_wall_sec + 180)
            try:
                return execute(args.effort, args.max_wall_sec)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old)
        return 0
    except PrerequisiteHold as exc:
        print(f"[HOLD] P106B Stage2iW {exc}; teacher/student GPU NOT_RUN")
        return 8
    except (OSError, ValueError, RuntimeError, TypeError, KeyError, TimeoutError) as exc:
        print(f"[FAIL] P106B Stage2iW {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
