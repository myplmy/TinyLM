#!/usr/bin/env python3
"""P106B Stage2jWb: one-request PEG parser-bypass forensic probe.

The failed Stage2f case 26 is replayed with exactly the original prompt,
sampler and model, changing only llama-server --skip-chat-parsing. Raw content
is kept write-once in ignored HF. It is NEVER a canonical training target:
the bypass puts reasoning/native framing into message.content.
"""
from __future__ import annotations

import argparse
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
from scripts.diag_p106b_http500_isolation import _payload, pinned_inputs  # noqa: E402
from scripts.p106b_http_errors import capture_http_error as _safe_error  # noqa: E402

OUTPUT_DIR = ROOT / "HF/sft_ready/p106b_teacher_sft/v12_peg_bypass_case26"
RAW = OUTPUT_DIR / "response.json"
WALL = 300


def self_test() -> None:
    assert OUTPUT_DIR.is_relative_to(ROOT / "HF")
    assert WALL == 300
    print("[PASS] one fixed case, --skip-chat-parsing only; no student/target/ckpt; GPU NOT_RUN")


def execute(entry: dict) -> int:
    if OUTPUT_DIR.exists() or OUTPUT_DIR.is_symlink():
        raise FileExistsError("v12 parser-bypass output exists; do not overwrite")
    if _compute_apps():
        print("[HOLD] competing GPU compute app; no teacher started")
        return 8
    baseline_used, baseline_free = read_memory()
    if baseline_free < 8192:
        print("[HOLD] GPU free below 8192MiB; no teacher started")
        return 8
    assets = asset_preflight(hash_model=True)
    prompt, payload, ctx, cap = _payload(entry)
    port, key = _free_port(), os.urandom(24).hex()
    command = [str(SERVER), "--offline", "--model", str(MODEL),
               "--host", "127.0.0.1", "--port", str(port), "--api-key", key,
               "--no-webui", "--cors-origins", "localhost", "--no-cors-credentials",
               "--cache-ram", "0", "--verbosity", "4", "--ctx-size", str(ctx),
               "--batch-size", "64", "--ubatch-size", "64", "--threads", "8",
               "--no-warmup", "--fit", "off", "--no-op-offload", "--gpu-layers", "all",
               "--chat-template-kwargs", '{"reasoning_effort":"medium"}',
               "--skip-chat-parsing"]
    server = None
    errors: list[str] = []
    began = time.monotonic()
    try:
        server = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, errors="replace", bufsize=1,
                                  start_new_session=True)

        def drain() -> None:
            assert server is not None and server.stdout is not None
            for line in server.stdout:
                if re.search(r"error|fail|peg-native|exception", line, re.I):
                    errors.append(line.replace(key, "<redacted-api-key>").strip()[:500])
                    if len(errors) > 40:
                        del errors[:20]

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
        t0 = time.monotonic()
        try:
            reply = _http_json(f"http://127.0.0.1:{port}/v1/chat/completions",
                               key, payload, timeout=150)
            choice = reply["choices"][0]
            message = choice["message"]
            content = message.get("content")
            if not isinstance(content, str):
                raise ValueError("bypassed response has no text content")
            outcome = {"http_status": 200, "finish_reason": choice.get("finish_reason"),
                       "content": content, "content_sha256": hashlib.sha256(content.encode()).hexdigest().upper(),
                       "completion_tokens": reply.get("usage", {}).get("completion_tokens"),
                       "native_marker_counts": {marker: content.count(marker) for marker in (
                           "<|im_start|>", "<|im_end|>", "<think>", "</think>",
                           "[[QUESTION]]", "[[/QUESTION]]", "[[ANSWER]]", "[[/ANSWER]]")}}
        except HTTPError as exc:
            outcome = _safe_error(exc, key)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
        record = {"schema": "P106B_STAGE2JWB_PEG_BYPASS_V1",
                  "source_failed_input": "Stage2fW case26, Stage2jW reproduced HTTP500",
                  "source_job_id": entry["job"]["job_id"],
                  "prompt_sha256": hashlib.sha256(json.dumps(prompt, ensure_ascii=False,
                                                               sort_keys=True).encode()).hexdigest().upper(),
                  "teacher_assets": assets, "change_only": "--skip-chat-parsing",
                  "ctx": ctx, "max_tokens": cap,
                  "baseline_used_free_mib": [baseline_used, baseline_free],
                  "after_used_free_mib": list(read_memory()),
                  "request_wall_sec": round(time.monotonic() - t0, 3),
                  "whole_wall_sec": round(time.monotonic() - began, 3),
                  "outcome": outcome, "server_error_tail": errors,
                  "student_training": "NOT_RUN", "accepted_for_training": False,
                  "reasoning_final_separation": "NOT_RUN_RAW_BYPASS"}
        with RAW.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        print("[PEG_BYPASS] " + json.dumps({
            "http_status": outcome.get("http_status"),
            "error_type": outcome.get("error_type", ""),
            "content_sha256": outcome.get("content_sha256", ""),
            "completion_tokens": outcome.get("completion_tokens"),
            "native_marker_counts": outcome.get("native_marker_counts", {}),
            "request_wall_sec": record["request_wall_sec"],
            "raw_sha256": sha256_file(RAW),
            "student_training": "NOT_RUN"}, sort_keys=True), flush=True)
        return 0 if outcome.get("http_status") == 200 else 9
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
            entries = pinned_inputs()
            entry = next(row for row in entries if row["arm"] == "stage2f" and row["position"] == 26)
            if args.check_only:
                print(json.dumps({"case": 26, "job_id": entry["job"]["job_id"],
                                  "output": OUTPUT_DIR.relative_to(ROOT).as_posix(),
                                  "student_training": "NOT_RUN", "model_gpu": "NOT_RUN"},
                                 sort_keys=True))
                print("[CHECK_ONLY] exact failed input pinned; model/GPU NOT_RUN")
            else:
                def time_limit(_signum, _frame):
                    raise TimeoutError("P106B Stage2jWb 300s hard wall")
                old = signal.signal(signal.SIGALRM, time_limit)
                signal.alarm(WALL)
                try:
                    return execute(entry)
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old)
        return 0
    except (OSError, ValueError, RuntimeError, TimeoutError, TypeError, KeyError) as exc:
        print(f"[FAIL] P106B Stage2jWb {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
