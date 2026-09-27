#!/usr/bin/env python3
"""P106 Stage0pW: bounded full-GPU Bonsai + parent-initialized P076 resource gate.

User authorization is limited to this turn's two tiny synthetic-update arms.
No training dataset, SFT corpus, original cache, or checkpoint is written.
This probes co-residency and startup/step peaks, never teacher truth or SFT.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import platform
import queue
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.diag_p106_bonsai_assets import (  # noqa: E402
    MODEL, MODEL_SHA256, regular, sha256_file,
)
from scripts.diag_p106_coload import SERVER, _free_port, _http_json  # noqa: E402
from scripts.diag_p106_vram_sample import read_memory  # noqa: E402
from scripts.probe_p076_micro_accum import micro_indices  # noqa: E402

PARENT = ROOT / "runs/ckpt/m100_ko-en_300M_dense.pt"
SEQ = 1024
EFFECTIVE_TOKENS = 131_072


def _spec(micro_bs: int, accum: int, no_ckpt: bool) -> dict:
    if (micro_bs, accum, no_ckpt) not in ((4, 32, True), (8, 16, False)):
        raise ValueError("only approved micro4/accum32/no-ckpt or micro8/accum16/ckpt-on")
    indices = micro_indices(micro_bs, accum)
    return {"micro_bs": micro_bs, "accum": accum, "activation_checkpoint": not no_ckpt,
            "effective_tokens": EFFECTIVE_TOKENS, "micro_indices": indices}


def _compute_apps() -> list[str]:
    proc = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,process_name",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=5, check=False,
    )
    if proc.returncode:
        raise RuntimeError("cannot inspect competing GPU compute processes")
    return [row.strip() for row in proc.stdout.splitlines()
            if row.strip() and "No running processes" not in row]


def _preflight(spec: dict, *, real: bool) -> dict:
    if platform.system() != "Linux" or "microsoft" not in platform.release().lower():
        raise ValueError("P106 Stage0pW requires the selected WSL2 runtime")
    for path in (MODEL, SERVER, PARENT):
        if not regular(path):
            raise ValueError(f"exact input missing or linked: {path}")
    if MODEL.stat().st_size != 5_946_648_928 or PARENT.stat().st_size < 100_000_000:
        raise ValueError("GGUF/parent file size differs from pinned asset contract")
    if not os.access(SERVER, os.X_OK):
        raise ValueError("Prism llama-server is not executable")
    contract = {
        "schema": "P106_STAGE0PW_PREFLIGHT_V1",
        "student_micro_bs": spec["micro_bs"], "student_accum": spec["accum"],
        "activation_checkpoint": spec["activation_checkpoint"],
        "effective_tokens_per_update": EFFECTIVE_TOKENS,
        "teacher_placement": "GPU_ALL_NO_OP_OFFLOAD_FIT_OFF_CTX512",
        "student": "P076_M100R1C_AG2_CLA2_PARENT_COMPILE_MUON_RMS4",
        "data": "SYNTHETIC_IN_MEMORY", "checkpoint_write": False,
        "sft": "NOT_RUN",
    }
    if real:
        if sha256_file(MODEL) != MODEL_SHA256:
            raise ValueError("GGUF SHA differs from the pinned official PTQ1_0 asset")
        contract["parent_sha256"] = sha256_file(PARENT)
        apps = _compute_apps()
        if apps:
            raise RuntimeError("competing GPU compute processes: " + "; ".join(apps))
        used, free = read_memory()
        contract.update({"baseline_used_mib": used, "baseline_free_mib": free})
        if free < 14_000:
            raise MemoryError(f"starting free {free}MiB < 14000MiB; no model started")
    return contract


def _student(spec: dict) -> int:
    import torch
    from tinylm.config import build_config
    from tinylm.model.transformer import TiedMLPTransformer
    from tinylm.train.init_utils import init_from_dense
    from tinylm.train.muon import Muon, split_params
    from tinylm.train.optimizer_audit import matrix_decay_groups
    from tinylm.train.trainer import _ce_chunked

    if not torch.cuda.is_available():
        print("[HOLD] PyTorch CUDA unavailable before student model load", flush=True)
        return 8
    # Never share or overwrite the user's ordinary compiler cache.
    compile_dir = tempfile.mkdtemp(prefix="tinylm_p106_stage0pw_")
    os.environ["TORCHINDUCTOR_CACHE_DIR"] = compile_dir
    torch.set_num_threads(1)
    torch.manual_seed(1337)
    try:
        cfg = build_config("m100R1c", "tied", SEQ, spec["activation_checkpoint"])
        cfg.attn_group = cfg.cla_group = 2
        model = TiedMLPTransformer(cfg).cuda()
        init_from_dense(model, PARENT, "cuda", depth_init="prop", group_init="mean")
        model.set_anneal(0.0)  # first training-step branch, not quality evidence
        model = torch.compile(model, mode="default")
        base_groups, _ = matrix_decay_groups(model, 1e-3, 0)
        matrices, _ = split_params(model)
        matrix_ids = {id(param) for param in matrices}
        groups = []
        for group in base_groups:
            params = [param for param in group["params"] if id(param) not in matrix_ids]
            if params:
                groups.append(dict(group, params=params))
        adamw = torch.optim.AdamW(groups, betas=(0.9, 0.95), eps=1e-8)
        muon = Muon(matrices, lr=4e-3, scale_mode="rms", weight_decay=0)
        tokens = torch.randint(0, cfg.vocab_size, (8, SEQ + 1), device="cuda")
        x_all, y_all = tokens[:, :-1], tokens[:, 1:]
        torch.cuda.synchronize()
        print(f"[STUDENT_READY] micro={spec['micro_bs']} accum={spec['accum']} "
              f"ckpt={spec['activation_checkpoint']} reserved_mib={torch.cuda.memory_reserved() // 2**20} "
              f"compile_cache={compile_dir}", flush=True)
        if sys.stdin.readline().strip() != "GO":
            print("[FAIL] no GO signal; student update not started", flush=True)
            return 9
        steps = []
        for step in (1, 2):
            adamw.zero_grad(set_to_none=True)
            muon.zero_grad(set_to_none=True)
            torch.cuda.reset_peak_memory_stats()
            started = time.monotonic()
            for group in spec["micro_indices"]:
                x = x_all[group[0]:group[-1] + 1]
                y = y_all[group[0]:group[-1] + 1]
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    logits = model(x)
                    loss = _ce_chunked(logits.reshape(-1, cfg.vocab_size),
                                       y.reshape(-1), 2048) / spec["accum"]
                loss.backward()
            grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            if not math.isfinite(float(grad_norm)):
                raise RuntimeError("nonfinite synthetic gradient")
            adamw.step()
            muon.step()
            torch.cuda.synchronize()
            row = {"step": step, "wall_sec": round(time.monotonic() - started, 3),
                   "peak_allocated_mib": torch.cuda.max_memory_allocated() // 2**20,
                   "peak_reserved_mib": torch.cuda.max_memory_reserved() // 2**20,
                   "finite_gradient": True}
            steps.append(row)
            print("[STUDENT_STEP] " + json.dumps(row, sort_keys=True), flush=True)
        print(json.dumps({"schema": "P106_STAGE0PW_STUDENT_V1",
                          "micro_bs": spec["micro_bs"], "accum": spec["accum"],
                          "activation_checkpoint": spec["activation_checkpoint"],
                          "parent_init": PARENT.name, "compiled": True,
                          "effective_tokens_per_update": EFFECTIVE_TOKENS,
                          "steps": steps, "data": "SYNTHETIC_IN_MEMORY",
                          "checkpoint_write": False, "sft_quality": "NOT_RUN"},
                         sort_keys=True), flush=True)
        return 0
    except torch.cuda.OutOfMemoryError as exc:
        print(f"[GATE NEGATIVE] parent/compiled student setup or update CUDA OOM: {exc}", flush=True)
        return 8
    except Exception as exc:  # report exact compiler/runtime failure, never claim negative science
        print(f"[FAIL] student setup/update: {type(exc).__name__}: {exc}", flush=True)
        return 9


def _kill_group(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=8)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _looks_like_gpu_oom(lines: list[str]) -> bool:
    combined = "\n".join(lines).lower()
    return any(token in combined for token in (
        "cuda out of memory", "cuda_error_out_of_memory",
        "cudamalloc failed", "failed to allocate cuda",
    ))


def _orchestrate(spec: dict) -> int:
    try:
        contract = _preflight(spec, real=True)
    except MemoryError as exc:
        print(f"[HOLD] {exc}", flush=True)
        return 8
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"[FAIL] preflight: {type(exc).__name__}: {exc}", flush=True)
        return 9
    base_used = contract["baseline_used_mib"]
    base_free = contract["baseline_free_mib"]
    student: subprocess.Popen | None = None
    server: subprocess.Popen | None = None
    student_lines: list[str] = []
    server_lines: list[str] = []
    messages: queue.Queue[str] = queue.Queue()
    stop = threading.Event()
    sampled_used = [base_used]
    sample_errors: list[str] = []
    low_free_count = 0
    port = _free_port()
    key = secrets.token_hex(24)

    def sample() -> None:
        nonlocal low_free_count
        while not stop.wait(0.2):
            try:
                used, free = read_memory()
                sampled_used.append(used)
                low_free_count = low_free_count + 1 if free < 512 else 0
                if low_free_count >= 2:
                    sample_errors.append("FREE_LT_512_TWICE")
                    _kill_group(student)
                    return
            except (OSError, RuntimeError, ValueError, IndexError, subprocess.TimeoutExpired) as exc:
                sample_errors.append(type(exc).__name__)
                return

    def drain_student() -> None:
        assert student is not None and student.stdout is not None
        for line in student.stdout:
            value = line.rstrip("\n")
            student_lines.append(value)
            if len(student_lines) > 160:
                del student_lines[:80]
            messages.put(value)

    def drain_server() -> None:
        assert server is not None and server.stdout is not None
        for line in server.stdout:
            if any(term in line for term in ("fused Gated Delta Net", "offloaded ",
                                             "model buffer size", "error", "failed")):
                server_lines.append(line.strip()[:500])

    def print_student_tail() -> None:
        for line in student_lines[-24:]:
            print("[STUDENT]", line, flush=True)

    try:
        print("[P106 Stage0pW] parent-initialized compiled student first, then full-GPU "
              "offline authenticated teacher; no data/checkpoint write", flush=True)
        student = subprocess.Popen(
            [str(Path(sys.executable).resolve()), "-B", "-X", "utf8", __file__,
             "--student", "--micro-bs", str(spec["micro_bs"]),
             "--accum", str(spec["accum"]), *( ["--no-ckpt"] if not spec["activation_checkpoint"] else [])],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, errors="replace", bufsize=1,
            start_new_session=True,
        )
        threading.Thread(target=drain_student, daemon=True).start()
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if student.poll() is not None:
                print(f"[FAIL] student exited before ready: {student.returncode}", flush=True)
                print_student_tail()
                return 8 if student.returncode == 8 else 9
            try:
                if "[STUDENT_READY]" in messages.get(timeout=0.25):
                    break
            except queue.Empty:
                pass
        else:
            print("[FAIL] parent-initialized student setup exceeded 120s", flush=True)
            print_student_tail()
            return 9
        student_used = read_memory()[0]
        command = [
            str(SERVER), "--offline", "--model", str(MODEL),
            "--host", "127.0.0.1", "--port", str(port), "--api-key", key,
            "--no-webui", "--cors-origins", "localhost", "--no-cors-credentials",
            "--cache-ram", "0", "--verbosity", "4", "--ctx-size", "512",
            "--batch-size", "64", "--ubatch-size", "64", "--threads", "8",
            "--no-warmup", "--fit", "off", "--no-op-offload", "--gpu-layers", "all",
        ]
        server = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, errors="replace", bufsize=1,
                                  start_new_session=True)
        threading.Thread(target=drain_server, daemon=True).start()
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if server.poll() is not None:
                resource_oom = _looks_like_gpu_oom(server_lines)
                print(f"[{'GATE NEGATIVE' if resource_oom else 'FAIL'}] "
                      f"full teacher exited before health: {server.returncode}", flush=True)
                for line in server_lines[-24:]:
                    print("[TEACHER]", line, flush=True)
                return 8 if resource_oom else 9
            try:
                _http_json(f"http://127.0.0.1:{port}/health", key, timeout=2)
                break
            except (OSError, HTTPError, URLError, ValueError):
                time.sleep(0.25)
        else:
            print("[FAIL] full teacher health timeout after 60s", flush=True)
            return 9
        warm = _http_json(f"http://127.0.0.1:{port}/completion", key,
                          {"prompt": "2+2=", "n_predict": 16, "temperature": 0}, timeout=45)
        if not str(warm.get("content", "")).strip():
            print("[FAIL] full teacher warm response empty", flush=True)
            return 9
        ready_used, ready_free = read_memory()
        if ready_free < 6_000:
            print(f"[GATE NEGATIVE] only {ready_free}MiB free after student+teacher load", flush=True)
            return 8
        threading.Thread(target=sample, daemon=True).start()
        teacher_reports: list[str] = []

        def generate_during_step() -> None:
            for _ in range(32):
                if stop.is_set() or student is None or student.poll() is not None:
                    return
                try:
                    out = _http_json(f"http://127.0.0.1:{port}/completion", key,
                                     {"prompt": "2+2=", "n_predict": 16, "temperature": 0}, timeout=45)
                    teacher_reports.append("OK" if str(out.get("content", "")).strip() else "EMPTY")
                except (OSError, HTTPError, URLError, ValueError) as exc:
                    teacher_reports.append(type(exc).__name__)
                    return

        worker = threading.Thread(target=generate_during_step, daemon=True)
        worker.start()
        assert student.stdin is not None
        student.stdin.write("GO\n")
        student.stdin.flush()
        try:
            student.wait(timeout=360)
        except subprocess.TimeoutExpired:
            print("[FAIL] two tiny compiled student updates exceeded 360s", flush=True)
            print_student_tail()
            return 9
        stop.set()
        worker.join(timeout=50)
        report = {
            "schema": "P106_STAGE0PW_FULL_TEACHER_PANEL_V1",
            "student_micro_bs": spec["micro_bs"], "student_accum": spec["accum"],
            "activation_checkpoint": spec["activation_checkpoint"],
            "effective_tokens_per_update": EFFECTIVE_TOKENS,
            "baseline_used_mib": base_used, "baseline_free_mib": base_free,
            "student_ready_used_mib": student_used,
            "teacher_student_ready_used_mib": ready_used,
            "teacher_student_ready_free_mib": ready_free,
            "combined_peak_used_mib_sampled": max(sampled_used),
            "remaining_free_mib_sampled_est": base_free - (max(sampled_used) - base_used),
            "sample_count": len(sampled_used), "sample_errors": sample_errors,
            "teacher_generation_ok": teacher_reports.count("OK"),
            "teacher_generation_errors": [value for value in teacher_reports if value != "OK"],
            "student_exit": student.returncode, "server_exit_during_test": server.poll(),
            "fusion": {
                "gdn_ar_enabled": any("fused Gated Delta Net (autoregressive) enabled" in s for s in server_lines),
                "gdn_chunked_enabled": any("fused Gated Delta Net (chunked) enabled" in s for s in server_lines),
            },
            "parent_sha256": contract["parent_sha256"], "gguf_sha256": MODEL_SHA256,
            "limits": "two synthetic parent-initialized compiled updates, no real SFT/data/300M schedule; 0.2s global NVML samples may miss a narrower peak",
        }
        for line in student_lines[-14:]:
            if line.startswith(("[STUDENT_READY]", "[STUDENT_STEP]", "[GATE NEGATIVE]", "[FAIL]", "{")):
                print("[STUDENT]", line, flush=True)
        for line in server_lines[-12:]:
            print("[TEACHER]", line, flush=True)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
        if student.returncode == 8 or "FREE_LT_512_TWICE" in sample_errors:
            print("[GATE NEGATIVE] full-teacher co-residency has inadequate resource margin", flush=True)
            return 8
        if (student.returncode != 0 or sample_errors or server.poll() is not None
                or not teacher_reports or report["teacher_generation_errors"]):
            print("[FAIL] student/server/sampler/generation contract", flush=True)
            return 9
        if not all(report["fusion"].values()):
            print("[GATE NEGATIVE] full teacher GDN fusion was not confirmed", flush=True)
            return 8
        if report["remaining_free_mib_sampled_est"] < 2048:
            print("[GATE NEGATIVE] sampled free margin below preregistered 2GiB safety floor", flush=True)
            return 8
        print("[PASS] two tiny compiled co-resident updates and sampled margin; full SFT/long-run quality NOT_RUN", flush=True)
        return 0
    finally:
        stop.set()
        _kill_group(student)
        _kill_group(server)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--micro-bs", type=int, choices=(4, 8), default=4)
    parser.add_argument("--accum", type=int, default=32)
    parser.add_argument("--no-ckpt", action="store_true")
    parser.add_argument("--student", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            a = _spec(4, 32, True)
            b = _spec(8, 16, False)
            assert len(a["micro_indices"]) == 32 and len(b["micro_indices"]) == 16
            assert all(sum(i in group for group in a["micro_indices"]) == 16 for i in range(8))
            assert all(sum(i in group for group in b["micro_indices"]) == 16 for i in range(8))
            assert _looks_like_gpu_oom(["cudaMalloc failed for CUDA buffer"])
            assert not _looks_like_gpu_oom(["backend init failed: bad path"])
            try:
                _spec(8, 32, False)
            except ValueError:
                pass
            else:
                raise AssertionError("unapproved double effective batch accepted")
            print("[PASS] approved two-arm effective-batch/cleanup/preflight contract; model/GPU NOT_RUN")
            return 0
        spec = _spec(args.micro_bs, args.accum, args.no_ckpt)
        if args.check_only:
            print(json.dumps(_preflight(spec, real=False), sort_keys=True))
            print("[CHECK_ONLY] asset names/modes and approved arm; GPU/model/HF content NOT_READ")
            return 0
        if args.student:
            return _student(spec)
        return _orchestrate(spec)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"[FAIL] P106 Stage0pW: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
