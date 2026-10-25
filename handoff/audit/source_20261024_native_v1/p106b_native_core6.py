#!/usr/bin/env python3
"""Opt-in native GGUF Core6; pure imports/check-only never start a worker.

Keep pinned TemplateLM encoding, plan_tokens and official tasks/metrics. Do not
use GGUFLM's implicit specials/empty-zero/unbounded-HTTP/slot-cache contract.
Native Q4/quantized CUDA kernels and per-request F32 KV are NOT HF FP32/noKV.
"""
from __future__ import annotations
import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import select
import struct
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_external_core6 as support
from scripts import diag_p106b_official_core6 as official
from scripts.p106b_official_lm_adapter import plan_tokens, token_ids

COMMIT = "2e7c58c5477478c8cf6e199cfaa5dcd5a4319c81"
HEADERS = ROOT / "data_cache/p106b_llama_eval_headers" / COMMIT
ENGINE = Path("/home/uranus/llama-b11396")
TAG = "p106b_native_gguf_core6_v1_s1337"
SCHEMA = "P106B_NATIVE_GGUF_CORE6_V1"
OUTPUT = ROOT / "test_result/evidence" / TAG
MAX_FRAME = 14_000_000
MAX_BYTES = 20_000_000
DEADLINE = datetime.fromisoformat("2026-10-24T08:40:00+09:00").timestamp()
ATOL, RTOL = official.ATOL, official.RTOL
REGISTRY = {
    "gpt2_q4km": dict(path="HF/benchmark_20261023/gpt2_q4km/gpt2-q4_k_m.gguf", architecture="gpt2",
        bytes=112858624, sha256="67027F93ACE5B0AF66C4FFCEEB529E556FACD9968E63C4F822D7B4A351E835E1",
        revision="f273bb57fe6ccad3d9ef415577a1b5c8d051544e"),
    "qwen35_08b_iq2xxs": dict(path="HF/benchmark_20261023/qwen35_08b_iq2xxs/Qwen3.5-0.8B-UD-IQ2_XXS.gguf",
        architecture="qwen35", bytes=338227456,
        sha256="A369165C8EC45A92D55CBAD98B5377E2C32CA8DFC824C899D9D05B33B6B53E54",
        revision="6ab461498e2023f6e3c1baea90a8f0fe38ab64d0"),
}
SOURCES = tuple(dict.fromkeys(("scripts/p106b_native_llama_worker.cpp", "scripts/p106b_native_core6.py",
    "scripts/test_p106b_native_core6.py", "scripts/diag_p106_full_coload_accum.py",
    "scripts/diag_p106b_teacher_tf.py", "scripts/diag_p106b_mtp_teacher.py",
    "scripts/diag_p106_vram_sample.py", "scripts/p106b_gemma_telemetry_resume.py") + support.SOURCES))
digest, read_json, write_json, close_report = support.digest, support.read_json, support.write_json, support.close_report
AdmissionHold = support.AdmissionHold


def policy():
    result = official.policy()
    result.update(batch_size=1, backend="EXACT_B11396_NATIVE_GGUF_CPP_LOGITS_IPC",
        precision="ORIGINAL_QUANTIZED_GGUF; NATIVE_KERNELS; FP32_LOGITS; F32_KV; FLASH_OFF; NOT_HF_FP32",
        use_cache=True, request_cache=False, logits_cache=False, tokenizer_cache=False,
        cache_scope="NATIVE_INTERNAL_PER_REQUEST_ONLY; CLEAR_DATA_AND_METADATA_BEFORE_AND_AFTER_EVERY_FORWARD",
        bos="NO_EXTRA_SPECIAL_FOR_NONEMPTY_CONTEXT; NATIVE_BOS_IF_VALID_ELSE_EOS_FOR_EMPTY",
        softmax_dtype="FP32_RAW_LOGITS; DOUBLE_EXP_LONG_DOUBLE_SUM; DOUBLE_LOGP",
        tf32="NATIVE_ENGINE_POLICY_NOT_HF_CONTROLLED",
        memory_queries="EXISTING_TIMEOUT_RETRY_V1; 3_ATTEMPTS_INCLUDING_FIRST; 5S_EACH; 0.2S_BETWEEN; GAPS_NOT_SAFE",
        native_parse_special=True, cross_choice_prefix_reuse=False,
        engine_commit=COMMIT, unsupported_models=["bonsai2_2b_ptq1"],
        gguFLM_not_adopted="implicit specials/empty zero/unbounded continuation/HTTP-per-token/slot cache",
        model_comparison="OFFICIAL_TASK_CONTRACT_ONLY; PRETRAINING_AND_ENGINE_PRECISION_NOT_MATCHED")
    return result


