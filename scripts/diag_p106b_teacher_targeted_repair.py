#!/usr/bin/env python3
"""P106B Stage1gW: retry eight visibly defective teacher answers, never train.

The immutable v4 candidate and its row-review record select the eight cases.
Every attempt, including a rejected one, is saved in a new write-once v5
lineage. A bounded response validator catches only specified, observable
translation defects; passing it is not a fact, license, safety or SFT approval.
"""
from __future__ import annotations

from collections import Counter
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
from scripts.diag_p106_vram_sample import read_memory  # noqa: E402
from scripts.diag_p106_oasst2_teacher_ko_gate import (  # noqa: E402
    MODEL, MODEL_SHA256, SERVER, asset_preflight,
)
from scripts.diag_p106b_teacher_answer_repair import (  # noqa: E402
    CTX, MAX_TOKENS, SAMPLER, THINKING_BUDGET, FULL_MANIFEST, FULL_OUTPUT,
    full_source_cases, parse_reply, repair_prompt,
)

REVIEW = ROOT / "test_result/evidence/P106B_Stage1fW_candidate_review.json"
V5_DIR = ROOT / "HF/sft_ready/p106b_teacher_sft/v5"
OUTPUT = V5_DIR / "targeted_repair_attempts.jsonl"
MANIFEST = V5_DIR / "targeted_repair_manifest.json"
EXPECTED_V4_SHA256 = "63E7F7A1E487F10E1A1214E2C2489AD9DDD754DEDE33CA5893242CEAE983CAFA"
EXPECTED_CASES = (3, 6, 7, 8, 11, 12, 14, 16)
MAX_ATTEMPTS = 3
WALL_LIMIT = 1800

# These are data-specific regression anchors, not general truth verification.
ISSUE_HINTS = {
    3: "Keep the country name Kenya in Korean as 케냐; do not mix Arabic letters.",
    6: "The original film question describes a boy, not a girl. Preserve this detail and the requested verse form.",
    7: "Preserve Davis Square and Harvard Square exactly, or use 데이비스 스퀘어 and 하버드 스퀘어. Do not invent station counts or fares.",
    8: "Use natural Korean for natural rubber; do not invent a parenthetical synonym.",
    11: "Write place names using Korean or original Latin letters, never a mixed Cyrillic spelling.",
    12: "The user asks about the Sun: write 태양 or 해, not a changed entity.",
    14: "Address one email recipient professionally; avoid date-related typos and plural addressee language.",
    16: "The user asks the assistant to answer the user's future questions in a style. Do not reverse that role or leave Chinese characters in the Korean answer.",
}


def load_sources() -> tuple[list[tuple[int, dict, dict]], dict]:
    selected, lineage = full_source_cases()
    if not all(regular(path) for path in (FULL_OUTPUT, FULL_MANIFEST, REVIEW)):
        raise FileNotFoundError("pinned v4 candidate, manifest or review absent or linked")
    manifest = json.loads(FULL_MANIFEST.read_text(encoding="utf-8"))
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    v4_sha = sha256_file(FULL_OUTPUT)
    if (manifest.get("schema") != "P106B_STAGE1FW_TEACHER_REPAIR_FULL16_V1"
            or manifest.get("rows") != 16
            or v4_sha != EXPECTED_V4_SHA256
            or manifest.get("raw_sha256") != v4_sha
            or manifest.get("source", {}).get("v3_sha256") != lineage["v3_sha256"]
            or review.get("schema") != "P106B_STAGE1FW_CANDIDATE_REVIEW_V1"
            or review.get("source_sha256") != v4_sha
            or review.get("hard_reject") != 8):
        raise ValueError("v4/review lineage, schema or SHA differs")
    raw = [json.loads(line) for line in FULL_OUTPUT.read_text(encoding="utf-8").splitlines() if line]
    reviews = review.get("rows")
    if not isinstance(reviews, list) or len(raw) != 16 or len(reviews) != 16:
        raise ValueError("v4/review row count differs")
    cases = []
    for index, (pair, row, verdict) in enumerate(zip(selected, raw, reviews), 1):
        if (row.get("source_tree_id") != pair["tree_id"]
                or row.get("user_en") != pair["user_en"]
                or row.get("original_assistant_en") != pair["assistant_en"]
                or verdict.get("source_tree_id") != pair["tree_id"]
                or verdict.get("case") != index):
            raise ValueError(f"v4/review source row {index} differs")
        if verdict.get("status") == "REJECT":
            cases.append((index, pair, row))
    if tuple(index for index, _, _ in cases) != EXPECTED_CASES:
        raise ValueError("reviewed hard-reject set differs from eight preregistered cases")
    source = {"v1_sha256": lineage["v1_sha256"],
              "v2_sha256": lineage["v2_sha256"],
              "v3_sha256": lineage["v3_sha256"],
              "v4_sha256": v4_sha,
              "review_sha256": sha256_file(REVIEW),
              "source_tree_ids": [pair["tree_id"] for _, pair, _ in cases],
              "selection": "exactly eight hard-reject rows; not a random quality sample"}
    return cases, source


