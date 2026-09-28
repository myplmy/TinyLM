#!/usr/bin/env python3
"""P106B Stage2jW: four-request, teacher-only HTTP 500 isolation gate.

This deliberately does not replay the long 25/34-request sessions or load the
student. It asks each fresh server the last recorded predecessor and the first
failed input, preserving the HTTP error body, prompt-token budget, GPU samples
and a bounded server-error tail in a NEW ignored HF version. Old v8/v10 are
SHA-pinned and never changed. A clean run does not prove the long-session bug
fixed; a reproduced 500 is a backend/tool failure, not a scientific negative.
"""
from __future__ import annotations

import argparse
from collections import deque
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
from scripts.diag_p106_bonsai_assets import sha256_file  # noqa: E402
from scripts.diag_p106_coload import _free_port, _http_json  # noqa: E402
from scripts.diag_p106_full_coload_accum import _compute_apps, _kill_group  # noqa: E402
from scripts.diag_p106_oasst2_teacher_ko_gate import MODEL, SERVER, asset_preflight  # noqa: E402
from scripts.diag_p106_vram_sample import read_memory  # noqa: E402
from scripts.diag_p106b_bilingual_pilot import select_jobs  # noqa: E402
from scripts.diag_p106b_online_rate5 import source_jobs, THINKING_SAMPLER  # noqa: E402
from scripts.p106b_http_errors import capture_http_error as _safe_error  # noqa: E402
from scripts.diag_p106b_teacher_answer_repair import (  # noqa: E402
    CTX as F_CTX, MAX_TOKENS as F_CAP, SAMPLER as F_SAMPLER,
    THINKING_BUDGET as F_THINKING_BUDGET,
)
from scripts.p106b_teacher_format import parse_reply, teacher_prompt  # noqa: E402

F_PARTIAL = ROOT / "HF/sft_ready/p106b_bilingual_v1/teacher_pilot/teacher_raw_000000.jsonl"
I_PARTIAL = ROOT / "HF/sft_ready/p106b_teacher_sft/v10_online_rate5_low/raw_000000.jsonl"
F_SHA = "2D395CD2155D04934F13240430B4D566BA621B6871775BCCB4083D8202E7347E"
I_SHA = "17A3EE87711E78D58FCD4A3BEF3A16662A02BE7BF25A00C4B949C22780EE5146"
OUTPUT_DIR = ROOT / "HF/sft_ready/p106b_teacher_sft/v11_http500_isolation"
RAW = OUTPUT_DIR / "requests.jsonl"
REPORT = OUTPUT_DIR / "report.json"
HARD_WALL_SEC = 600
SERVER_LINE = re.compile(r"error|fail|context|memory|oom|slot|token|exception", re.I)


def pinned_inputs() -> list[dict]:
    for path, expected in ((F_PARTIAL, F_SHA), (I_PARTIAL, I_SHA)):
        if path.is_symlink() or not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"partial source absent/linked/changed: {path.relative_to(ROOT)}")
    f_jobs, _ = select_jobs()
    online, _ = source_jobs()
    if len(f_jobs) != 32 or len(online["ko"]) < 23:
        raise ValueError("fixed failed-input selection differs")
    return [
        {"arm": "stage2f", "position": 25, "job": f_jobs[24]},
        {"arm": "stage2f", "position": 26, "job": f_jobs[25]},
        {"arm": "stage2i_low", "position": 22, "job": online["ko"][21]},
        {"arm": "stage2i_low", "position": 23, "job": online["ko"][22]},
    ]


def _payload(entry: dict) -> tuple[list[dict], dict, int, int]:
    job = entry["job"]
    if entry["arm"] == "stage2f":
        prompt = teacher_prompt(job["task"], job["target_language"], {
            "concept_id": job["concept_id"],
            "family_heuristic": job["family_heuristic"],
            "source_turns": job["source_turns"],
        })
        payload = {"messages": prompt, **F_SAMPLER, "max_tokens": F_CAP,
                   "thinking_budget_tokens": F_THINKING_BUDGET,
                   "seed": int(job["job_id"][:8], 16) + 1}
        return prompt, payload, F_CTX, F_CAP
    turn = job["source_turns"][0]
    prompt = teacher_prompt(job["task"], "ko", {
        "user_en": turn["user_text"], "original_assistant_en": turn["assistant_text"]})
    payload = {"messages": prompt, **THINKING_SAMPLER, "max_tokens": 2048,
               "reasoning_effort": "low", "seed": 20260928 + entry["position"]}
    return prompt, payload, 3072, 2048


