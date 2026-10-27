#!/usr/bin/env python3
"""Bounded P106 Prism inference with read-only, in-memory NVML sampling.

The model and installed runtime are never modified. This diagnoses runtime
placement/cost; it is not a teacher-quality or concurrent-training test.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "HF/models--prism-ml--Ternary-Bonsai-2-27B-gguf/Ternary-Bonsai-2-27B-PTQ1_0.gguf"
CLI = Path("/home/uranus/llama-prism-bin-ubuntu-x64-cuda133/llama-prism-b10743-adfffbe/llama-cli")
PROMPT = "Answer the arithmetic question 2+2. State the result as one digit."
FFN_FIRST32_PATTERN = r"blk\.([0-9]|[12][0-9]|3[01])\.ffn_(gate|up|down)\.weight"
FFN_FIRST32_BYTES = 1_871_708_160  # 96 unique GGUF tensors from llama-gguf metadata
FFN_FIRST60_PATTERN = r"blk\.([0-9]|[1-5][0-9])\.ffn_(gate|up|down)\.weight"
FFN_FIRST60_BYTES_EST = FFN_FIRST32_BYTES * 60 // 32  # equal FFN shapes; verify metadata before exact-byte claim


def parse_memory(line: str) -> tuple[int, int]:
    cells = [part.strip() for part in line.split(",")]
    if len(cells) != 2:
        raise ValueError("nvidia-smi memory row must have two fields")
    return int(cells[0]), int(cells[1])


def read_memory() -> tuple[int, int]:
    proc = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.free",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=5, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("nvidia-smi could not read GPU memory")
    return parse_memory(proc.stdout.splitlines()[0])


def fusion_trace_level_ok(require_fusion: bool, verbosity: int) -> bool:
    """An absent info-level 'enabled' line at verbosity 3 is NOT a negative result."""
    return not require_fusion or verbosity >= 4


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-layers", choices=["16", "40", "48", "56", "all"])
    parser.add_argument("--fit-off", action="store_true")
    parser.add_argument("--no-op-offload", action="store_true")
    parser.add_argument("--require-fusion", action="store_true")
    parser.add_argument("--ffn-cpu-first32", action="store_true")
    parser.add_argument("--ffn-cpu-first60", action="store_true")
    parser.add_argument("--verbosity", type=int, choices=[3, 4, 5], default=3)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        assert parse_memory("3251, 12811") == (3251, 12811)
        for bad in ("3251", "3251, x", "3251, 12811, 0"):
            try:
                parse_memory(bad)
            except ValueError:
                pass
            else:
                raise AssertionError("invalid NVML row accepted")
        pattern = re.compile(FFN_FIRST32_PATTERN)
        assert pattern.fullmatch("blk.0.ffn_gate.weight")
        assert pattern.fullmatch("blk.31.ffn_down.weight")
        assert not pattern.fullmatch("blk.32.ffn_gate.weight")
        assert not pattern.fullmatch("blk.0.ssm_out.weight")
        pattern60 = re.compile(FFN_FIRST60_PATTERN)
        assert pattern60.fullmatch("blk.59.ffn_down.weight")
        assert not pattern60.fullmatch("blk.60.ffn_up.weight")
        assert fusion_trace_level_ok(True, 4)
        assert fusion_trace_level_ok(False, 3)
        assert not fusion_trace_level_ok(True, 3)
        print("[PASS] P106 in-memory VRAM sampler parser; model/GPU NOT_RUN")
        return 0
    if args.gpu_layers is None:
        parser.error("--gpu-layers is required for runtime sampling")
    if not fusion_trace_level_ok(args.require_fusion, args.verbosity):
        parser.error("--require-fusion needs --verbosity 4 or 5; level 3 omits enabled evidence")
    if args.ffn_cpu_first32 and args.ffn_cpu_first60:
        parser.error("select exactly one FFN CPU override count")
    if (args.ffn_cpu_first32 or args.ffn_cpu_first60) and args.gpu_layers != "all":
        parser.error("FFN CPU override requires --gpu-layers all")
    if MODEL.is_symlink() or not MODEL.is_file() or CLI.is_symlink() or not CLI.is_file():
        print("[FAIL] exact model/Prism CLI missing or linked", file=sys.stderr)
        return 9
    try:
        before_used, before_free = read_memory()
    except (OSError, RuntimeError, ValueError, IndexError, subprocess.TimeoutExpired) as exc:
        print(f"[FAIL] GPU preflight: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9
    minimum_free = 10_240 if args.gpu_layers == "all" else 8_192
    if before_free < minimum_free:
        print(f"[HOLD] free VRAM {before_free}MiB < {minimum_free}MiB; no model started")
        return 8

    samples = [before_used]
    failures: list[str] = []
    stop = threading.Event()

    def sample() -> None:
        while not stop.wait(0.2):
            try:
                samples.append(read_memory()[0])
            except (OSError, RuntimeError, ValueError, IndexError, subprocess.TimeoutExpired) as exc:
                failures.append(type(exc).__name__)
                return

    cmd = [
        str(CLI), "--offline", "--simple-io", "--verbosity", str(args.verbosity),
        "--model", str(MODEL), "--gpu-layers", args.gpu_layers,
        "--ctx-size", "512", "--n-predict", "64", "--threads", "8",
        "--batch-size", "64", "--ubatch-size", "64", "--flash-attn", "auto",
        "--reasoning-effort", "medium", "--reasoning-budget", "16",
        "--temp", "0", "--top-p", "1", "--top-k", "0", "--min-p", "0",
        "--no-display-prompt", "--single-turn", "--no-warmup", "--prompt", PROMPT,
    ]
    if args.fit_off:
        cmd.extend(("--fit", "off"))
    if args.no_op_offload:
        cmd.append("--no-op-offload")
    if args.ffn_cpu_first32:
        cmd.extend(("--override-tensor", FFN_FIRST32_PATTERN + "=CPU"))
    if args.ffn_cpu_first60:
        cmd.extend(("--override-tensor", FFN_FIRST60_PATTERN + "=CPU"))
    print("[P106] bounded command:", " ".join(cmd), flush=True)
    worker = threading.Thread(target=sample, daemon=True)
    worker.start()
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    except subprocess.TimeoutExpired:
        stop.set()
        worker.join(timeout=6)
        print("[FAIL] model process timed out after 120s")
        return 9
    stop.set()
    worker.join(timeout=6)
    elapsed = time.monotonic() - started
    print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n")
    try:
        after_used, after_free = read_memory()
    except (OSError, RuntimeError, ValueError, IndexError, subprocess.TimeoutExpired):
        after_used, after_free = -1, -1
    peak_used = max(samples)
    combined_output = proc.stdout + proc.stderr
    fusion = {
        "gdn_ar_enabled": "fused Gated Delta Net (autoregressive) enabled" in combined_output,
        "gdn_ar_disabled": "fused Gated Delta Net (autoregressive) not supported, set to disabled" in combined_output,
        "gdn_chunked_enabled": "fused Gated Delta Net (chunked) enabled" in combined_output,
        "gdn_chunked_disabled": "fused Gated Delta Net (chunked) not supported, set to disabled" in combined_output,
    }
    report = {
        "schema": "P106_RUNTIME_VRAM_V1", "gpu_layers_requested": args.gpu_layers,
        "fit_off": args.fit_off, "op_offload": not args.no_op_offload,
        "verbosity": args.verbosity,
        "ffn_cpu_first32": args.ffn_cpu_first32,
        "ffn_first32_metadata_bytes": FFN_FIRST32_BYTES if args.ffn_cpu_first32 else 0,
        "ffn_cpu_first60": args.ffn_cpu_first60,
        "ffn_first60_metadata_bytes_est": FFN_FIRST60_BYTES_EST if args.ffn_cpu_first60 else 0,
        "baseline_used_mib": before_used, "baseline_free_mib": before_free,
        "peak_used_mib_sampled": peak_used,
        "peak_increment_mib_sampled": peak_used - before_used,
        "after_used_mib": after_used, "after_free_mib": after_free,
        "sample_count": len(samples), "sample_failures": failures,
        "wall_sec": round(elapsed, 3), "cli_exit": proc.returncode,
        "model_output_contains_digit_four": "\n4\n" in proc.stdout,
        "fusion": fusion,
        "limit": "0.2s global-GPU NVML samples can include other processes or miss a narrower peak; no concurrent TinyLM trainer",
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
    if (proc.returncode != 0 or failures or peak_used - before_used < 128
            or not report["model_output_contains_digit_four"]):
        print("[FAIL] runtime exit, synthetic answer, NVML sampler, or CUDA allocation contract")
        return 9
    if args.require_fusion and not (fusion["gdn_ar_enabled"] and fusion["gdn_chunked_enabled"]):
        print("[GATE NEGATIVE] requested GDN AR/chunked fusion was not both enabled")
        return 8
    print("[PASS] bounded process and sampled CUDA allocation; quality/concurrent training NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