def identity():
    files = {name: digest(ROOT / name) for name in SOURCES}
    manifest = read_json(HEADERS / "headers_manifest.json")
    if manifest.get("commit") != COMMIT:
        raise AdmissionHold("exact header commit required")
    for name, item in manifest["files"].items():
        path = HEADERS / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise AdmissionHold("downloaded header/license pin differs: " + name)
        files[str(path.relative_to(ROOT))] = item["sha256"]
    for name in ("headers_manifest.json", "build_manifest.json"):
        files[str((HEADERS / name).relative_to(ROOT))] = digest(HEADERS / name)
    build = read_json(HEADERS / "build_manifest.json")
    if (build["commit"] != COMMIT or build["cpp_sha256"] != files["scripts/p106b_native_llama_worker.cpp"]
            or build["headers_manifest_sha256"] != digest(HEADERS / "headers_manifest.json")):
        raise AdmissionHold("worker was not compiled from the current source/exact headers")
    binary = HEADERS / build["worker"]
    if binary.parent != HEADERS or binary.is_symlink() or digest(binary) != build["worker_sha256"]:
        raise AdmissionHold("compiled worker pin differs")
    if digest(build["compiler_resolved_path"]) != build["compiler_sha256"]:
        raise AdmissionHold("compiler identity differs")
    actual_libraries = {path.name for path in ENGINE.glob("*.so*") if path.is_file() and not path.is_symlink()}
    if actual_libraries != set(build["libraries"]): raise AdmissionHold("native backend library set changed")
    actual_links = {path.name: os.readlink(path) for path in ENGINE.glob("*.so*") if path.is_symlink()}
    if actual_links != build["library_links"]: raise AdmissionHold("native library symlink mapping changed")
    if any(not (ENGINE / name).resolve().is_relative_to(ENGINE) for name in actual_links):
        raise AdmissionHold("native library link escaped the pinned engine directory")
    for name, sha in build["libraries"].items():
        if Path(name).name != name or (ENGINE / name).is_symlink() or digest(ENGINE / name) != sha:
            raise AdmissionHold("existing native library differs: " + name)
    files[str(binary.relative_to(ROOT))] = build["worker_sha256"]
    return dict(files=files, build=build, sha256=hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest().upper())


def asset_identity(model):
    spec = REGISTRY[model]
    path = ROOT / spec["path"]
    if path.is_symlink() or not path.is_file() or any(p.is_symlink() for p in path.parents):
        raise AdmissionHold("exact regular preregistered GGUF required")
    manifest = read_json(path.parent / "manifest.json")
    if (manifest.get("revision") != spec["revision"] or manifest.get("sha256", "").upper() != spec["sha256"]
            or manifest.get("bytes") != spec["bytes"] or path.stat().st_size != spec["bytes"] or digest(path) != spec["sha256"]):
        raise AdmissionHold("preregistered native model manifest/bytes/SHA differs")
    return dict(model=model, path=str(path), **{key: spec[key] for key in ("architecture", "revision", "bytes", "sha256")},
        acquisition_manifest_sha256=digest(path.parent / "manifest.json"))


def validate_execution(model, mode, deadline, cap, *, now=None):
    if model not in REGISTRY or mode not in {"canary", "cost", "full"}:
        raise AdmissionHold("explicit registered native model/phase required")
    parsed = datetime.fromisoformat(deadline)
    bounds = {"canary": (300, 600), "cost": (600, 600), "full": (60, 7200)}[mode]
    if parsed.tzinfo is None or type(cap) is not int or not bounds[0] <= cap <= bounds[1]:
        raise AdmissionHold("aware deadline and bounded whole phase required")
    now = time.time() if now is None else now
    stop = parsed.timestamp()
    if stop > DEADLINE or now + cap > stop:
        raise AdmissionHold("whole native phase does not fit authorized 08:40 deadline")
    return dict(deadline=parsed.isoformat(), deadline_epoch=stop, hard_cap_seconds=cap)


def prerequisites(model, mode, signature, assets):
    if mode == "canary":
        return {}
    common = dict(schema=SCHEMA, tag=TAG, model=model, source_identity=signature, assets=assets, policy=policy(), returncode=0)
    canary_path = OUTPUT / model / "canary/report.json"
    canary = read_json(canary_path)
    if (any(canary.get(k) != v for k, v in common.items()) or canary.get("status") != "NATIVE_CANARY_COMPLETE"
            or canary.get("mode") != "canary" or canary.get("numerical_canary", {}).get("passed") is not True):
        raise AdmissionHold("same-model/same-source closed native numerical canary required")
    result = dict(canary_report_sha256=digest(canary_path))
    if mode == "full":
        path = OUTPUT / model / "cost/report.json"
        cost = read_json(path)
        if (any(cost.get(k) != v for k, v in common.items()) or cost.get("status") != "NATIVE_LIMITED_COST_DIAGNOSTIC"
                or cost.get("mode") != "cost" or cost.get("actual_counts") != official.expected_counts("cost")
                or cost.get("raw_independent_recount") is not True
                or cost.get("prerequisites", {}).get("canary_report_sha256") != result["canary_report_sha256"]):
            raise AdmissionHold("same-model complete native cost evidence required")
        timing, startup = cost.get("task_evaluation_seconds", {}), cost.get("pre_evaluation_seconds")
        if set(timing) != set(official.TASK_COUNTS) or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in timing.values()):
            raise AdmissionHold("positive complete per-task native cost required")
        if type(startup) not in (int, float) or not math.isfinite(startup) or startup <= 0:
            raise AdmissionHold("measured native startup required")
        result.update(cost_report_sha256=digest(path), forecast_seconds=
            1.3 * sum(official.TASK_COUNTS[name] * value / 32 for name, value in timing.items()) + startup + 60,
            forecast_policy="PER_TASK_FIRST32_X1.3_PLUS_MEASURED_STARTUP_PLUS60; ESTIMATE_ONLY")
    return result


