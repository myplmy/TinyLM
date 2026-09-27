#!/usr/bin/env python3
"""Bounded, no-checkpoint Bonsai/P076 concurrent-residency probe.

The student has the P076 B3 *shape and optimizer routing*, not its parent
weights, compiled graph, 16-way gradient accumulation, or dataset. Therefore
this can expose an OOM, but a successful run is not a full-training guarantee.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.diag_p106_vram_sample import (  # noqa: E402
    CLI, FFN_FIRST32_PATTERN, FFN_FIRST60_PATTERN, MODEL, parse_memory, read_memory,
)

SERVER = CLI.with_name("llama-server")
PYTHON = Path(sys.executable).resolve()


def _read_gpu() -> tuple[int, int]:
    return read_memory()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_json(url: str, key: str, payload: dict | None = None, timeout: float = 5) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    })
    with urlopen(request, timeout=timeout) as response:
        body = response.read(2_000_000)
        return json.loads(body) if body else {}


def _student(micro_bs: int) -> int:
    # No parent checkpoint, dataset, HF, cache, or output file is opened here.
    import torch

    from tinylm.config import build_config
    from tinylm.model.transformer import TiedMLPTransformer
    from tinylm.train.muon import Muon, split_params
    from tinylm.train.trainer import _ce_chunked

    torch.set_num_threads(1)
    torch.manual_seed(1337)
    cfg = build_config("m100R1c", "tied", 1024, False)
    cfg.attn_group = cfg.cla_group = 2
    model = TiedMLPTransformer(cfg).cuda()
    matrices, _ = split_params(model)
    matrix_ids = {id(param) for param in matrices}
    groups = []
    for group in model.param_groups(1e-3):
        params = [param for param in group["params"] if id(param) not in matrix_ids]
        if params:
            groups.append(dict(group, params=params))
    adamw = torch.optim.AdamW(groups, betas=(0.9, 0.95), eps=1e-8)
    muon = Muon(matrices, lr=4e-3, scale_mode="rms", weight_decay=0)
    x = torch.randint(0, cfg.vocab_size, (micro_bs, 1024), device="cuda")
    y = torch.randint(0, cfg.vocab_size, (micro_bs, 1024), device="cuda")
    torch.cuda.synchronize()
    model_reserved = torch.cuda.memory_reserved() // 2**20
    print(f"[STUDENT_READY] model_reserved_mib={model_reserved}", flush=True)
    if sys.stdin.readline().strip() != "GO":
        print("[FAIL] no GO signal; student update not started", flush=True)
        return 9
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    try:
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(x)
            loss = _ce_chunked(logits.reshape(-1, cfg.vocab_size), y.reshape(-1), 2048)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        adamw.step()
        muon.step()
        torch.cuda.synchronize()
        report = {
            "schema": "P106_P076_STUDENT_PROXY_V1",
            "step_count": 1, "micro_bs": micro_bs, "seq": 1024, "accum": 1,
            "architecture": "m100R1c tied, ag2, cla2, no activation checkpoint",
            "optimizer": "Muon RMS4 x4 matrices + AdamW others, matrix WD 0",
            "parent_init": "RANDOM_NOT_P076_PARENT", "compile": False,
            "data": "SYNTHETIC_IN_MEMORY", "checkpoint_write": False,
            "loss": float(loss.detach()),
            "model_reserved_mib": model_reserved,
            "peak_allocated_mib": torch.cuda.max_memory_allocated() // 2**20,
            "peak_reserved_mib": torch.cuda.max_memory_reserved() // 2**20,
            "wall_sec": round(time.monotonic() - started, 3),
        }
        print(json.dumps(report, sort_keys=True), flush=True)
        return 0
    except torch.cuda.OutOfMemoryError as exc:
        print(f"[GATE NEGATIVE] student synthetic update OOM: {exc}", flush=True)
        return 8


def _orchestrate(placement: str, micro_bs: int) -> int:
    if any(path.is_symlink() or not path.is_file() for path in (MODEL, SERVER)):
        print("[FAIL] exact local GGUF/server missing or linked", flush=True)
        return 9
    try:
        base_used, base_free = _read_gpu()
    except (OSError, ValueError, IndexError, RuntimeError) as exc:
        print(f"[FAIL] NVML preflight: {type(exc).__name__}: {exc}", flush=True)
        return 9
    # Teacher ~4 GiB + historical student reserved ~8.64 GiB + margin.
    if base_free < 14_000:
        print(f"[HOLD] starting GPU free {base_free}MiB < 14000MiB; no model started")
        return 8
    port = _free_port()
    key = secrets.token_hex(24)
    command = [
        str(SERVER), "--offline", "--model", str(MODEL),
        "--host", "127.0.0.1", "--port", str(port),
        "--api-key", key, "--no-webui", "--cors-origins", "localhost",
        "--no-cors-credentials", "--cache-ram", "0", "--verbosity", "4",
        "--ctx-size", "512", "--batch-size", "64", "--ubatch-size", "64",
        "--threads", "8", "--no-warmup", "--fit", "off",
        "--no-op-offload", "--gpu-layers", "all" if placement.startswith("ffn") else "40",
    ]
    if placement == "ffn32":
        command.extend(("--override-tensor", FFN_FIRST32_PATTERN + "=CPU"))
    if placement == "ffn60":
        command.extend(("--override-tensor", FFN_FIRST60_PATTERN + "=CPU"))
    # The random local API key is intentionally absent from runlog/stdout.
    print(f"[P106 COLOAD] placement={placement}, micro_bs={micro_bs}, "
          "offline localhost authenticated server, ctx512, no disk cache; "
          "synthetic P076 1-step; no checkpoint", flush=True)
    server = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, errors="replace", bufsize=1,
                              start_new_session=True)
    student: subprocess.Popen | None = None
    server_lines: list[str] = []
    student_lines: list[str] = []
    student_queue: queue.Queue[str] = queue.Queue()
    stop = threading.Event()
    samples = [base_used]
    sample_errors: list[str] = []
    teacher_reply: list[str] = []

    def drain_server() -> None:
        assert server.stdout is not None
        for line in server.stdout:
            if any(term in line for term in (
                    "resolve_fused_ops", "offloaded ", "model buffer size",
                    "listening on", "error", "failed", "API key")):
                server_lines.append(line.strip()[:500])

    def sample() -> None:
        while not stop.wait(0.2):
            try:
                samples.append(_read_gpu()[0])
            except (OSError, RuntimeError, ValueError, IndexError) as exc:
                sample_errors.append(type(exc).__name__)
                return

    def drain_student() -> None:
        assert student is not None and student.stdout is not None
        for line in student.stdout:
            student_lines.append(line.rstrip("\n"))
            student_queue.put(line)

    def request_teacher() -> None:
        try:
            response = _http_json(f"http://127.0.0.1:{port}/completion", key,
                                  {"prompt": "2+2=", "n_predict": 32, "temperature": 0},
                                  timeout=45)
            teacher_reply.append(f"completion_status=OK, content_chars={len(str(response.get('content', '')))}")
        except (OSError, HTTPError, URLError, ValueError) as exc:
            teacher_reply.append(f"completion_error={type(exc).__name__}: {exc}")

    threading.Thread(target=drain_server, daemon=True).start()
    threading.Thread(target=sample, daemon=True).start()
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if server.poll() is not None:
                print(f"[FAIL] teacher server exited early: {server.returncode}", flush=True)
                return 9
            try:
                _http_json(f"http://127.0.0.1:{port}/health", key, timeout=2)
                break
            except (OSError, HTTPError, URLError, ValueError):
                time.sleep(0.2)
        else:
            print("[FAIL] teacher server did not become ready within 45s", flush=True)
            return 9
        teacher_only_used = _read_gpu()[0]
        student = subprocess.Popen([str(PYTHON), "-B", "-X", "utf8", __file__,
                                    "--student", "--micro-bs", str(micro_bs)],
                                   cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, errors="replace",
                                   bufsize=1, start_new_session=True)
        threading.Thread(target=drain_student, daemon=True).start()
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if student.poll() is not None:
                print(f"[FAIL] student exited before ready: {student.returncode}", flush=True)
                return 9
            try:
                if "[STUDENT_READY]" in student_queue.get(timeout=0.25):
                    break
            except queue.Empty:
                pass
        else:
            print("[FAIL] synthetic student did not become ready within 60s", flush=True)
            return 9
        # Generation and synthetic backward/update overlap while both models remain loaded.
        generation = threading.Thread(target=request_teacher, daemon=True)
        generation.start()
        assert student.stdin is not None
        student.stdin.write("GO\n")
        student.stdin.flush()
        try:
            student.wait(timeout=120)
        except subprocess.TimeoutExpired:
            print("[FAIL] synthetic student exceeded 120s", flush=True)
            return 9
        generation.join(timeout=50)
        report = {
            "schema": "P106_P076_COLOAD_V1", "placement": placement,
            "student_micro_bs": micro_bs,
            "baseline_used_mib": base_used, "baseline_free_mib": base_free,
            "teacher_idle_increment_mib": teacher_only_used - base_used,
            "combined_peak_used_mib_sampled": max(samples),
            "combined_peak_increment_mib_sampled": max(samples) - base_used,
            "remaining_free_mib_sampled_est": base_free - (max(samples) - base_used),
            "sample_count": len(samples), "sample_errors": sample_errors,
            "student_exit": student.returncode,
            "teacher_exit_during_test": server.poll(),
            "teacher_generation": teacher_reply,
            "fusion": {
                "gdn_ar_enabled": any("fused Gated Delta Net (autoregressive) enabled" in line for line in server_lines),
                "gdn_chunked_enabled": any("fused Gated Delta Net (chunked) enabled" in line for line in server_lines),
            },
            "limits": "synthetic random-init eager one update, accum1; 0.2s global NVML samples; not P076 compiled 300M training or teacher-quality proof",
        }
        for line in server_lines[-24:]:
            print("[TEACHER]", line, flush=True)
        for line in student_lines[-24:]:
            print("[STUDENT]", line, flush=True)
        print(json.dumps(report, sort_keys=True), flush=True)
        if student.returncode == 8:
            print("[GATE NEGATIVE] both models loaded but student step OOM", flush=True)
            return 8
        if (student.returncode != 0 or sample_errors or server.poll() is not None
                or not any(item.startswith("completion_status=OK") for item in teacher_reply)):
            print("[FAIL] co-load process/sampler/generation contract", flush=True)
            return 9
        if not (report["fusion"]["gdn_ar_enabled"] and report["fusion"]["gdn_chunked_enabled"]):
            print("[GATE NEGATIVE] both fused GDN paths were not confirmed enabled", flush=True)
            return 8
        print("[PASS] bounded teacher generation + synthetic student update co-residency; full P076 training NOT_RUN", flush=True)
        return 0
    finally:
        stop.set()
        for process in (student, server):
            if process is not None and process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=8)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--placement", choices=("ffn32", "ffn60", "gpu40"))
    parser.add_argument("--student", action="store_true")
    parser.add_argument("--micro-bs", type=int, choices=(4, 8), default=8)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        assert parse_memory("1450, 14926") == (1450, 14926)
        assert SERVER.name == "llama-server"
        assert "ffn_(gate|up|down)" in FFN_FIRST32_PATTERN
        print("[PASS] P106 co-load CPU contract; model/GPU NOT_RUN")
        return 0
    if args.student:
        return _student(args.micro_bs)
    if args.placement is None:
        parser.error("--placement required for actual co-load")
    return _orchestrate(args.placement, args.micro_bs)


if __name__ == "__main__":
    raise SystemExit(main())