def _token_budget(port: int, key: str, payload: dict, ctx: int, cap: int) -> dict:
    try:
        formatted = _http_json(f"http://127.0.0.1:{port}/apply-template", key,
                               {"messages": payload["messages"],
                                "reasoning_effort": payload.get("reasoning_effort", "medium")}, timeout=10)
        prompt = formatted.get("prompt")
        if not isinstance(prompt, str):
            raise ValueError("apply-template returned no prompt")
        tokens = _http_json(f"http://127.0.0.1:{port}/tokenize", key,
                            {"content": prompt, "add_special": False,
                             "parse_special": True}, timeout=10).get("tokens")
        if not isinstance(tokens, list):
            raise ValueError("tokenize returned no tokens")
        return {"input_tokens": len(tokens), "ctx": ctx, "requested_max_tokens": cap,
                "nominal_sum_exceeds_ctx": len(tokens) + cap > ctx,
                "method": "server /apply-template then /tokenize; template parity with chat completion unverified"}
    except (OSError, HTTPError, URLError, ValueError, KeyError, TypeError) as exc:
        return {"input_tokens": None, "ctx": ctx, "requested_max_tokens": cap,
                "method": "TOKEN_PREFLIGHT_UNAVAILABLE", "error_type": type(exc).__name__}


def self_test() -> None:
    assert HARD_WALL_SEC == 600 and F_CAP == 4096
    fake = HTTPError("http://127.0.0.1", 500, "error", {}, None)
    assert fake.code == 500
    assert OUTPUT_DIR.is_relative_to(ROOT / "HF")
    print("[PASS] teacher-only four fixed requests, 600s hard wall and write-once diagnostic output; GPU NOT_RUN")