def ints(values):
    if any(type(v) is not int or not 0 <= v < 2**31 for v in values):
        raise ValueError("wire requires nonnegative int32 IDs")
    return struct.pack("<I", len(values)) + struct.pack("<" + "i" * len(values), *values)


class Reader:
    def __init__(self, data): self.data, self.position = data, 0
    def take(self, count):
        if count < 0 or self.position + count > len(self.data): raise ValueError("short worker response")
        value = self.data[self.position:self.position+count]; self.position += count; return value
    def unpack(self, fmt): return struct.unpack(fmt, self.take(struct.calcsize(fmt)))
    def u32(self): return self.unpack("<I")[0]
    def string(self): return self.take(self.u32())
    def end(self):
        if self.position != len(self.data): raise ValueError("trailing worker response bytes")


class Worker:
    def __init__(self, assets, build, stop, writer, proof):
        self.assets, self.build, self.stop, self.writer, self.proof = assets, build, stop, writer, proof
        self.process = None; self.request_id = 0; self.tail = []; self.thread = None
        self.sample_stop = threading.Event(); self.sampler = None; self.samples = []; self.telemetry_errors = []
        self.memory_reader = None; self.offload_lines = []; self.offload_line_count = 0

    def retrying_memory(self, source, *, emit=print):
        from scripts.p106b_gemma_telemetry_resume import RetryingMemoryReader
        def guarded():
            if self.sample_stop.is_set(): raise InterruptedError("native telemetry stopping")
            if self.process is not None and self.process.poll() is not None:
                raise ChildProcessError("owned native worker exited during memory observation")
            if time.time()+5 > self.stop: raise TimeoutError("native memory query cannot fit its 5s deadline budget")
            return source()
        return RetryingMemoryReader(guarded, emit=emit, pause=self.sample_stop.wait)

    def observe_memory(self, reader, rss_reader):
        start = time.monotonic()
        used, available = reader()
        if available < 512: raise MemoryError("native GPU free memory below 512MiB")
        if self.process.poll() is not None: raise ChildProcessError("owned native worker exited during sampling")
        rss = rss_reader(self.process.pid)
        if rss is None: raise ChildProcessError("owned native worker RSS disappeared")
        self.samples.append(dict(gpu_used_mib=used, gpu_free_mib=available, owned_rss_mib=rss,
            query_start_monotonic=start, query_end_monotonic=time.monotonic()))

    def sampling_error(self, error):
        expected_shutdown = self.sample_stop.is_set() and isinstance(error, (InterruptedError, ChildProcessError))
        if not expected_shutdown: self.telemetry_errors.append(type(error).__name__)

    def __enter__(self):
        began = time.monotonic()
        cmd = [str(HEADERS / self.build["worker"]), "--execute", self.assets["path"], self.assets["architecture"], str(self.stop)]
        env = dict(os.environ, LD_LIBRARY_PATH=str(ENGINE))
        self.proof.update(command=cmd, model_load_attempted=False, worker_cleanup_complete=False)
        try:
            from scripts.diag_p106_vram_sample import read_memory
            from scripts.diag_p106b_mtp_teacher import owned_rss
            self.memory_reader = self.retrying_memory(read_memory, emit=lambda line: print(line, flush=True))
            baseline, free = self.memory_reader()
            if free < 2048: raise AdmissionHold("native worker requires at least 2048MiB free before loading")
            self.proof["baseline_gpu_used_mib"] = baseline
            self.proof["model_load_attempted"] = True
            self.process = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, bufsize=0, start_new_session=True, env=env)
            self.proof["owned_pid"] = self.process.pid
            def drain():
                for line in self.process.stderr:
                    self.tail.append(line[:4000].decode("utf-8", "replace").rstrip())
                    del self.tail[:-200]
                    if "offload" in self.tail[-1].lower() or "buffer size" in self.tail[-1].lower():
                        self.offload_line_count += 1
                        if len(self.offload_lines) < 64: self.offload_lines.append(self.tail[-1])
            self.thread = threading.Thread(target=drain, daemon=True); self.thread.start()
            def sample():
                while not self.sample_stop.is_set():
                    try:
                        self.observe_memory(self.memory_reader, owned_rss)
                    except Exception as exc:
                        self.sampling_error(exc)
                        return
                    self.sample_stop.wait(.5)
            self.proof["sampling_started_at"] = datetime.now(timezone.utc).isoformat()
            self.sampler = threading.Thread(target=sample, daemon=True); self.sampler.start()
            reader = Reader(self.rpc(1))
            names = ("vocab_size", "training_context", "context", "n_batch", "n_ubatch", "bos_id", "eos_id")
            info = dict(zip(names, reader.unpack("<5I2i")))
            info.update(zip(("add_bos", "add_eos", "vocab_type"), reader.unpack("<3I")))
            info.update(zip(("parameters", "model_tensor_bytes"), reader.unpack("<2Q")))
            info.update(architecture=reader.string().decode(), gpu_backend=reader.string().decode())
            info.update(tokenizer_model=reader.string().decode(), tokenizer_pre=reader.string().decode())
            reader.end()
            if (info["architecture"] != self.assets["architecture"] or info["context"] != 1024
                    or info["training_context"] < 1024 or info["n_batch"] != 1024 or info["n_ubatch"] != 1024):
                raise AdmissionHold("native runtime identity/context differs")
            token_ids([info["eos_id"]], info["vocab_size"])
            info["prefix_id"] = info["bos_id"] if 0 <= info["bos_id"] < info["vocab_size"] else info["eos_id"]
            if self.assets["architecture"] == "gpt2" and (info["vocab_size"] != 50257 or info["eos_id"] != 50256 or info["prefix_id"] != 50256):
                raise AdmissionHold("GPT2 actual vocabulary/native prefix differs")
            self.info = info; self.proof.update(native_info=info, model_loaded=True, startup_seconds=time.monotonic()-began)
            self.observe_memory(self.memory_reader, owned_rss)
            return self
        except BaseException:
            try: self.close()
            except BaseException as cleanup: self.proof["cleanup_error"] = str(cleanup)[:1000]
            raise

    def transfer(self, fd, count=None, data=None, timeout=180):
        end = min(self.stop, time.time()+timeout); result = bytearray(); offset = 0
        while offset < (len(data) if data is not None else count):
            remaining = end-time.time()
            if remaining <= 0: raise TimeoutError("native IPC deadline exceeded")
            ready = select.select([] if data is not None else [fd], [fd] if data is not None else [], [], remaining)
            if not ready[0 if data is None else 1]: raise TimeoutError("native IPC timeout")
            if data is not None:
                step = os.write(fd, data[offset:offset+65536])
            else:
                block = os.read(fd, min(65536, count-offset))
                if not block: raise RuntimeError("owned native worker closed its pipe")
                result.extend(block); step = len(block)
            if step <= 0: raise RuntimeError("native IPC made no progress")
            offset += step
        return bytes(result)

    def rpc(self, op, payload=b"", timeout=180):
        if self.telemetry_errors: raise RuntimeError("native resource telemetry failed: " + repr(self.telemetry_errors))
        self.request_id += 1
        request = struct.pack("<II", op, self.request_id) + payload
        if len(request) > MAX_FRAME: raise ValueError("native request frame cap")
        self.writer.append(dict(event="native_request", id=self.request_id, op=op,
            wire_b64=base64.b64encode(request).decode("ascii")))
        self.transfer(self.process.stdin.fileno(), data=struct.pack("<I", len(request))+request, timeout=timeout)
        size = struct.unpack("<I", self.transfer(self.process.stdout.fileno(), 4, timeout=timeout))[0]
        if not 12 <= size <= MAX_FRAME: raise ValueError("native response frame cap")
        raw = self.transfer(self.process.stdout.fileno(), size, timeout=timeout)
        self.writer.append(dict(event="native_response", id=self.request_id, op=op,
            wire_b64=base64.b64encode(raw).decode("ascii")))
        reader = Reader(raw); actual_op, actual_id, status = reader.unpack("<III")
        if (actual_op, actual_id) != (op, self.request_id): raise ValueError("native response identity differs")
        if status:
            error = reader.string().decode("utf-8", "replace"); reader.end(); raise RuntimeError(error)
        return reader.take(len(raw)-reader.position)

    def tokenize(self, text, add_special=False):
        raw = text.encode("utf-8")
        if len(raw) > 1_000_000: raise ValueError("bounded UTF-8 tokenizer input required")
        reader = Reader(self.rpc(2, struct.pack("<II", 2+int(add_special), len(raw))+raw))
        count = reader.u32(); values = list(reader.unpack("<"+"i"*count)); reader.end()
        if values: token_ids(values, self.info["vocab_size"])
        return values

    def detokenize(self, ids):
        reader = Reader(self.rpc(5, ints(ids))); raw = reader.string(); reader.end(); return raw

    def score(self, plan):
        reader = Reader(self.rpc(3, ints(plan.input_ids)+struct.pack("<I", plan.target_start)+ints(plan.continuation_ids)))
        count = reader.u32(); total = reader.unpack("<d")[0]; greedy = reader.u32()
        per_token = [reader.unpack("<dI") for _ in range(count)]; reader.end()
        if (count != len(plan.continuation_ids) or greedy not in (0, 1)
                or any(g not in (0, 1) or not math.isfinite(p) or p > 0 for p, g in per_token)
                or not math.isfinite(total) or total > 0 or abs(total-math.fsum(p for p, _ in per_token)) > 1e-10
                or bool(greedy) != all(g for _, g in per_token)):
            raise ValueError("invalid complete native target likelihood")
        return (total, bool(greedy)), per_token

    def logits(self, input_ids, positions):
        reader = Reader(self.rpc(4, ints(input_ids)+ints(positions)))
        rows, vocab = reader.unpack("<II")
        if rows != len(positions) or vocab != self.info["vocab_size"]:
            raise ValueError("raw full-logits dimensions differ")
        raw = reader.take(rows*vocab*4); reader.end()
        return raw

    def close(self):
        self.sample_stop.set()
        if self.process is None:
            if self.memory_reader is not None: self.proof["telemetry"] = self.memory_reader.snapshot()
            return
        from scripts.diag_p106_full_coload_accum import _kill_group
        errors = []
        try:
            if self.process.poll() is None:
                try:
                    reader = Reader(self.rpc(6, timeout=2)); self.proof["native_memory_clear_calls"] = reader.unpack("<Q")[0]; reader.end()
                    self.process.wait(timeout=2)
                except BaseException as exc:
                    errors.append(type(exc).__name__)
                    if self.process.poll() is None:
                        if os.getpgid(self.process.pid) != self.process.pid: raise RuntimeError("worker process group ownership differs")
                        _kill_group(self.process)
                        self.process.wait(timeout=8)
        finally:
            self.sample_stop.set()
            if self.sampler is not None: self.sampler.join(timeout=6)
            if self.thread is not None: self.thread.join(timeout=2)
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream is not None: stream.close()
            self.proof.update(worker_returncode=self.process.poll(), worker_cleanup_complete=self.process.poll() is not None,
                cleanup_diagnostics=errors, worker_stderr_tail=self.tail, telemetry_errors=self.telemetry_errors,
                resource_sample_count=len(self.samples), sampling_ended_at=datetime.now(timezone.utc).isoformat(),
                resource_scope="0.5s GLOBAL_GPU_AND_OWNED_PID_RSS_SAMPLES; RETRY_GAPS_AND_CLEANUP_NOT_CONTINUOUSLY_OBSERVED",
                telemetry=self.memory_reader.snapshot() if self.memory_reader is not None else None,
                raw_offload_stderr=self.offload_lines, offload_line_count=self.offload_line_count,
                offload_scope="RAW_NATIVE_MESSAGES; NOT_BYTE_ACCURATE_PLACEMENT_PROOF")
            if self.samples:
                self.proof.update(sampled_gpu_peak_mib=max(row["gpu_used_mib"] for row in self.samples),
                    sampled_gpu_min_free_mib=min(row["gpu_free_mib"] for row in self.samples),
                    sampled_owned_worker_peak_rss_mib=max(row["owned_rss_mib"] for row in self.samples))

    def __exit__(self, error_type, *_):
        try: self.close()
        except BaseException as cleanup:
            self.proof["cleanup_error"] = str(cleanup)[:1000]
            if error_type is None: raise


