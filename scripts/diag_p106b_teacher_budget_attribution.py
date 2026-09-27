#!/usr/bin/env python3
"""P106B Stage1aWb: bounded paired thinking-output attribution, not SFT.

The four public OASST2 pairs are chosen from the immutable v1 teacher ledger:
three previously incomplete plus one complete control. Both arms use the same
ctx4096, medium reasoning and explicit model-card thinking sampler; only the
completion-token cap differs. Teacher reasoning is retained for private audit
but is NEVER parsed as a student target. --execute is a user-authorized, under
ten-minute model diagnostic; CPU --self-test and --check-only do not load it.
"""
from __future__ import annotations

from collections import Counter, defaultdict
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
from scripts.diag_p106_oasst2_teacher_ko_gate import (  # noqa: E402
    DATASET_DIR as V1_DIR, MANIFEST as V1_MANIFEST, OUTPUT as V1_OUTPUT,
    MODEL, MODEL_SHA256, SERVER, asset_preflight, parse_translation,
    select_candidates, translation_prompt,
)
from scripts.diag_p106_bonsai_assets import regular, sha256_file  # noqa: E402
from scripts.diag_p106_coload import _free_port, _http_json  # noqa: E402
from scripts.diag_p106_full_coload_accum import _compute_apps, _kill_group  # noqa: E402
from scripts.diag_p106_vram_sample import read_memory  # noqa: E402

V2_DIR = V1_DIR.parent / "v2"
OUT = V2_DIR / "budget_probe.jsonl"
MANIFEST = V2_DIR / "budget_probe_manifest.json"
COUNT = 4
CTX = 4096
CAPS = (768, 3072)
WALL_LIMIT = 520
MODEL_CARD_THINKING = {
    "temperature": 1.0, "top_p": 0.95, "top_k": 20,
    "min_p": 0.05, "presence_penalty": 0.0, "repeat_penalty": 1.0,
    "reasoning_effort": "medium", "stream": False,
}


def choose_pairs() -> tuple[list[dict], dict]:
    if not regular(V1_OUTPUT) or not regular(V1_MANIFEST):
        raise FileNotFoundError("immutable v1 candidate/manifest absent or linked")
    manifest = json.loads(V1_MANIFEST.read_text(encoding="utf-8"))
    if (manifest.get("schema") != "P106_STAGE1AW_OASST2_KO_CANDIDATES_V1"
            or manifest.get("recorded") != 16
            or manifest.get("format_outcomes") != {"INCOMPLETE": 7, "JSON_COMPLETE": 9}
            or sha256_file(V1_OUTPUT) != manifest.get("output_sha256")):
        raise ValueError("v1 source status or SHA differs from the user log")
    selected, _ = select_candidates()
    old = [json.loads(line) for line in V1_OUTPUT.read_text(encoding="utf-8").splitlines()
           if line.strip()]
    if len(old) != len(selected) or any(
            row.get("source_tree_id") != pair["tree_id"]
            or row.get("user_en") != pair["user_en"]
            or row.get("assistant_en") != pair["assistant_en"]
            for row, pair in zip(old, selected)):
        raise ValueError("v1 rows do not match pinned source selection")
    previous_incomplete = [dict(pair, prior_status=row["format_status"])
                           for row, pair in zip(old, selected)
                           if row.get("format_status") == "INCOMPLETE"]
    previous_complete = [dict(pair, prior_status=row["format_status"])
                         for row, pair in zip(old, selected)
                         if row.get("format_status") == "JSON_COMPLETE"]
    if len(previous_incomplete) != 7 or len(previous_complete) != 9:
        raise ValueError("v1 candidate status counts differ")
    pairs = previous_incomplete[:3] + previous_complete[:1]
    return pairs, {"v1_candidate_sha256": manifest["output_sha256"],
                   "prior_incomplete": 3, "prior_complete_control": 1,
                   "tree_ids": [pair["tree_id"] for pair in pairs]}