def execute(entries: list[dict]) -> int:
    if OUTPUT_DIR.exists() or OUTPUT_DIR.is_symlink():
        raise FileExistsError("v11 diagnostic output already exists; never overwrite")
    if _compute_apps():
        print("[HOLD] competing GPU compute app; teacher not started")
        return 8
    baseline_used, baseline_free = read_memory()
    if baseline_free < 8192:
        print("[HOLD] GPU free below 8192MiB; teacher not started")
        return 8
    assets = asset_preflight(hash_model=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    rows: list[dict] = []
    has_http_error = False
    with RAW.open("x", encoding="utf-8") as stream:
        for arm in ("stage2f", "stage2i_low"):
            ctx = F_CTX if arm == "stage2f" else 3072
            port, key = _free_port(), os.urandom(24).hex()
            command = [str(SERVER), "--offline", "--model", str(MODEL),
                       "--host", "127.0.0.1", "--port", str(port), "--api-key", key,
                       "--no-webui", "--cors-origins", "localhost", "--no-cors-credentials",
                       "--cache-ram", "0", "--verbosity", "4", "--ctx-size", str(ctx),
                       "--batch-size", "64", "--ubatch-size", "64", "--threads", "8",
                       "--no-warmup", "--fit", "off", "--no-op-offload", "--gpu-layers", "all"]
            command += (["--chat-template-kwargs", '{"reasoning_effort":"medium"}']
                        if arm == "stage2f" else ["--reasoning", "auto"])
            server = None
            stop = threading.Event()
            sampled_used = [baseline_used]
            server_errors: deque[str] = deque(maxlen=20)
            try:
                server = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                          text=True, errors="replace", bufsize=1,
                                          start_new_session=True)

                def drain() -> None:
                    assert server is not None and server.stdout is not None
                    for line in server.stdout:
                        if SERVER_LINE.search(line):
                            safe = line.replace(key, "<redacted-api-key>")
                            server_errors.append(safe.strip()[:500])

                def sample() -> None:
                    while not stop.wait(0.2):
                        try:
                            sampled_used.append(read_memory()[0])
                        except (OSError, RuntimeError, ValueError, IndexError):
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
                    raise TimeoutError("teacher health timeout")
                for entry in [item for item in entries if item["arm"] == arm]:
                    if time.monotonic() - started >= HARD_WALL_SEC - 140:
                        raise TimeoutError("four-request wall budget exhausted")
                    prompt, payload, _, cap = _payload(entry)
                    budget = _token_budget(port, key, payload, ctx, cap)
                    input_sha = hashlib.sha256(json.dumps(prompt, ensure_ascii=False,
                                                           sort_keys=True).encode()).hexdigest().upper()
                    before_used, before_free = read_memory()
                    t0 = time.monotonic()
                    outcome: dict
                    try:
                        reply = _http_json(f"http://127.0.0.1:{port}/v1/chat/completions",
                                           key, payload, timeout=130)
                        parsed = parse_reply(reply, language=entry["job"]["target_language"])
                        outcome = {"http_status": 200, "format_status": parsed["format_status"],
                                   "finish_reason": parsed["finish_reason"],
                                   "completion_tokens": parsed["usage"]["completion_tokens"],
                                   "reasoning_sha256": hashlib.sha256(parsed["teacher_reasoning_content"].encode()).hexdigest().upper(),
                                   "final_sha256": hashlib.sha256(parsed["teacher_final_content"].encode()).hexdigest().upper()}
                    except HTTPError as exc:
                        outcome = _safe_error(exc, key)
                        has_http_error = True
                    except (OSError, URLError, TimeoutError) as exc:
                        outcome = {"http_status": None, "error_type": type(exc).__name__,
                                   "message": str(exc)[:400]}
                        has_http_error = True
                    after_used, after_free = read_memory()
                    row = {"schema": "P106B_STAGE2JW_HTTP500_ROW_V1",
                           "arm": arm, "position": entry["position"],
                           "job_id": entry["job"]["job_id"],
                           "source_id": entry["job"]["source_id"],
                           "prompt_sha256": input_sha, "token_budget": budget,
                           "request_wall_sec": round(time.monotonic() - t0, 3),
                           "used_mib_before_after": [before_used, after_used],
                           "free_mib_before_after": [before_free, after_free],
                           "sampled_peak_used_mib": max(sampled_used),
                           "outcome": outcome,
                           "server_diagnostic_tail": list(server_errors)}
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                    stream.flush()
                    rows.append(row)
                    print("[HTTP500_ISOLATION] " + json.dumps({
                        "arm": arm, "position": entry["position"],
                        "input_tokens": budget.get("input_tokens"),
                        "ctx": ctx, "max_tokens": cap,
                        "nominal_sum_exceeds_ctx": budget.get("nominal_sum_exceeds_ctx"),
                        "http_status": outcome.get("http_status"),
                        "error_type": outcome.get("error_type", ""),
                        "body_sha256": outcome.get("body_sha256", ""),
                        "request_wall_sec": row["request_wall_sec"],
                        "free_mib_after": after_free,
                        "sampled_peak_used_mib": row["sampled_peak_used_mib"]},
                        sort_keys=True), flush=True)
                    if outcome.get("http_status") != 200:
                        break
            finally:
                stop.set()
                _kill_group(server)
    report = {"schema": "P106B_STAGE2JW_HTTP500_ISOLATION_V1",
              "teacher_assets": assets, "source_partial_shas": {"stage2f": F_SHA,
                                                            "stage2i_low": I_SHA},
              "requests_recorded": len(rows), "http_errors_recorded": sum(
                  row["outcome"].get("http_status") != 200 for row in rows),
              "whole_wall_sec": round(time.monotonic() - started, 3),
              "raw_jsonl": RAW.relative_to(ROOT).as_posix(),
              "raw_sha256": sha256_file(RAW),
              "student_loaded": False, "student_updates": 0,
              "old_long_session_reproduced": False,
              "scope": "two fresh teacher servers, each predecessor+failed input only; no accumulated server state or student co-residency"}
    with REPORT.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("[HTTP500_SUMMARY] " + json.dumps({k: report[k] for k in (
        "requests_recorded", "http_errors_recorded", "whole_wall_sec",
        "raw_sha256", "student_updates", "old_long_session_reproduced")},
        sort_keys=True), flush=True)
    return 9 if has_http_error else 0


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
            entries = pinned_inputs()
            if args.check_only:
                print(json.dumps({"positions": [(r["arm"], r["position"],
                                                 r["job"]["job_id"]) for r in entries],
                                  "output": OUTPUT_DIR.relative_to(ROOT).as_posix(),
                                  "student_updates": 0, "model_gpu": "NOT_RUN"}, sort_keys=True))
                print("[CHECK_ONLY] exact old partial SHA and four fixed jobs PASS; GPU NOT_RUN")
            else:
                def time_limit(_signum, _frame):
                    raise TimeoutError("P106B Stage2jW 600s hard wall")
                old = signal.signal(signal.SIGALRM, time_limit)
                signal.alarm(HARD_WALL_SEC)
                try:
                    return execute(entries)
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old)
        return 0
    except (OSError, ValueError, RuntimeError, TimeoutError, TypeError, KeyError) as exc:
        print(f"[FAIL] P106B Stage2jW {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