def adapter_type(TemplateLM):
    class NativeLM(TemplateLM):
        backend = "causal"
        def __init__(self, worker):
            super().__init__(); self.worker = worker; self.vocab_size = worker.info["vocab_size"]
        @property
        def eot_token_id(self): return self.worker.info["eos_id"]
        @property
        def prefix_token_id(self): return self.worker.info["prefix_id"]
        @property
        def max_length(self): return 1024
        @property
        def batch_size(self): return 1
        @property
        def device(self): return "cpu"  # Harness bookkeeping; the external worker owns CUDA.
        @property
        def tokenizer_name(self): return "native-gguf-" + COMMIT
        def tok_encode(self, string, add_special_tokens=None, **kwargs):
            if kwargs: raise ValueError("unsupported native tokenizer kwargs")
            return self.worker.tokenize(string, bool(add_special_tokens))
        def loglikelihood(self, requests, **kwargs):
            requests = list(requests)
            if any(len(row.args) != 2 or any(type(value) is not str for value in row.args) or not row.args[1] for row in requests):
                raise ValueError("native Core6 requires explicit nonempty string continuations")
            return super().loglikelihood(requests, **kwargs)
        def _loglikelihood_tokens(self, requests, **kwargs):
            requests = list(requests)
            token_ids([self.eot_token_id, self.prefix_token_id], self.vocab_size)
            plans = [plan_tokens(ctx, cont, self.vocab_size, 1024) for _, ctx, cont in requests]
            return [self.worker.score(plan)[0] for plan in plans]
        def loglikelihood_rolling(self, requests, **kwargs): raise NotImplementedError("Core6 likelihood only")
        def generate_until(self, requests, **kwargs): raise NotImplementedError("No generation or chat path")
    return NativeLM


