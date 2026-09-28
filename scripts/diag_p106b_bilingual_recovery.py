#!/usr/bin/env python3
"""P106B Stage2fWb: resume seven missing jobs from immutable v8 partial raw.

Known PEG-native HTTP 500 is a rejected teacher attempt, not a usable answer.
At most one fresh-seed retry is allowed per job. Other HTTP failures are tool
failures and stop with a versioned partial manifest. Previous 29 attempts are
SHA-pinned and REUSED BY REFERENCE, never copied or rewritten.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.diag_p106_bonsai_assets import regular, sha256_file  # noqa: E402
from scripts.diag_p106_coload import _free_port, _http_json  # noqa: E402
from scripts.diag_p106_full_coload_accum import _compute_apps, _kill_group  # noqa: E402
from scripts.diag_p106_oasst2_teacher_ko_gate import MODEL, MODEL_SHA256, SERVER, asset_preflight  # noqa: E402
from scripts.diag_p106_vram_sample import read_memory  # noqa: E402
from scripts.diag_p106b_bilingual_pilot import (  # noqa: E402
    select_jobs, near_duplicate, LEGACY, LEGACY_SHA, CTX, MAX_TOKENS,
    SAMPLER, THINKING_BUDGET, FAMILIES, LANGUAGES,
)
from scripts.diag_p106b_online_rate5 import PUBLIC_V3_MANIFEST  # noqa: E402
from scripts.diag_p106b_http500_isolation import _token_budget  # noqa: E402
from scripts.p106b_http_errors import capture_http_error as _safe_error  # noqa: E402
from scripts.p106b_shards import ShardWriter, verify  # noqa: E402
from scripts.p106b_teacher_format import parse_reply, teacher_prompt  # noqa: E402
from scripts.p106b_teacher_wrapper import wrap_turns  # noqa: E402
from tinylm.data.sft import IGNORE, encode_conversation  # noqa: E402

OLD_RAW = ROOT / "HF/sft_ready/p106b_bilingual_v1/teacher_pilot/teacher_raw_000000.jsonl"
OLD_SHA = "2D395CD2155D04934F13240430B4D566BA621B6871775BCCB4083D8202E7347E"
OUTPUT_DIR = ROOT / "HF/sft_ready/p106b_bilingual_v2/teacher_recovery"
REPORT = OUTPUT_DIR / "recovery_manifest.json"
MAX_ATTEMPTS = 2
WALL_LIMIT = 1800


def _candidate_tokens(job: dict, candidate: dict, source: dict, tok, prior_questions: list[str]) -> tuple[int, int]:
    language, task = job["target_language"], job["task"]
    turns = ([{"user_text": turn["user_text"], "assistant_text": turn["assistant_text"]}
              for turn in job["source_turns"]] if task == "next_turn" else [])
    turns.append({"user_text": candidate["user_text"],
                  "assistant_text": candidate["assistant_text"]})
    canonical = wrap_turns(turns, source_id=job["source_id"],
                           source_sha256=source["job_deck_sha256"],
                           teacher_model_sha256=MODEL_SHA256, language=language,
                           source_license=job["source_license"],
                           generation_id=f"stage2fwb:{job['job_id']}",
                           correction_note=candidate["correction_note"])
    ids, labels, _ = encode_conversation(canonical, tok, "chatml")
    if not 2 <= len(ids) <= 1025:
        raise ValueError("STUDENT_CONTEXT_OVER_1024")
    targets = sum(label != IGNORE for label in labels)
    if targets <= 0:
        raise ValueError("ASSISTANT_MASK_EMPTY")
    if any(near_duplicate(candidate["user_text"], old) for old in prior_questions):
        raise ValueError("EXACT_OR_NEAR_DUPLICATE_QUESTION")
    return len(ids), targets


def old_partial(selected: list[dict], source: dict, tok) -> tuple[dict, dict[str, list[str]]]:
    if not regular(OLD_RAW) or sha256_file(OLD_RAW) != OLD_SHA:
        raise ValueError("immutable Stage2f partial raw SHA differs")
    raw = [json.loads(line) for line in OLD_RAW.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(raw) != 29 or {row.get("case") for row in raw} != set(range(1, 26)):
        raise ValueError("Stage2f partial attempt/case coverage differs")
    accepted: dict[str, list[str]] = {language: [] for language in LANGUAGES}
    counts: Counter[str] = Counter()
    teacher_tokens: Counter[str] = Counter()
    student_tokens: Counter[str] = Counter()
    assistant_tokens: Counter[str] = Counter()
    family_yield: Counter[str] = Counter()
    request_wall = 0.0
    for row in raw:
        job = selected[row["case"] - 1]
        if (row.get("schema") != "P106B_STAGE2FW_TEACHER_ATTEMPT_V1"
                or row.get("job_id") != job["job_id"]
                or row.get("target_language") != job["target_language"]
                or row.get("source_id") != job["source_id"]):
            raise ValueError("old partial job lineage differs")
        language = job["target_language"]
        counts[f"{language}:{row['screen_status']}"] += 1
        request_wall += float(row["request_wall_sec"])
        usage = row["teacher"]["usage"].get("completion_tokens")
        if type(usage) is int and usage >= 0:
            teacher_tokens[language] += usage
        else:
            counts["USAGE_MISSING"] += 1
        if row["screen_status"] == "CANDIDATE":
            candidate = row["teacher"].get("parsed_content")
            if not isinstance(candidate, dict):
                raise ValueError("old candidate lacks parsed content")
            tokens, targets = _candidate_tokens(job, candidate, source, tok, accepted[language])
            accepted[language].append(candidate["user_text"])
            student_tokens[language] += tokens
            assistant_tokens[language] += targets
            family_yield[job["family_heuristic"]] += 1
    state = {"old_attempts": len(raw), "counts": counts, "teacher_tokens": teacher_tokens,
             "student_tokens": student_tokens, "assistant_tokens": assistant_tokens,
             "family_yield": family_yield, "old_request_wall_sec": round(request_wall, 3)}
    if counts["ko:CANDIDATE"] != 12 or counts["en:CANDIDATE"] != 11:
        raise ValueError("old partial candidate count differs")
    return state, accepted


def self_test() -> None:
    assert MAX_ATTEMPTS == 2 and WALL_LIMIT == 1800
    assert len(FAMILIES) == 8 and LANGUAGES == ("ko", "en")
    print("[PASS] reference old partial, bounded PEG rejection/retry, new write-once shards; GPU NOT_RUN")


def prepare():
    from tokenizers import Tokenizer

    selected, source = select_jobs()
    if PUBLIC_V3_MANIFEST.is_symlink() or not PUBLIC_V3_MANIFEST.is_file():
        raise ValueError("public v3 manifest unavailable or linked")
    public = json.loads(PUBLIC_V3_MANIFEST.read_text(encoding="utf-8"))
    if public.get("sources", {}).get("oasst", {}).get("repo") != "OpenAssistant/oasst1":
        raise ValueError("public v3 oasst source is not pinned OASST1")
    source["public_v3_manifest_sha256"] = sha256_file(PUBLIC_V3_MANIFEST)
    source["source_repos"] = {key: {"repo": value["repo"], "revision": value["revision"]}
                              for key, value in public["sources"].items()}
    if not regular(LEGACY) or sha256_file(LEGACY) != LEGACY_SHA:
        raise ValueError("legacy student tokenizer missing/changed")
    tok = Tokenizer.from_file(str(LEGACY))
    state, accepted = old_partial(selected, source, tok)
    if OUTPUT_DIR.exists() or OUTPUT_DIR.is_symlink():
        raise FileExistsError("Stage2fWb output version exists; never overwrite")
    return selected, source, tok, state, accepted


def execute(selected: list[dict], source: dict, tok, state: dict,
            accepted: dict[str, list[str]]) -> int:
    if _compute_apps():
        print("[HOLD] competing GPU compute app; teacher not started")
        return 8
    if read_memory()[1] < 8192:
        print("[HOLD] GPU free below 8192MiB; teacher not started")
        return 8
    assets = asset_preflight(hash_model=True)
    port, key = _free_port(), os.urandom(24).hex()
    command = [str(SERVER), "--offline", "--model", str(MODEL),
               "--host", "127.0.0.1", "--port", str(port), "--api-key", key,
               "--no-webui", "--cors-origins", "localhost", "--no-cors-credentials",
               "--cache-ram", "0", "--verbosity", "4", "--ctx-size", str(CTX),
               "--batch-size", "64", "--ubatch-size", "64", "--threads", "8",
               "--no-warmup", "--fit", "off", "--no-op-offload", "--gpu-layers", "all",
               "--chat-template-kwargs", '{"reasoning_effort":"medium"}']
    server = None
    server_tail: deque[str] = deque(maxlen=24)
    started = time.monotonic()
    tool_error = ""
    writer = None
    try:
        server = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, errors="replace", bufsize=1,
                                  start_new_session=True)

        def drain() -> None:
            assert server is not None and server.stdout is not None
            for line in server.stdout:
                if re.search(r"error|fail|peg-native|exception", line, re.I):
                    server_tail.append(line.replace(key, "<redacted-api-key>").strip()[:500])

        threading.Thread(target=drain, daemon=True).start()
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
            print("[HOLD] teacher-only free below 2048MiB")
            return 8
        OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
        writer = ShardWriter(OUTPUT_DIR, "recovery_raw")
        new_wall = 0.0
        for index in range(25, 32):
            job = selected[index]
            language = job["target_language"]
            last_error = ""
            for attempt in range(1, MAX_ATTEMPTS + 1):
                if time.monotonic() - started >= WALL_LIMIT - 140:
                    tool_error = "WALL_BUDGET_BEFORE_PANEL_COMPLETE"
                    break
                source_payload = {"concept_id": job["concept_id"],
                                  "family_heuristic": job["family_heuristic"],
                                  "source_turns": job["source_turns"]}
                prompt = teacher_prompt(job["task"], language, source_payload)
                if last_error:
                    prompt[0]["content"] += (
                        " Previous attempt had a malformed answer envelope or native parser error. "
                        "Write exactly one complete set of the requested fields."
                    )
                seed = int(job["job_id"][:8], 16) + attempt
                payload = {"messages": prompt, **SAMPLER, "max_tokens": MAX_TOKENS,
                           "thinking_budget_tokens": THINKING_BUDGET, "seed": seed}
                budget = _token_budget(port, key, payload, CTX, MAX_TOKENS)
                t0 = time.monotonic()
                parsed = None
                backend = None
                try:
                    reply = _http_json(f"http://127.0.0.1:{port}/v1/chat/completions",
                                       key, payload, timeout=130)
                    parsed = parse_reply(reply, language=language)
                except HTTPError as exc:
                    backend = _safe_error(exc, key)
                except (OSError, URLError, TimeoutError) as exc:
                    backend = {"http_status": None, "error_type": type(exc).__name__,
                               "message": str(exc)[:400]}
                elapsed = round(time.monotonic() - t0, 3)
                new_wall += elapsed
                state["counts"][f"{language}:REQUEST"] += 1
                reason = ""
                candidate = parsed.get("parsed_content") if parsed else None
                if backend is not None:
                    message = backend.get("message", "")
                    reason = ("PEG_NATIVE_MISMATCH"
                              if backend.get("classification") == "PEG_NATIVE_MISMATCH"
                              else "BACKEND_ERROR")
                    if reason == "BACKEND_ERROR":
                        tool_error = f"HTTP/transport error case{index+1}: {backend.get('http_status')}"
                elif candidate is None:
                    reason = str(parsed["format_status"]) + ":" + str(parsed["parse_error"])
                else:
                    try:
                        tokens, targets = _candidate_tokens(job, candidate, source, tok,
                                                            accepted[language])
                    except (ValueError, TypeError, KeyError) as exc:
                        reason = "CANONICAL_SCREEN:" + str(exc)[:180]
                    else:
                        accepted[language].append(candidate["user_text"])
                        state["student_tokens"][language] += tokens
                        state["assistant_tokens"][language] += targets
                        state["family_yield"][job["family_heuristic"]] += 1
                screen = "CANDIDATE" if not reason else "REJECTED"
                state["counts"][f"{language}:{screen}"] += 1
                if reason == "PEG_NATIVE_MISMATCH":
                    state["counts"]["PEG_NATIVE_MISMATCH"] += 1
                usage = parsed["usage"].get("completion_tokens") if parsed else None
                if type(usage) is int and usage >= 0:
                    state["teacher_tokens"][language] += usage
                elif backend is None:
                    state["counts"]["USAGE_MISSING"] += 1
                record = {"schema": "P106B_STAGE2FWB_RECOVERY_ATTEMPT_V1",
                          "case": index + 1, "attempt": attempt, "job_id": job["job_id"],
                          "source_id": job["source_id"], "language": language,
                          "family": job["family_heuristic"], "prompt_sha256": hashlib.sha256(
                              json.dumps(prompt, ensure_ascii=False, sort_keys=True).encode()).hexdigest().upper(),
                          "token_budget": budget, "request_wall_sec": elapsed,
                          "teacher": parsed, "backend_error": backend,
                          "screen_status": screen, "screen_reason": reason,
                          "server_diagnostic_tail": list(server_tail),
                          "accepted_for_training": False}
                writer.append(record)
                print("[BILINGUAL_RECOVERY] " + json.dumps({
                    "case": index + 1, "attempt": attempt, "language": language,
                    "http_status": backend.get("http_status") if backend else 200,
                    "format": parsed.get("format_status") if parsed else "HTTP_ERROR",
                    "screen": screen, "reason": reason,
                    "input_tokens": budget.get("input_tokens"),
                    "request_wall_sec": elapsed}, sort_keys=True), flush=True)
                if tool_error or screen == "CANDIDATE" or candidate is not None:
                    break
                last_error = reason
            if tool_error:
                break
        raw_manifest = writer.close(lineage=source | {
            "old_partial_sha256": OLD_SHA, "new_stage": "Stage2fWb"})
        verify(OUTPUT_DIR, raw_manifest)
        total_student = sum(state["student_tokens"].values())
        report = {"schema": "P106B_STAGE2FWB_BILINGUAL_RECOVERY_V1",
                  "source": source, "teacher_assets": assets,
                  "old_partial_raw": OLD_RAW.relative_to(ROOT).as_posix(),
                  "old_partial_sha256": OLD_SHA, "old_attempts": state["old_attempts"],
                  "new_attempts": raw_manifest["rows"],
                  "new_raw_manifest": writer.manifest_path.relative_to(ROOT).as_posix(),
                  "new_raw_concat_sha256": raw_manifest["concat_sha256"],
                  "combined_format_and_screen": dict(state["counts"]),
                  "teacher_completion_tokens_by_language": dict(state["teacher_tokens"]),
                  "old_request_wall_sec": state["old_request_wall_sec"],
                  "new_request_wall_sec": round(new_wall, 3),
                  "student_canonical_tokens_by_language": dict(state["student_tokens"]),
                  "assistant_supervised_tokens_by_language": dict(state["assistant_tokens"]),
                  "candidate_family_counts": dict(state["family_yield"]),
                  "student_ko_fraction": round(state["student_tokens"]["ko"] / total_student, 4)
                  if total_student else None,
                  "tool_error": tool_error,
                  "accepted_for_training": 0, "student_training": "NOT_RUN",
                  "quality": "NOT_RUN",
                  "limit": "old 29 attempts referenced by SHA plus only cases26-32 newly generated; format/length screen, not truth or 300M corpus"}
        with REPORT.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print("[BILINGUAL_RECOVERY_SUMMARY] " + json.dumps({
            "old_attempts": report["old_attempts"], "new_attempts": report["new_attempts"],
            "combined_format_and_screen": report["combined_format_and_screen"],
            "student_canonical_tokens_by_language": report["student_canonical_tokens_by_language"],
            "tool_error": tool_error, "student_training": "NOT_RUN"},
            ensure_ascii=False, sort_keys=True), flush=True)
        if tool_error:
            return 9
        if min(state["counts"]["ko:CANDIDATE"], state["counts"]["en:CANDIDATE"]) < 12:
            print("[GATE NEGATIVE] fewer than twelve screened candidates per language")
            return 8
        print("[PASS] 32-job panel completed by immutable-partial reference; educational truth NOT_RUN")
        return 0
    finally:
        _kill_group(server)


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
        else:
            selected, source, tok, state, accepted = prepare()
            if args.check_only:
                print(json.dumps({"old_partial_sha256": OLD_SHA,
                                  "old_attempts": state["old_attempts"],
                                  "old_candidate_counts": {lang: state["counts"][f"{lang}:CANDIDATE"]
                                                           for lang in LANGUAGES},
                                  "remaining_cases": list(range(26, 33)),
                                  "new_output": OUTPUT_DIR.relative_to(ROOT).as_posix(),
                                  "model_gpu": "NOT_RUN", "student_training": "NOT_RUN"},
                                 sort_keys=True))
                print("[CHECK_ONLY] immutable old partial and remaining seven jobs PASS; GPU NOT_RUN")
            else:
                def time_limit(_signum, _frame):
                    raise TimeoutError("P106B Stage2fWb 1800s hard wall")
                old = signal.signal(signal.SIGALRM, time_limit)
                signal.alarm(WALL_LIMIT)
                try:
                    return execute(selected, source, tok, state, accepted)
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old)
        return 0
    except (OSError, ValueError, RuntimeError, TimeoutError, TypeError, KeyError) as exc:
        print(f"[FAIL] P106B Stage2fWb {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