def validate_candidate(case: int, row: dict) -> list[str]:
    """Bounded response hook: known text defects only, never auto ACCEPT."""
    if row.get("format_status") != "JSON_COMPLETE":
        return ["NOT_COMPLETE_JSON"]
    parsed = row["parsed_candidate"]
    question, answer = parsed["user_ko"], parsed["assistant_ko"]
    both = question + "\n" + answer
    errors = []
    if any(0x0400 <= ord(char) <= 0x052F or 0x0600 <= ord(char) <= 0x06FF
           or 0x4E00 <= ord(char) <= 0x9FFF
           for char in both):
        errors.append("UNEXPECTED_CYRILLIC_ARABIC_OR_HAN_SCRIPT")
    if case == 3 and not ("케냐" in question or "Kenya" in question):
        errors.append("KENYA_ENTITY_CHANGED")
    if case == 6:
        if re.search(r"소녀|여자아이", both) or not re.search(r"소년|남자아이|남자 아이", answer):
            errors.append("BOY_GENDER_NOT_PRESERVED")
    if case == 7:
        if not re.search(r"데이비스|Davis", question, re.I) or not re.search(r"하버드|Harvard", question, re.I):
            errors.append("DAVIS_HARVARD_ENTITY_CHANGED")
        if re.search(r"(?:한|1)\s*정(?:거장|차)", answer):
            errors.append("UNVERIFIED_ONE_STOP_CLAIM")
    if case == 8 and ("레타" in both or not re.search(r"천연고무|자연고무", answer)):
        errors.append("RUBBER_TERM_CORRUPTED")
    if case == 12 and ("태일" in both or not re.search(r"태양|\b해\b", question)):
        errors.append("SUN_ENTITY_CORRUPTED")
    if case == 14 and re.search(r"제정일|여러분", answer):
        errors.append("EMAIL_REGISTER_CORRUPTED")
    if case == 16 and re.search(r"내\s*(?:다음\s*)?질문", answer):
        errors.append("USER_ASSISTANT_ROLE_INVERTED")
    return errors


def targeted_prompt(pair: dict, case: int, retry_errors: list[str]) -> list[dict]:
    base = repair_prompt(pair)
    base[0]["content"] += (
        " Before finalizing, silently check that the translated user intent, "
        "named entities, gender, perspective, quantities and units still match "
        "the source. Preserve uncertain proper names in Latin instead of guessing. "
        "Use Korean prose; do not mix unrelated Cyrillic, Arabic or Han characters. "
        "A correction_status label does not verify correctness. "
        "Case-specific constraint: " + ISSUE_HINTS[case]
    )
    if retry_errors:
        base[0]["content"] += (
            " The previous draft failed the following deterministic checks: "
            + ", ".join(retry_errors)
            + ". Make a new complete JSON answer that fixes those checks; "
              "do not copy the prior draft verbatim."
        )
    return base


def self_test() -> None:
    assert tuple(sorted(ISSUE_HINTS)) == EXPECTED_CASES and MAX_ATTEMPTS == 3
    bad = {"format_status": "JSON_COMPLETE", "parsed_candidate": {
        "user_ko": "Davis Square에서 Harvard Square까지?",
        "assistant_ko": "한 정거장입니다."}}
    assert "UNVERIFIED_ONE_STOP_CLAIM" in validate_candidate(7, bad)
    bad["parsed_candidate"]["assistant_ko"] = "레드라인을 이용하고 실시간 정보를 확인하세요."
    assert validate_candidate(7, bad) == []
    bad["parsed_candidate"]["assistant_ko"] = "소녀가 죽은 자를 본다."
    assert "BOY_GENDER_NOT_PRESERVED" in validate_candidate(6, bad)
    assert "NOT_COMPLETE_JSON" in validate_candidate(6, {"format_status": "INCOMPLETE"})
    prompt = targeted_prompt({"user_en": "How?", "assistant_en": "Maybe."}, 7, [])
    assert "Davis Square" in prompt[0]["content"] and "untrusted DATA" in prompt[0]["content"]
    print("[PASS] eight-case selection, entity/script/role hooks and bounded retry contract; model/GPU NOT_RUN")