def compare(actual, expected):
    return support.compare_scores(actual, expected)


def numerical_canary(lm, torch):
    cases = [("Hello", " world!"), ("The answer is", " 42."), ("안녕", " 하세요."),
        ("", "Hello"), ("A ", "B"), ("un", "believable")]
    plans, encodings = [], []
    for context, continuation in cases:
        if context:
            ctx, cont = lm._encode_pair(context, continuation)
        else:
            cont = lm.tok_encode(continuation, add_special_tokens=False)
            ctx, cont = ([lm.prefix_token_id], cont) if cont[0] != lm.prefix_token_id else (cont[:1], cont[1:])
        plans.append(plan_tokens(ctx, cont, lm.vocab_size, 1024)); encodings.append(dict(context=ctx, continuation=cont))
        combined = context+continuation
        if lm.worker.detokenize(lm.tok_encode(combined)) != combined.encode("utf-8"):
            raise ValueError("native UTF-8 tokenize/detokenize roundtrip differs")
    results, checks = [], []
    for case, plan in zip(cases, plans):
        actual, per = lm.worker.score(plan)
        if len(plan.continuation_ids) > (MAX_FRAME-32)//(lm.vocab_size*4):
            raise ValueError("canary full-label logits exceed bounded wire frame")
        raw = lm.worker.logits(plan.input_ids, list(range(plan.target_start, len(plan.input_ids))))
        values = torch.frombuffer(bytearray(raw), dtype=torch.float32).reshape(-1, lm.vocab_size)
        labels = torch.tensor(plan.continuation_ids, dtype=torch.long)
        loss = torch.nn.functional.cross_entropy(values, labels, reduction="sum")
        direct = (-float(loss), bool(values.argmax(-1).eq(labels).all()))
        ce_check = compare([actual], [direct])
        single = []
        for index, target in enumerate(plan.continuation_ids, plan.target_start):
            one = plan_tokens(list(plan.input_ids[:index+1]), [target], lm.vocab_size)
            single.append(lm.worker.score(one)[0])
        single_check = compare([actual], [(math.fsum(row[0] for row in single), all(row[1] for row in single))])
        cold_check = compare([actual], [lm.worker.score(plan)[0]])
        # Change a later input token while leaving the observed prefix fixed.
        if len(plan.input_ids) >= 2:
            position = min(plan.target_start, len(plan.input_ids)-2)
            changed = list(plan.input_ids); changed[-1] = (changed[-1]+1) % lm.vocab_size
            before = lm.worker.logits(plan.input_ids, [position])
            after = lm.worker.logits(changed, [position])
            a = torch.frombuffer(bytearray(before), dtype=torch.float32)
            b = torch.frombuffer(bytearray(after), dtype=torch.float32)
            if not bool(torch.allclose(a, b, atol=ATOL, rtol=RTOL)):
                raise ValueError("native causal future-token invariance negative")
            future = dict(passed=True, max_absolute=float((a-b).abs().max()))
        else: future = dict(passed=True, scope="single input position; no future input exists")
        results.append(actual)
        checks.append(dict(arguments=list(case), full_label_ce=ce_check, single_prefix=single_check,
            cold_replay=cold_check, future_token=future, target_logps=[row[0] for row in per]))
    # Boundary: 1024 input tokens and the last two target logits, not 1024 output rows.
    ordinary = lm.tok_encode(" a")[0]
    boundary = plan_tokens([ordinary]*1030, [ordinary, ordinary], lm.vocab_size, 1024)
    if len(boundary.input_ids) != 1024 or boundary.truncated_context_tokens != 7:
        raise ValueError("1024 last(max+1) boundary differs")
    bscore = lm.worker.score(boundary)[0]
    replay = [lm.worker.score(plan_tokens(boundary.input_ids[:p+1], [target], lm.vocab_size))[0]
        for p, target in enumerate(boundary.continuation_ids, boundary.target_start)]
    boundary_check = compare([bscore], [(math.fsum(v[0] for v in replay), all(v[1] for v in replay))])
    # Literal native BOS/EOS roundtrip, no forced extra special on ordinary text.
    special = lm.worker.detokenize([lm.prefix_token_id]).decode("utf-8")
    if lm.tok_encode(special) != [lm.prefix_token_id]: raise ValueError("native special-token literal differs")
    return dict(passed=True, quality_claim=False, checks=checks, encodings=encodings,
        boundary_1024=boundary_check, boundary_truncated_context_tokens=boundary.truncated_context_tokens,
        boundary_input_tokens=1024, boundary_target_logits=2,
        special_literal=special, actual_prefix_id=lm.prefix_token_id, vocab_size=lm.vocab_size,
        atol=ATOL, rtol=RTOL, cache_contract=policy()["cache_scope"],
        independent_original_hf_tokenizer_equivalence="NOT_CLAIMED; NATIVE_GGUF_TOKENIZER_CONTRACT",
        forced_http_crosscheck="NOT_RUN; SEPARATE_OWNED_SERVER_REQUIRED")


