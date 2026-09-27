#!/usr/bin/env python3
"""P106B Stage2fW: bounded bilingual/topic teacher extraction pilot.

Select exactly two fixed public-v3 jobs per (eight heuristic families x ko/en)
from a SHA-bound finite deck. Each request starts from its own system+source
messages; only an intentional next_turn job carries that source dialogue.
Format may be retried once, but a duplicate concept is not regenerated until
an arbitrary token budget is filled. All attempts, reasoning and final text
are in write-once ignored HF shards <=20MB; no student training occurs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
import unicodedata
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_p106b_job_deck import OUTPUT as JOB_DIR, OUTPUT_MANIFEST as JOB_MANIFEST, source_contract  # noqa: E402
from scripts.diag_p106_bonsai_assets import regular, sha256_file  # noqa: E402
from scripts.diag_p106_coload import _free_port, _http_json  # noqa: E402
from scripts.diag_p106_full_coload_accum import _compute_apps, _kill_group  # noqa: E402
from scripts.diag_p106_vram_sample import read_memory  # noqa: E402
from scripts.diag_p106_oasst2_teacher_ko_gate import MODEL, MODEL_SHA256, SERVER, asset_preflight  # noqa: E402
from scripts.diag_p106b_teacher_answer_repair import CTX, MAX_TOKENS, SAMPLER, THINKING_BUDGET  # noqa: E402
from scripts.diag_p106b_teacher_tagged_pair import MANIFEST as FORMAT_MANIFEST, OUTPUT as FORMAT_RAW  # noqa: E402
from scripts.diag_p106b_scale_preflight import TOKENIZER as LEGACY, TOKENIZER_SHA256 as LEGACY_SHA  # noqa: E402
from scripts.p106b_shards import ShardWriter, verify  # noqa: E402
from scripts.p106b_teacher_format import parse_reply, teacher_prompt  # noqa: E402
from scripts.p106b_teacher_wrapper import wrap_turns  # noqa: E402
from tinylm.data.sft import IGNORE, encode_conversation  # noqa: E402
from tinylm.data.sft import IGNORE, encode_conversation  # noqa: E402

OUTPUT_DIR = ROOT / "HF/sft_ready/p106b_bilingual_v1/teacher_pilot"
OUTPUT_MANIFEST = OUTPUT_DIR / "pilot_manifest.json"
FAMILIES = ("math_logic", "code", "format_following", "culture_art",
            "politics_society", "game_trpg_meme", "daily_dialogue",
            "general_knowledge_or_other")
LANGUAGES = ("ko", "en")
PER_GROUP = 2
MAX_ATTEMPTS = 2
WALL_LIMIT = 2400


class PrerequisiteHold(ValueError):
    """Missing prior user gate rather than source/tool failure."""


def select_jobs() -> tuple[list[dict], dict]:
    if not regular(JOB_MANIFEST):
        raise PrerequisiteHold("Stage2eW finite job deck not yet available")
    deck = json.loads(JOB_MANIFEST.read_text(encoding="utf-8"))
    if (deck.get("schema") != "P106B_STAGE2EW_JOB_DECK_V1"
            or deck.get("source") != source_contract()):
        raise ValueError("job deck/source lineage differs")
    if not regular(FORMAT_MANIFEST) or not regular(FORMAT_RAW):
        raise PrerequisiteHold("Stage2cW tagged-format paired evidence not yet available")
    fmt = json.loads(FORMAT_MANIFEST.read_text(encoding="utf-8"))
    if (fmt.get("schema") != "P106B_STAGE2CW_TAGGED_JSON_PAIR_V1"
            or fmt.get("raw_sha256") != sha256_file(FORMAT_RAW)
            or fmt.get("format_status", {}).get("tagged", {}).get("TAGGED_COMPLETE", 0) < 12
            or fmt.get("canonical_wrapper_ok", {}).get("tagged", 0) < 12):
        raise PrerequisiteHold("Stage2cW tagged format/canonical threshold not met")
    train_spec = deck.get("splits", {}).get("train", {})
    relative = train_spec.get("manifest")
    if not isinstance(relative, str) or relative != (JOB_DIR / "train_shards_manifest.json").relative_to(ROOT).as_posix():
        raise ValueError("train job shard manifest path differs")
    shard_manifest_path = ROOT / relative
    if not regular(shard_manifest_path):
        raise ValueError("train job shard manifest absent or linked")
    shards = json.loads(shard_manifest_path.read_text(encoding="utf-8"))
    verify(JOB_DIR, shards)
    if (shards.get("rows") != train_spec.get("rows")
            or shards.get("concat_sha256") != train_spec.get("concat_sha256")):
        raise ValueError("train job shard count/SHA differs")
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    seen = set()
    for spec in shards["shards"]:
        with (JOB_DIR / spec["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                job = json.loads(line)
                if job.get("schema") != "P106B_STAGE2EW_TEACHER_JOB_V1" or job.get("split") != "train":
                    raise ValueError("teacher job schema/split differs")
                if job["job_id"] in seen:
                    raise ValueError("duplicate job id")
                seen.add(job["job_id"])
                groups[(job["family_heuristic"], job["target_language"])].append(job)
    selected = []
    for family in FAMILIES:
        for language in LANGUAGES:
            candidates = sorted(groups[(family, language)], key=lambda row: row["job_id"])
            if len(candidates) < PER_GROUP:
                raise PrerequisiteHold(f"family/language seed deficit: {family}/{language}")
            selected.extend(candidates[:PER_GROUP])
    if len(selected) != len(FAMILIES) * len(LANGUAGES) * PER_GROUP:
        raise ValueError("pilot selection count differs")
    return selected, {"job_deck_sha256": sha256_file(JOB_MANIFEST),
                      "train_jobs_concat_sha256": shards["concat_sha256"],
                      "format_pair_raw_sha256": fmt["raw_sha256"],
                      "teacher_model_sha256": MODEL_SHA256,
                      "selected_job_ids": [job["job_id"] for job in selected]}


def normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def near_duplicate(left: str, right: str) -> bool:
    a, b = normalized(left), normalized(right)
    if a == b:
        return True
    if min(len(a), len(b)) < 30:
        return False
    sa = {a[index:index + 5] for index in range(len(a) - 4)}
    sb = {b[index:index + 5] for index in range(len(b) - 4)}
    return bool(sa and sb and len(sa & sb) / len(sa | sb) >= 0.85)


def self_test() -> None:
    assert len(FAMILIES) * len(LANGUAGES) * PER_GROUP == 32
    assert near_duplicate("같은 개념 질문은 무엇인가요?", "같은 개념 질문은 무엇인가요?")
    assert not near_duplicate("수학 문제의 답은 4입니다.", "영화의 줄거리를 설명해 주세요.")
    assert MAX_ATTEMPTS == 2 and WALL_LIMIT == 2400
    print("[PASS] finite 8-family x 2-language x 2-job selection and near-duplicate check; model/GPU NOT_RUN")


def execute(selected: list[dict], source: dict) -> int:
    from tokenizers import Tokenizer

    if OUTPUT_DIR.is_symlink() or OUTPUT_DIR.exists():
        raise FileExistsError("pilot output version already exists; use a new stage")
    if not regular(LEGACY) or sha256_file(LEGACY) != LEGACY_SHA:
        raise ValueError("legacy student tokenizer absent or changed")
    asset_preflight(hash_model=True)
    if _compute_apps():
        print("[HOLD] competing GPU compute app; teacher not started")
        return 8
    if read_memory()[1] < 8192:
        print("[HOLD] GPU free below 8192MiB; teacher not started")
        return 8
    tok = Tokenizer.from_file(str(LEGACY))
    port, key = _free_port(), os.urandom(24).hex()
    command = [str(SERVER), "--offline", "--model", str(MODEL),
               "--host", "127.0.0.1", "--port", str(port), "--api-key", key,
               "--no-webui", "--cors-origins", "localhost", "--no-cors-credentials",
               "--cache-ram", "0", "--verbosity", "4", "--ctx-size", str(CTX),
               "--batch-size", "64", "--ubatch-size", "64", "--threads", "8",
               "--no-warmup", "--fit", "off", "--no-op-offload", "--gpu-layers", "all",
               "--chat-template-kwargs", '{"reasoning_effort":"medium"}']
    server = None
    begin = time.monotonic()
    try:
        server = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, errors="replace", bufsize=1,
                                  start_new_session=True)
        def drain() -> None:
            assert server is not None and server.stdout is not None
            for _ in server.stdout:
                pass
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
            print("[GATE NEGATIVE] teacher-only free below 2048MiB")
            return 8
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        writer = ShardWriter(OUTPUT_DIR, "teacher_raw")
        status: Counter[str] = Counter()
        output_tokens: Counter[str] = Counter()
        student_tokens: Counter[str] = Counter()
        assistant_tokens: Counter[str] = Counter()
        family_yield: Counter[str] = Counter()
        request_wall = 0.0
        accepted_questions: dict[str, list[str]] = {language: [] for language in LANGUAGES}
        for index, job in enumerate(selected):
            if time.monotonic() - begin >= WALL_LIMIT:
                print("[GATE NEGATIVE] teacher pilot hard wall; partial raw shards preserved")
                return 8
            language, task = job["target_language"], job["task"]
            source_payload = {"concept_id": job["concept_id"],
                              "family_heuristic": job["family_heuristic"],
                              "source_turns": job["source_turns"]}
            last_error = ""
            for attempt in range(1, MAX_ATTEMPTS + 1):
                prompt = teacher_prompt(task, language, source_payload)
                if last_error:
                    prompt[0]["content"] += (
                        " Previous attempt failed the tagged wire format: " + last_error
                        + ". Return one fresh complete set of fields."
                    )
                seed = int(job["job_id"][:8], 16) + attempt
                payload = {"messages": prompt, **SAMPLER, "max_tokens": MAX_TOKENS,
                           "thinking_budget_tokens": THINKING_BUDGET, "seed": seed}
                started = time.monotonic()
                reply = _http_json(f"http://127.0.0.1:{port}/v1/chat/completions", key,
                                   payload, timeout=120)
                elapsed = round(time.monotonic() - started, 3)
                request_wall += elapsed
                row = parse_reply(reply, language=language, output_format="tagged")
                reason = ""
                candidate = row["parsed_content"]
                if candidate is None:
                    reason = row["format_status"] + ":" + row["parse_error"]
                else:
                    try:
                        turns = ([{"user_text": turn["user_text"],
                                   "assistant_text": turn["assistant_text"]}
                                  for turn in job["source_turns"]] if task == "next_turn" else [])
                        turns.append({"user_text": candidate["user_text"],
                                      "assistant_text": candidate["assistant_text"]})
                        canonical = wrap_turns(
                            turns, source_id=job["source_id"],
                            source_sha256=source["job_deck_sha256"],
                            teacher_model_sha256=MODEL_SHA256, language=language,
                            source_license=job["source_license"],
                            generation_id=f"stage2fw:{job['job_id']}",
                            correction_note=candidate["correction_note"])
                        ids, labels, _ = encode_conversation(canonical, tok, "chatml")
                        if len(ids) < 2 or len(ids) - 1 > 1024:
                            reason = "STUDENT_CONTEXT_OVER_1024"
                        elif sum(label != IGNORE for label in labels) <= 0:
                            reason = "ASSISTANT_MASK_EMPTY"
                        elif any(near_duplicate(candidate["user_text"], previous)
                                 for previous in accepted_questions[language]):
                            reason = "EXACT_OR_NEAR_DUPLICATE_QUESTION"
                        else:
                            accepted_questions[language].append(candidate["user_text"])
                            student_tokens[language] += len(ids)
                            assistant_tokens[language] += sum(label != IGNORE for label in labels)
                            family_yield[job["family_heuristic"]] += 1
                    except (ValueError, TypeError, KeyError) as exc:
                        reason = "CANONICAL_WRAP:" + str(exc)
                state = "CANDIDATE" if not reason else "REJECTED"
                usage = row["usage"]["completion_tokens"]
                if type(usage) is int and usage >= 0:
                    output_tokens[language] += usage
                else:
                    status["USAGE_MISSING"] += 1
                status[f"{language}:{state}"] += 1
                record = {"schema": "P106B_STAGE2FW_TEACHER_ATTEMPT_V1",
                          "job_id": job["job_id"], "case": index + 1, "attempt": attempt,
                          "task": task, "target_language": language,
                          "family_heuristic": job["family_heuristic"],
                          "source_id": job["source_id"],
                          "source_license": job["source_license"],
                          "concept_id": job["concept_id"],
                          "source_turns": job["source_turns"],
                          "prompt_sha256": hashlib.sha256(json.dumps(
                              prompt, ensure_ascii=False, sort_keys=True).encode()).hexdigest().upper(),
                          "request_wall_sec": elapsed, "teacher": row,
                          "screen_status": state, "screen_reason": reason,
                          "teacher_truth_status": "PSEUDO_UNVERIFIED",
                          "accepted_for_training": False}
                writer.append(record)
                print("[BILINGUAL_PILOT] " + json.dumps({
                    "case": index + 1, "language": language, "family": job["family_heuristic"],
                    "attempt": attempt, "format": row["format_status"],
                    "screen": state, "reason": reason, "completion_tokens": usage,
                    "request_wall_sec": elapsed}, sort_keys=True), flush=True)
                if state == "CANDIDATE" or candidate is not None:
                    break  # Only malformed wire format gets one retry.
                last_error = reason
        raw_manifest = writer.close(lineage=source)
        verify(OUTPUT_DIR, raw_manifest)
        total_student = sum(student_tokens.values())
        report = {"schema": "P106B_STAGE2FW_BILINGUAL_PILOT_V1",
                  "source": source, "teacher_model_sha256": MODEL_SHA256,
                  "job_count": len(selected), "attempts": raw_manifest["rows"],
                  "format_and_screen": dict(status),
                  "teacher_completion_tokens_by_language": dict(output_tokens),
                  "teacher_request_wall_sec": round(request_wall, 3),
                  "student_canonical_tokens_by_language": dict(student_tokens),
                  "assistant_supervised_tokens_by_language": dict(assistant_tokens),
                  "candidate_family_counts": dict(family_yield),
                  "student_ko_fraction": (round(student_tokens["ko"] / total_student, 4)
                                          if total_student else None),
                  "raw_shards_manifest": writer.manifest_path.relative_to(ROOT).as_posix(),
                  "raw_concat_sha256": raw_manifest["concat_sha256"],
                  "max_shard_bytes": 20_000_000,
                  "teacher_context_policy": "stateless independent request per job; only explicit next_turn source history",
                  "accepted_for_training": 0, "student_training": "NOT_RUN",
                  "quality": "NOT_RUN", "limit": "32 finite heuristic-topic jobs, not 300M/600M or a verified 50:50 corpus"}
        with OUTPUT_MANIFEST.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
        if min(status["ko:CANDIDATE"], status["en:CANDIDATE"]) < 12:
            print("[GATE NEGATIVE] fewer than twelve screened candidates per language")
            return 8
        print("[PASS] bounded teacher content production/format only; truth, 300M and student SFT NOT_RUN")
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
            return 0
        selected, source = select_jobs()
        if args.check_only:
            print(json.dumps({"jobs": len(selected), "source": source,
                              "new_output": OUTPUT_DIR.relative_to(ROOT).as_posix(),
                              "teacher_model_gpu": "NOT_RUN", "student_training": "NOT_RUN"},
                             sort_keys=True))
            print("[CHECK_ONLY] finite deck/format source PASS; model/GPU NOT_RUN")
            return 0
        def time_limit(_signum, _frame):
            raise TimeoutError("P106B bilingual pilot hard wall exceeded; partial raw shards preserved")
        old = signal.signal(signal.SIGALRM, time_limit)
        signal.alarm(WALL_LIMIT + 120)
        try:
            return execute(selected, source)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
    except PrerequisiteHold as exc:
        print(f"[HOLD] P106B Stage2fW {exc}", file=sys.stderr)
        return 8
    except (OSError, ValueError, RuntimeError, TimeoutError, TypeError, KeyError) as exc:
        print(f"[FAIL] P106B Stage2fW {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