def response_record(reply: dict, pair: dict, cap: int, elapsed: float) -> dict:
    choices = reply.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        choice: dict = {}
    else:
        choice = choices[0] if isinstance(choices[0], dict) else {}
    message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
    final_content = message.get("content")
    reasoning_content = message.get("reasoning_content")
    if not isinstance(final_content, str):
        final_content = ""
    if not isinstance(reasoning_content, str):
        reasoning_content = ""
    status, user_ko, assistant_ko = parse_translation(reply)
    usage = reply.get("usage") if isinstance(reply.get("usage"), dict) else {}
    timings = reply.get("timings") if isinstance(reply.get("timings"), dict) else {}
    prompt = translation_prompt(pair)
    return {
        "source_tree_id": pair["tree_id"], "prior_v1_status": pair["prior_status"],
        "user_en": pair["user_en"], "assistant_en": pair["assistant_en"],
        "prompt_sha256": hashlib.sha256(json.dumps(prompt, ensure_ascii=False,
                                                     sort_keys=True).encode()).hexdigest().upper(),
        "reasoning_effort": "medium", "ctx": CTX, "max_tokens": cap,
        "sampler": {key: val for key, val in MODEL_CARD_THINKING.items()
                    if key not in ("stream", "reasoning_effort")},
        "finish_reason": choice.get("finish_reason", "MISSING"),
        "format_status": status,
        "teacher_reasoning_content": reasoning_content,
        "teacher_final_content": final_content,
        "reasoning_chars": len(reasoning_content), "final_chars": len(final_content),
        "reasoning_sha256": hashlib.sha256(reasoning_content.encode()).hexdigest().upper(),
        "final_sha256": hashlib.sha256(final_content.encode()).hexdigest().upper(),
        "user_ko": user_ko, "assistant_ko": assistant_ko,
        "student_target_eligible": status == "JSON_COMPLETE",
        "student_target_source": "final_content.assistant_ko_only" if status == "JSON_COMPLETE" else "NONE",
        "student_training": "NOT_RUN", "truth_status": "PSEUDO_UNVERIFIED",
        "usage": {key: usage.get(key) for key in
                  ("prompt_tokens", "completion_tokens", "total_tokens")},
        "timings": {key: timings.get(key) for key in
                    ("prompt_n", "predicted_n", "prompt_ms", "predicted_ms")},
        "elapsed_sec": round(elapsed, 3),
    }


def summarize(rows: list[dict], source: dict, elapsed: float) -> dict:
    by_cap = defaultdict(list)
    for row in rows:
        by_cap[row["max_tokens"]].append(row)
    arms = {}
    for cap in CAPS:
        arm = by_cap[cap]
        arms[str(cap)] = {
            "responses": len(arm),
            "format_status": dict(Counter(row["format_status"] for row in arm)),
            "finish_reason": dict(Counter(row["finish_reason"] for row in arm)),
            "completed_previous_incomplete": sum(
                row["prior_v1_status"] == "INCOMPLETE" and row["format_status"] == "JSON_COMPLETE"
                for row in arm),
            "completion_tokens_reported": sum(
                row["usage"]["completion_tokens"] or 0 for row in arm),
            "teacher_reasoning_content_present": sum(bool(row["teacher_reasoning_content"]) for row in arm),
            "teacher_final_content_present": sum(bool(row["teacher_final_content"]) for row in arm),
        }
    return {
        "schema": "P106B_STAGE1AWB_BUDGET_ATTRIBUTION_V1",
        "dataset_version": "p106b_teacher_sft/v2",
        "source": source, "teacher_model_sha256": MODEL_SHA256,
        "teacher_ctx": CTX, "sampler": MODEL_CARD_THINKING,
        "paired_caps": list(CAPS), "rows": len(rows), "arms": arms,
        "elapsed_sec": round(elapsed, 3),
        "raw_jsonl": OUT.relative_to(ROOT).as_posix(),
        "raw_sha256": sha256_file(OUT),
        "student_training": "NOT_RUN", "quality": "NOT_RUN",
        "claim_limit": "Four selected v1 cases only; not a new 12/16 population gate",
    }