def limited_http_canary(lm, request, cases):
    """Optional injected owned-server diagnostic; never called by cost/full."""
    from scripts.diag_p106b_teacher_tf import payload, probability_entry
    if not 1 <= len(cases) <= 4: raise ValueError("at most four explicit HTTP canary pairs")
    checks = []
    for context, continuation in cases:
        ctx, cont = lm._encode_pair(context, continuation)
        if not ctx or not cont: raise ValueError("nonempty bounded HTTP canary encoding required")
        parsed = probability_entry(request("/completion", payload(ctx, cont[0], 100)))
        if parsed["chosen"]["id"] != cont[0]: raise ValueError("HTTP canary target was not forced")
        native = lm.worker.score(plan_tokens(ctx, cont[:1], lm.vocab_size))[0]
        http_greedy = max(parsed["top"], key=lambda row: row["logprob"])["id"] == cont[0]
        compare([native], [(parsed["chosen"]["logprob"], http_greedy)])
        checks.append(dict(context_ids=ctx, target_id=cont[0], native=native[0], http=parsed["chosen"]["logprob"]))
    return dict(status="LIMITED_HTTP_DIAGNOSTIC_ONLY", checks=checks, quality_claim=False)


def evaluate_tasks(lm, target, report, tasks, mode):
    from lm_eval.evaluator import simple_evaluate
    from lm_eval.tasks import TaskManager
    from scripts.p106b_shards import ShardWriter
    counts, timing = official.expected_counts(mode), {}
    report.update(actual_counts={}, official_results={}, independent_audits={}, sample_manifests={},
        task_evaluation_seconds=timing, raw_independent_recount=False)
    lengths = ShardWriter(target, "token_lengths")
    try:
        with official.length_observer(lm, lengths) as summary:
            for name, task in tasks.items():
                began = time.monotonic()
                result = simple_evaluate(model=lm, tasks=[task], num_fewshot=0, task_manager=TaskManager(),
                    batch_size=1, device="cpu", use_cache=None, cache_requests=False, limit=32 if mode == "cost" else None,
                    bootstrap_iters=100000, log_samples=True, apply_chat_template=False, fewshot_as_multiturn=False,
                    random_seed=1337, numpy_random_seed=1337, torch_random_seed=1337, fewshot_random_seed=1337)
                timing[name] = time.monotonic()-began
                if set(result["samples"]) != {name}: raise ValueError("native official task identity differs")
                rows = result.pop("samples")[name]
                memory = official.audit_samples(task, rows, counts[name])
                writer = ShardWriter(target, name+"_samples")
                try:
                    for row in rows: writer.append(official.plain(row))
                finally:
                    if writer._total_rows:
                        manifest = writer.close(lineage=dict(tag=TAG, model=report["model"], task=name, mode=mode))
                        report["sample_manifests"][name] = manifest
                audit = support.recount_raw(task, target, manifest, counts[name])
                if any(audit[key] != value for key, value in memory.items()): raise ValueError("native raw disk recount differs")
                for metric, key in (("acc", "correct"), ("acc_norm", "correct_norm")):
                    score = result["results"][name].get(metric+",none")
                    if score is not None and not math.isclose(score, audit[key]/counts[name], abs_tol=1e-12):
                        raise ValueError("native official metric oracle negative")
                report["independent_audits"][name] = audit
                report["official_results"][name] = official.plain(result)
                report["actual_counts"][name] = counts[name]
                print(json.dumps(dict(event="NATIVE_TASK_CLOSED", model=report["model"], task=name,
                    mode=mode, rows=counts[name], seconds=timing[name]), sort_keys=True), flush=True)
            report["token_lengths_summary"] = summary
    finally:
        if lengths._total_rows: report["lengths_manifest"] = lengths.close(lineage=dict(tag=TAG, model=report["model"], mode=mode))
    choices = sum(a["choice_likelihoods"] for a in report["independent_audits"].values())
    if report["actual_counts"] != counts or mode == "full" and (sum(counts.values()) != 19965 or choices != 67106):
        raise ValueError("native official denominator/complete choices differ")
    report.update(choice_likelihoods=choices, raw_independent_recount=True, evaluation_seconds=sum(timing.values()))


