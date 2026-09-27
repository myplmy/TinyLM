#!/usr/bin/env python3
"""P106B Stage2hW: bounded Bonsai none/low/medium generation-rate probe.

Four pinned questions use the same model, source, tagged prompt, sampler,
max output, context and per-question seed. Effort/order vary deliberately.
The server remains --reasoning auto; per-request reasoning_effort is explicit.
No student model or dataset acceptance. Raw reasoning/final is write-once HF;
runlog contains only timing, usage and completion status.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
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
from scripts.diag_p106_bonsai_assets import sha256_file  # noqa: E402
from scripts.diag_p106_coload import _free_port, _http_json  # noqa: E402
from scripts.diag_p106_full_coload_accum import _compute_apps, _kill_group  # noqa: E402
from scripts.diag_p106_vram_sample import read_memory  # noqa: E402
from scripts.diag_p106_oasst2_teacher_ko_gate import MODEL, MODEL_SHA256, SERVER, asset_preflight  # noqa: E402
from scripts.diag_p106b_teacher_answer_repair import CTX, SAMPLER, full_source_cases  # noqa: E402
from scripts.p106b_teacher_format import parse_reply, teacher_prompt  # noqa: E402

SAMPLER_BASE = {key: value for key, value in SAMPLER.items() if key != "reasoning_effort"}
CASES = (2, 5, 14, 16)  # math, code/API, professional format, style/persona.
EFFORTS = ("none", "low", "medium")
ORDERS = (("none", "low", "medium"), ("medium", "low", "none"),
          ("low", "none", "medium"), ("medium", "none", "low"))
MAX_TOKENS = 2048
WALL_LIMIT = 900
V9_DIR = ROOT / "HF/sft_ready/p106b_teacher_sft/v9"
OUTPUT = V9_DIR / "reasoning_effort_profile.jsonl"
MANIFEST = V9_DIR / "reasoning_effort_profile_manifest.json"


def selected_cases() -> tuple[list[dict], dict]:
    source, lineage = full_source_cases()
    if len(source) != 16:
        raise ValueError("pinned OASST2 source is not 16 cases")
    return [source[index - 1] for index in CASES], lineage


def self_test() -> None:
    assert len(CASES) == len(ORDERS) == 4 and all(set(order) == set(EFFORTS) for order in ORDERS)
    base = teacher_prompt("repair", "ko", {"user_en": "What is 2+2?", "original_assistant_en": "4"})
    for effort in EFFORTS:
        payload = {"messages": base, **SAMPLER_BASE, "max_tokens": MAX_TOKENS,
                   "reasoning_effort": effort, "seed": 1337}
        assert payload["reasoning_effort"] == effort and "thinking_budget_tokens" not in payload
    print("[PASS] none/low/medium same prompt/seed/sampler/cap and crossed order; model/GPU NOT_RUN")


def execute(cases: list[dict], lineage: dict) -> int:
    if V9_DIR.is_symlink() or any(path.exists() or path.is_symlink() for path in (OUTPUT, MANIFEST)):
        raise FileExistsError("reasoning-effort output version already exists; use another stage")
    assets = asset_preflight(hash_model=True)
    if _compute_apps():
        print("[HOLD] competing GPU compute app; teacher not started")
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
               "--reasoning", "auto"]
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
        V9_DIR.mkdir(parents=True, exist_ok=True)
        summary: dict[str, Counter[str]] = {name: Counter() for name in EFFORTS}
        with OUTPUT.open("x", encoding="utf-8") as stream:
            for panel_index, (pair, order) in enumerate(zip(cases, ORDERS), 1):
                source = {"user_en": pair["user_en"],
                          "original_assistant_en": pair["assistant_en"]}
                prompt = teacher_prompt("repair", "ko", source)
                seed = 20260928 + panel_index
                for position, effort in enumerate(order, 1):
                    if time.monotonic() - begin >= WALL_LIMIT:
                        print("[GATE NEGATIVE] bounded effort wall reached; partial v9 raw preserved")
                        return 8
                    payload = {"messages": prompt, **SAMPLER_BASE, "max_tokens": MAX_TOKENS,
                               "reasoning_effort": effort, "seed": seed}
                    started = time.monotonic()
                    error = ""
                    try:
                        reply = _http_json(f"http://127.0.0.1:{port}/v1/chat/completions", key,
                                           payload, timeout=120)
                        row = parse_reply(reply, language="ko")
                    except HTTPError as exc:
                        error = f"HTTP_{exc.code}"
                        row = {"format_status": "API_UNSUPPORTED", "finish_reason": "ERROR",
                               "teacher_reasoning_content": "", "teacher_final_content": "",
                               "parsed_content": None, "parse_error": error,
                               "usage": {"completion_tokens": None, "prompt_tokens": None,
                                         "total_tokens": None}}
                    elapsed = round(time.monotonic() - started, 3)
                    tokens = row.get("usage", {}).get("completion_tokens")
                    summary[effort][row["format_status"]] += 1
                    summary[effort]["requests"] += 1
                    if type(tokens) is int and tokens >= 0:
                        summary[effort]["completion_tokens"] += tokens
                    else:
                        summary[effort]["usage_missing"] += 1
                    summary[effort]["request_wall_ms"] += round(elapsed * 1000)
                    record = {"schema": "P106B_STAGE2HW_EFFORT_ROW_V1",
                              "case": CASES[panel_index - 1],
                              "source_tree_id": pair["tree_id"],
                              "user_en": pair["user_en"],
                              "original_assistant_en": pair["assistant_en"],
                              "effort": effort, "order_position": position, "seed": seed,
                              "prompt_sha256": hashlib.sha256(json.dumps(
                                  prompt, ensure_ascii=False, sort_keys=True).encode()).hexdigest().upper(),
                              "request_wall_sec": elapsed, "api_error": error,
                              "teacher": row, "accepted_for_training": False,
                              "student_training": "NOT_RUN"}
                    stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                    stream.flush()
                    print("[EFFORT_ROW] " + json.dumps({
                        "case": record["case"], "effort": effort,
                        "format": row["format_status"], "finish": row["finish_reason"],
                        "completion_tokens": tokens,
                        "reasoning_chars": len(row["teacher_reasoning_content"]),
                        "final_chars": len(row["teacher_final_content"]),
                        "request_wall_sec": elapsed, "api_error": error}, sort_keys=True),
                          flush=True)
        per_effort = {}
        for effort, counter in summary.items():
            wall = counter["request_wall_ms"] / 1000
            tokens = counter["completion_tokens"]
            per_effort[effort] = {"requests": counter["requests"],
                                  "format_status": {k: v for k, v in counter.items()
                                                    if k not in {"requests", "completion_tokens",
                                                                 "request_wall_ms", "usage_missing"}},
                                  "completion_tokens": tokens,
                                  "request_wall_sec": round(wall, 3),
                                  "completion_tokens_per_request_wall_sec":
                                  round(tokens / wall, 3) if wall and not counter["usage_missing"] else None,
                                  "usage_missing": counter["usage_missing"]}
        report = {"schema": "P106B_STAGE2HW_EFFORT_PROFILE_V1",
                  "source": lineage, "teacher_model_sha256": MODEL_SHA256,
                  "asset_preflight": assets,
                  "cases": list(CASES), "efforts": list(EFFORTS),
                  "orders": [list(order) for order in ORDERS],
                  "ctx": CTX, "max_tokens": MAX_TOKENS,
                  "sampler": SAMPLER_BASE, "thinking_budget_tokens": "NOT_SET",
                  "server_reasoning": "auto", "per_effort": per_effort,
                  "whole_wall_sec": round(time.monotonic() - begin, 3),
                  "raw_jsonl": OUTPUT.relative_to(ROOT).as_posix(),
                  "raw_sha256": sha256_file(OUTPUT),
                  "student_training": "NOT_RUN", "quality": "NOT_RUN",
                  "limit": "four selected Korean repair tasks; request wall includes HTTP overhead and first-call effects, not pure GPU decode"}
        with MANIFEST.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({k: report[k] for k in ("schema", "per_effort", "whole_wall_sec",
                                              "raw_sha256", "student_training", "quality")},
                         ensure_ascii=False, sort_keys=True), flush=True)
        if any(summary[effort]["requests"] != 4 or summary[effort]["usage_missing"]
               for effort in EFFORTS):
            print("[GATE NEGATIVE] one effort unavailable or missing usage; retain all observations")
            return 8
        print("[PASS] bounded effort/format timing recorded; quality/student training NOT_RUN")
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
        cases, source = selected_cases()
        if args.check_only:
            print(json.dumps({"cases": list(CASES), "efforts": list(EFFORTS),
                              "orders": [list(x) for x in ORDERS],
                              "max_tokens": MAX_TOKENS, "sampler": SAMPLER_BASE,
                              "source": source,
                              "model_gpu": "NOT_RUN", "student_training": "NOT_RUN",
                              "new_output": OUTPUT.relative_to(ROOT).as_posix()}, sort_keys=True))
            print("[CHECK_ONLY] pinned teacher source/effort prompt PASS; GPU NOT_RUN")
            return 0
        def time_limit(_signum, _frame):
            raise TimeoutError("P106B effort profile hard wall exceeded; partial v9 raw preserved")
        old = signal.signal(signal.SIGALRM, time_limit)
        signal.alarm(WALL_LIMIT + 120)
        try:
            return execute(cases, source)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
    except (OSError, ValueError, RuntimeError, TimeoutError, TypeError, KeyError) as exc:
        print(f"[FAIL] P106B Stage2hW {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