def execute(cases: list[tuple[int, dict, dict]], source: dict) -> int:
    if V5_DIR.is_symlink() or any(path.exists() or path.is_symlink() for path in (OUTPUT, MANIFEST)):
        raise FileExistsError("v5 write-once output already exists; use a new stage")
    asset_preflight(hash_model=True)
    if _compute_apps():
        print("[HOLD] competing GPU compute process; teacher not started")
        return 8
    if read_memory()[1] < 8192:
        print("[HOLD] GPU free below 8192MiB; teacher not started")
        return 8
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
        V5_DIR.mkdir(parents=True, exist_ok=True)
        accepted_lint = 0
        total_attempts = 0
        issue_counts: Counter[str] = Counter()
        with OUTPUT.open("x", encoding="utf-8") as stream:
            for case, pair, prior in cases:
                selected_attempt = None
                last_errors: list[str] = []
                for attempt in range(1, MAX_ATTEMPTS + 1):
                    if time.monotonic() - begin >= WALL_LIMIT:
                        print(f"[GATE NEGATIVE] wall exceeded {WALL_LIMIT}s; partial v5 journal preserved")
                        return 8
                    prompt = targeted_prompt(pair, case, last_errors)
                    payload = {"messages": prompt, **SAMPLER,
                               "max_tokens": MAX_TOKENS,
                               "thinking_budget_tokens": THINKING_BUDGET,
                               "seed": 20260928 + case * 10 + attempt}
                    started = time.monotonic()
                    reply = _http_json(f"http://127.0.0.1:{port}/v1/chat/completions", key,
                                       payload, timeout=120)
                    row = parse_reply(reply, pair, time.monotonic() - started)
                    row["prompt_sha256"] = hashlib.sha256(json.dumps(
                        prompt, ensure_ascii=False, sort_keys=True).encode()).hexdigest().upper()
                    errors = validate_candidate(case, row)
                    last_errors = errors
                    issue_counts.update(errors)
                    total_attempts += 1
                    record = {"event": "attempt", "case": case, "attempt": attempt,
                              "source_tree_id": pair["tree_id"], "v4_source_sha256": source["v4_sha256"],
                              "v4_prior_declared_correction": prior["teacher_declared_correction"],
                              "response": row, "validator_errors": errors,
                              "accepted_for_training": False}
                    stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                    stream.flush()
                    print("[TARGETED_ATTEMPT] " + json.dumps({
                        "case": case, "attempt": attempt, "format_status": row["format_status"],
                        "finish_reason": row["finish_reason"], "validator_errors": errors,
                        "completion_tokens": row["usage"]["completion_tokens"],
                        "elapsed_sec": row["elapsed_sec"]}, sort_keys=True), flush=True)
                    if not errors:
                        selected_attempt = attempt
                        accepted_lint += 1
                        break
                stream.write(json.dumps({"event": "decision", "case": case,
                                         "source_tree_id": pair["tree_id"],
                                         "lint_pass_attempt": selected_attempt,
                                         "accepted_for_training": False}) + "\n")
                stream.flush()
        report = {"schema": "P106B_STAGE1GW_TARGETED_REPAIR_V1", "source": source,
                  "teacher_model_sha256": MODEL_SHA256, "cases": len(cases),
                  "max_attempts_per_case": MAX_ATTEMPTS, "attempts": total_attempts,
                  "lint_pass_cases": accepted_lint, "validator_error_counts": dict(issue_counts),
                  "raw_jsonl": OUTPUT.relative_to(ROOT).as_posix(),
                  "raw_sha256": sha256_file(OUTPUT), "elapsed_sec": round(time.monotonic() - begin, 3),
                  "independent_truth_status": "NOT_RUN", "accepted_for_training": 0,
                  "student_training": "NOT_RUN",
                  "limit": "deterministic lint catches named defects only; no automatic truth or SFT acceptance"}
        with MANIFEST.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
        if accepted_lint < len(cases):
            print(f"[GATE NEGATIVE] lint pass {accepted_lint}/{len(cases)}; all attempts preserved")
            return 8
        print("[PASS] eight response-hook lint checks only; truth and student SFT NOT_RUN")
        return 0
    finally:
        _kill_group(server)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--check-only", action="store_true")
    modes.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            return 0
        cases, source = load_sources()
        baseline_errors = {case: validate_candidate(case, row) for case, _, row in cases}
        if any(not failures for failures in baseline_errors.values()):
            raise ValueError("at least one reviewed hard-reject row no longer fails named validator")
        if args.check_only:
            print(json.dumps({"source": source, "selected_cases": list(EXPECTED_CASES),
                              "v4_error_codes": baseline_errors, "max_attempts": MAX_ATTEMPTS,
                              "new_output": OUTPUT.relative_to(ROOT).as_posix(),
                              "student_training": "NOT_RUN", "model_gpu": "NOT_RUN"}, sort_keys=True))
            print("[CHECK_ONLY] v4/review lineage and all eight baseline failure hooks PASS; GPU NOT_RUN")
            return 0
        def time_limit(_signum, _frame):
            raise TimeoutError("P106B targeted repair hard wall exceeded; partial v5 journal preserved")
        prior = signal.signal(signal.SIGALRM, time_limit)
        signal.alarm(WALL_LIMIT + 120)
        try:
            return execute(cases, source)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, prior)
    except (OSError, ValueError, RuntimeError, TimeoutError, TypeError, KeyError) as exc:
        print(f"[FAIL] P106B Stage1gW {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