def execute(model, mode, expected_source, deadline, cap):
    signature = identity()
    if signature["sha256"] != expected_source: raise AdmissionHold("native source/build/library identity differs")
    admission = validate_execution(model, mode, deadline, cap)
    target = OUTPUT / model / mode
    if target.exists() or target.is_symlink() or any(p.is_symlink() for p in target.parents):
        raise FileExistsError("existing complete/partial native output is preserved")
    target.mkdir(parents=True, exist_ok=False)
    report = dict(schema=SCHEMA, tag=TAG, model=model, mode=mode, status="STARTED", returncode=9,
        source_identity=signature, policy=policy(), admission=admission, quality_claim=False,
        training=False, optimizer_updates=0, checkpoint_writes=0, started_at=datetime.now(timezone.utc).isoformat())
    began = time.monotonic(); primary = None; writer = None
    try:
        # Reserve 30 seconds of the admitted whole-phase cap for evidence closure.
        with support.phase_wall_limit(cap-30):
            assets = asset_identity(model); report["assets"] = assets
            pre = prerequisites(model, mode, signature, assets); report["prerequisites"] = pre
            support.admit_forecast(pre, admission)
            for key, value in official.OFFLINE.items(): os.environ[key] = value
            import tinylm
            from scripts.prepare_p106b_official_eval import configure_hf_cache, COMMIT as HARNESS_COMMIT, MANIFEST_SHA
            configure_hf_cache()
            from scripts.p106b_official_tasks import load_tasks
            tasks, specs, provenance = load_tasks()
            report.update(task_specs=specs, framework_provenance=provenance,
                framework_commit=HARNESS_COMMIT, data_manifest_sha256=MANIFEST_SHA)
            from scripts.interactive_research_infer import require_idle_gpu
            report["gpu_idle_before_model"] = require_idle_gpu()
            support.admit_forecast(pre, admission)
            if time.time()+30 >= admission["deadline_epoch"]: raise AdmissionHold("native startup deadline margin insufficient")
            from scripts.p106b_shards import ShardWriter, verify
            from lm_eval.api.model import TemplateLM
            import torch
            torch.set_num_threads(4)
            writer = ShardWriter(target, "native_wire")
            proof = {}; report["model_proof"] = proof
            with Worker(assets, signature["build"], min(admission["deadline_epoch"]-30, time.time()+cap-(time.monotonic()-began)-30), writer, proof) as worker:
                lm = adapter_type(TemplateLM)(worker)
                report["numerical_canary"] = numerical_canary(lm, torch)
                report["pre_evaluation_seconds"] = time.monotonic()-began
                if mode != "canary": evaluate_tasks(lm, target, report, tasks, mode)
            if not proof.get("worker_cleanup_complete") or proof.get("worker_returncode") != 0:
                raise ValueError("native owned worker did not close cleanly")
            if proof.get("telemetry_errors") or not proof.get("resource_sample_count"):
                raise ValueError("native resource measurement did not close completely")
            report["gpu_idle_after_worker"] = require_idle_gpu()
            if asset_identity(model) != assets: raise ValueError("native model source changed during evaluation")
            report["source_assets_unchanged"] = True
            if identity() != signature: raise ValueError("native source changed during evaluation")
            report.update(status={"canary": "NATIVE_CANARY_COMPLETE", "cost": "NATIVE_LIMITED_COST_DIAGNOSTIC",
                "full": "NATIVE_OFFICIAL_CORE6_FULL_COMPLETE"}[mode], returncode=0)
    except BaseException as exc:
        primary = exc
        report.update(status="NATIVE_PREREQUISITE_HOLD" if isinstance(exc, AdmissionHold) else "NATIVE_EVALUATION_ERROR",
            error_type=type(exc).__name__, error=str(exc)[:2000])
        raise
    finally:
        try:
            if writer is not None and writer._total_rows:
                manifest = writer.close(lineage=dict(tag=TAG, model=model, mode=mode)); report["wire_manifest"] = manifest
                from scripts.p106b_shards import verify
                verify(target, manifest)
            report["sources_unchanged"] = identity() == signature
            if report["returncode"] == 0 and not report["sources_unchanged"]: raise ValueError("native source changed before report closure")
        except BaseException as closure:
            report.update(status="NATIVE_EVALUATION_ERROR", returncode=9, closure_verification_error=str(closure)[:1000])
            if primary is None: primary = closure
        report.update(ended_at=datetime.now(timezone.utc).isoformat(), wall_seconds=time.monotonic()-began)
        if report["returncode"] == 0 and (report["wall_seconds"] > cap or time.time() >= admission["deadline_epoch"]):
            primary = TimeoutError("native evidence closure exceeded admitted whole-phase cap/deadline")
            report.update(status="NATIVE_EVALUATION_ERROR", returncode=9, error_type="TimeoutError", error=str(primary))
        close_report(target / "report.json", report, primary_error=primary)
    if primary is not None: raise primary
    return {key: report[key] for key in ("status", "model", "mode", "wall_seconds")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(); group.add_argument("--check-only", action="store_true"); group.add_argument("--execute", action="store_true")
    parser.add_argument("--model", choices=tuple(REGISTRY)); parser.add_argument("--mode", choices=("canary", "cost", "full"))
    parser.add_argument("--source-sha256"); parser.add_argument("--deadline"); parser.add_argument("--max-wall-sec", type=int)
    args = parser.parse_args(argv)
    if args.execute:
        if any(getattr(args, name) is None for name in ("model", "mode", "source_sha256", "deadline", "max_wall_sec")):
            parser.error("execute requires explicit model/mode/source/deadline/whole-wall bounds")
        result = execute(args.model, args.mode, args.source_sha256, args.deadline, args.max_wall_sec)
    else:
        result = dict(status="SOURCE_ONLY", models=0, backend_initializations=0, tag=TAG,
            source_identity=identity(), policy=policy(), registry=REGISTRY)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