def self_test() -> None:
    pair = {"tree_id": "x", "prior_status": "INCOMPLETE",
            "user_en": "What is 2+2?", "assistant_en": "It is 4."}
    complete = {"choices": [{"finish_reason": "stop", "message": {
        "reasoning_content": "private thinking 2+2",
        "content": json.dumps({"user_ko": "2+2는?", "assistant_ko": "4입니다."}, ensure_ascii=False)}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 22}}
    row = response_record(complete, pair, CAPS[1], 1.0)
    assert row["student_target_eligible"] and row["assistant_ko"] == "4입니다."
    assert "private thinking" not in row["assistant_ko"]
    assert row["teacher_reasoning_content"] == "private thinking 2+2"
    truncated = {"choices": [{"finish_reason": "length", "message": {
        "reasoning_content": "unfinished thought", "content": '{"user_ko":'}}],
        "usage": {"completion_tokens": 768}}
    failed = response_record(truncated, pair, CAPS[0], 2.0)
    assert failed["format_status"] == "INCOMPLETE" and failed["finish_reason"] == "length"
    assert failed["teacher_final_content"] and not failed["student_target_eligible"]
    print("[PASS] paired teacher response separates reasoning/final/finish/usage; only final JSON is a possible student target; GPU NOT_RUN")


def execute(pairs: list[dict], source: dict) -> int:
    if V2_DIR.is_symlink() or any(path.exists() or path.is_symlink() for path in (OUT, MANIFEST)):
        raise FileExistsError("v2 budget probe already exists; preserve it and use a new stage")
    asset_preflight(hash_model=True)
    if _compute_apps():
        print("[HOLD] competing GPU compute process; no teacher started")
        return 8
    _, start_free = read_memory()
    if start_free < 8192:
        print(f"[HOLD] GPU free {start_free}MiB below 8192MiB; no teacher started")
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
        _, ready_free = read_memory()
        if ready_free < 2048:
            print(f"[GATE NEGATIVE] teacher-only free {ready_free}MiB below 2048MiB")
            return 8
        V2_DIR.mkdir(parents=True, exist_ok=True)
        rows: list[dict] = []
        with OUT.open("x", encoding="utf-8") as stream:
            for index, pair in enumerate(pairs):
                # Alternating order limits a fixed warmup/order explanation.
                order = CAPS if index % 2 == 0 else tuple(reversed(CAPS))
                for cap in order:
                    if time.monotonic() - begin >= WALL_LIMIT:
                        print("[GATE NEGATIVE] budget probe exceeded 520s before all eight requests")
                        return 8
                    payload = {"messages": translation_prompt(pair),
                               **MODEL_CARD_THINKING, "max_tokens": cap,
                               "seed": 1337 + index}
                    started = time.monotonic()
                    reply = _http_json(f"http://127.0.0.1:{port}/v1/chat/completions", key,
                                       payload, timeout=100)
                    row = response_record(reply, pair, cap, time.monotonic() - started)
                    rows.append(row)
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                    stream.flush()
                    print("[TEACHER_ROW] " + json.dumps({
                        "case": index + 1, "cap": cap, "finish_reason": row["finish_reason"],
                        "format_status": row["format_status"],
                        "reasoning_chars": row["reasoning_chars"], "final_chars": row["final_chars"],
                        "completion_tokens": row["usage"]["completion_tokens"],
                        "elapsed_sec": row["elapsed_sec"]}, sort_keys=True), flush=True)
        report = summarize(rows, source, time.monotonic() - begin)
        with MANIFEST.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
        print("[PASS] four paired format/finish-reason observations only; no student training or full16 gate")
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
        pairs, source = choose_pairs()
        if args.check_only:
            print(json.dumps({"source": source, "pairs": len(pairs),
                              "caps": CAPS, "ctx": CTX, "sampler": MODEL_CARD_THINKING,
                              "student_training": "NOT_RUN"}, sort_keys=True))
            print("[CHECK_ONLY] immutable v1 lineage and paired four-case design PASS; model/GPU NOT_RUN")
            return 0
        def time_limit(_signum, _frame):
            raise TimeoutError("P106B Stage1aWb hard wall 570s")
        prior = signal.signal(signal.SIGALRM, time_limit)
        signal.alarm(570)
        try:
            return execute(pairs, source)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, prior)
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        print(f"[FAIL] P106B Stage1aWb {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
