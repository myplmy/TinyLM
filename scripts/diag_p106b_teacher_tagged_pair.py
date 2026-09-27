#!/usr/bin/env python3
"""P106B Stage2cW: user-run paired tagged-vs-JSON teacher wire-format gate.

The same sixteen pinned OASST2 questions, model, sampler, context and seeds
are tested in crossed order. Only the requested output wire format differs.
Both raw reasoning and final text remain in a new write-once ignored HF v6;
neither arm becomes a student training dataset or a truth-verification result.
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
from scripts.diag_p106_bonsai_assets import regular, sha256_file  # noqa: E402
from scripts.diag_p106_coload import _free_port, _http_json  # noqa: E402
from scripts.diag_p106_full_coload_accum import _compute_apps, _kill_group  # noqa: E402
from scripts.diag_p106_vram_sample import read_memory  # noqa: E402
from scripts.diag_p106_oasst2_teacher_ko_gate import (  # noqa: E402
    MODEL, MODEL_SHA256, SERVER, asset_preflight,
)
from scripts.diag_p106b_teacher_answer_repair import (  # noqa: E402
    CTX, MAX_TOKENS, SAMPLER, THINKING_BUDGET, FULL_OUTPUT, FULL_MANIFEST,
    full_source_cases,
)
from scripts.p106b_teacher_format import parse_reply, teacher_prompt  # noqa: E402
from scripts.p106b_teacher_wrapper import wrap_turns  # noqa: E402

V4_SHA256 = "63E7F7A1E487F10E1A1214E2C2489AD9DDD754DEDE33CA5893242CEAE983CAFA"
V6_DIR = ROOT / "HF/sft_ready/p106b_teacher_sft/v6"
OUTPUT = V6_DIR / "tagged_json_pair_attempts.jsonl"
MANIFEST = V6_DIR / "tagged_json_pair_manifest.json"
WALL_LIMIT = 2400
FORMATS = ("tagged", "json_control")


def check_inputs() -> tuple[list[dict], dict]:
    selected, source = full_source_cases()
    if not regular(FULL_OUTPUT) or not regular(FULL_MANIFEST):
        raise FileNotFoundError("v4 full16 raw/manifest absent or linked")
    prior = json.loads(FULL_MANIFEST.read_text(encoding="utf-8"))
    if (prior.get("schema") != "P106B_STAGE1FW_TEACHER_REPAIR_FULL16_V1"
            or prior.get("rows") != 16 or sha256_file(FULL_OUTPUT) != V4_SHA256
            or prior.get("raw_sha256") != V4_SHA256
            or prior.get("source", {}).get("v3_sha256") != source["v3_sha256"]
            or len(selected) != 16):
        raise ValueError("pinned full16/teacher lineage differs")
    return selected, {"v1_sha256": source["v1_sha256"],
                      "v2_sha256": source["v2_sha256"],
                      "v3_sha256": source["v3_sha256"],
                      "v4_sha256": V4_SHA256,
                      "source_tree_ids": [item["tree_id"] for item in selected]}


def self_test() -> None:
    assert len(FORMATS) == 2 and WALL_LIMIT == 2400
    source = {"user_en": "What is 2+2?", "original_assistant_en": "5"}
    a = teacher_prompt("repair", "ko", source, output_format="tagged")
    b = teacher_prompt("repair", "ko", source, output_format="json_control")
    assert a[1] == b[1] and a[0] != b[0]
    reply = {"choices": [{"finish_reason": "stop", "message": {
        "reasoning_content": "private thought",
        "content": "[[QUESTION]]\n2+2는?\n[[/QUESTION]]\n[[ANSWER]]\n4입니다.\n[[/ANSWER]]"}}]}
    record = parse_reply(reply, language="ko", output_format="tagged")
    assert record["format_status"] == "TAGGED_COMPLETE"
    canonical = wrap_turns([{"user_text": record["parsed_content"]["user_text"],
                             "assistant_text": record["parsed_content"]["assistant_text"]}],
                           source_id="fixture:1", source_sha256="A" * 64,
                           teacher_model_sha256="B" * 64, language="ko",
                           source_license="fixture-only", generation_id="stage2cw")
    assert [m["role"] for m in canonical["messages"]] == ["user", "assistant"]
    assert "private thought" not in json.dumps(canonical, ensure_ascii=False)
    print("[PASS] crossed paired prompts, tagged parser and content-only canonical wrapper; model/GPU NOT_RUN")


def execute(selected: list[dict], source: dict) -> int:
    if V6_DIR.is_symlink() or any(path.exists() or path.is_symlink() for path in (OUTPUT, MANIFEST)):
        raise FileExistsError("v6 wire-format pair already exists; use another stage/version")
    asset_preflight(hash_model=True)
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
        V6_DIR.mkdir(parents=True, exist_ok=True)
        status: dict[str, Counter[str]] = {name: Counter() for name in FORMATS}
        wrapped_count: Counter[str] = Counter()
        completion_tokens: Counter[str] = Counter()
        request_wall: Counter[str] = Counter()
        with OUTPUT.open("x", encoding="utf-8") as stream:
            for index, pair in enumerate(selected):
                if time.monotonic() - begin >= WALL_LIMIT:
                    print("[GATE NEGATIVE] hard wall reached; partial v6 journal retained")
                    return 8
                order = FORMATS if index % 2 == 0 else tuple(reversed(FORMATS))
                for output_format in order:
                    prompt = teacher_prompt("repair", "ko", {
                        "user_en": pair["user_en"],
                        "original_assistant_en": pair["assistant_en"]},
                        output_format=output_format)
                    payload = {"messages": prompt, **SAMPLER, "max_tokens": MAX_TOKENS,
                               "thinking_budget_tokens": THINKING_BUDGET,
                               "seed": 20260928 + index}
                    started = time.monotonic()
                    reply = _http_json(f"http://127.0.0.1:{port}/v1/chat/completions", key,
                                       payload, timeout=120)
                    measured = round(time.monotonic() - started, 3)
                    row = parse_reply(reply, language="ko", output_format=output_format)
                    wrapped = False
                    if row["parsed_content"] is not None:
                        fields = row["parsed_content"]
                        try:
                            wrap_turns([{"user_text": fields["user_text"],
                                         "assistant_text": fields["assistant_text"]}],
                                       source_id=pair["tree_id"],
                                       source_sha256=source["v4_sha256"],
                                       teacher_model_sha256=MODEL_SHA256,
                                       language="ko", source_license="Apache-2.0_card_only",
                                       generation_id=f"stage2cw:{index}:{output_format}",
                                       correction_note=fields["correction_note"])
                            wrapped = True
                        except ValueError as exc:
                            row["parse_error"] = f"canonical wrapper: {exc}"
                    status[output_format][row["format_status"]] += 1
                    if wrapped:
                        wrapped_count[output_format] += 1
                    usage = row["usage"]["completion_tokens"]
                    if type(usage) is int and usage >= 0:
                        completion_tokens[output_format] += usage
                    else:
                        status[output_format]["USAGE_MISSING"] += 1
                    request_wall[output_format] += measured
                    record = {"case": index + 1, "source_tree_id": pair["tree_id"],
                              "source_user_en": pair["user_en"],
                              "source_assistant_en": pair["assistant_en"],
                              "output_format": output_format, "order_in_pair": order.index(output_format),
                              "prompt_sha256": hashlib.sha256(json.dumps(
                                  prompt, ensure_ascii=False, sort_keys=True).encode()).hexdigest().upper(),
                              "request_wall_sec": measured, "canonical_wrapper_ok": wrapped,
                              "teacher": row, "accepted_for_training": False}
                    stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                    stream.flush()
                    print("[WIRE_PAIR] " + json.dumps({"case": index + 1,
                        "format": output_format, "status": row["format_status"],
                        "finish": row["finish_reason"], "completion_tokens": usage,
                        "request_wall_sec": measured, "canonical_wrapper_ok": wrapped},
                        sort_keys=True), flush=True)
        report = {"schema": "P106B_STAGE2CW_TAGGED_JSON_PAIR_V1",
                  "source": source, "teacher_model_sha256": MODEL_SHA256,
                  "language": "ko", "task": "repair", "cases": len(selected),
                  "requests": 2 * len(selected), "ctx": CTX,
                  "max_tokens": MAX_TOKENS, "thinking_budget_tokens": THINKING_BUDGET,
                  "sampler": SAMPLER, "order": "ABBA alternating by case",
                  "format_status": {name: dict(status[name]) for name in FORMATS},
                  "canonical_wrapper_ok": dict(wrapped_count),
                  "completion_tokens": dict(completion_tokens),
                  "request_wall_sec": {k: round(v, 3) for k, v in request_wall.items()},
                  "whole_wall_sec": round(time.monotonic() - begin, 3),
                  "raw_jsonl": OUTPUT.relative_to(ROOT).as_posix(),
                  "raw_sha256": sha256_file(OUTPUT),
                  "accepted_for_training": 0, "student_training": "NOT_RUN",
                  "quality": "NOT_RUN", "limit": "same source paired wire-format only; no truth or broad corpus claim"}
        with MANIFEST.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
        complete = status["tagged"]["TAGGED_COMPLETE"]
        if complete < 12 or wrapped_count["tagged"] < 12:
            print(f"[GATE NEGATIVE] tagged fields/wrapped {complete}/{wrapped_count['tagged']} of 16 below preregistered 12/16")
            return 8
        print("[PASS] tagged output format only; completion/time paired, truth/student SFT NOT_RUN")
        return 0
    finally:
        _kill_group(server)


def main() -> int:
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
        selected, source = check_inputs()
        if args.check_only:
            print(json.dumps({"source": source, "cases": len(selected),
                              "requests": 2 * len(selected), "sampler": SAMPLER,
                              "new_output": OUTPUT.relative_to(ROOT).as_posix(),
                              "model_gpu": "NOT_RUN", "student_training": "NOT_RUN"}, sort_keys=True))
            print("[CHECK_ONLY] v4/source lineage PASS; teacher/model/GPU NOT_RUN")
            return 0
        def time_limit(_signum, _frame):
            raise TimeoutError("Stage2cW hard wall exceeded; partial v6 journal preserved")
        old = signal.signal(signal.SIGALRM, time_limit)
        signal.alarm(WALL_LIMIT + 120)
        try:
            return execute(selected, source)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
    except (OSError, ValueError, RuntimeError, TimeoutError, TypeError, KeyError) as exc:
        print(f"[FAIL] P106B Stage2cW {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
