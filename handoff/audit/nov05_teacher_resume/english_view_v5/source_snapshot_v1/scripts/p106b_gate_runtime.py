#!/usr/bin/env python3
"""Scoped public-data and one-teacher-server helpers for user-run P106B gates."""
from __future__ import annotations

from contextlib import contextmanager
import json
import math
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.diag_p106b_online_rate5 import (MODEL, MODEL_SHA256, SERVER, STUDENT,
    STUDENT_SHA256, TOKENIZER, TOKENIZER_SHA256, THINKING_SAMPLER, _compute_apps,
    _free_port, _http_json, _kill_group, read_memory, sample_memory,
    require_sampler_health, capture_server_line, public_source_jobs, ToolFailure,
    GateNegative, PrerequisiteHold)
from scripts.diag_p106_bonsai_assets import sha256_file, regular
from scripts.p106b_shards import verify

V17 = ROOT / "HF/sft_ready/p106b_teacher_sft/v17_online_public1_low"
V17_REPORT_SHA = "2206E86B1F4D4DB1B1F1F28C1479974371B7EBB4D3F454103DD1D134EEF5AE01"


def read_v17() -> tuple[list[dict], dict]:
    report_path = V17 / "online_public1_low_manifest.json"
    if not regular(report_path) or sha256_file(report_path) != V17_REPORT_SHA:
        raise PrerequisiteHold("exact Wg v17 report missing/changed")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (report.get("status") != "ONE_UPDATE_COMPLETE"
            or report.get("actually_trained_conversations") != 128
            or report.get("sample_errors")):
        raise PrerequisiteHold("Wg low1 technical prerequisite not passed")
    specs = {}
    for kind in ("raw", "canonical"):
        spec_path = V17 / f"{kind}_shards_manifest.json"
        if not regular(spec_path):
            raise ValueError(f"v17 {kind} shard manifest absent/linked")
        specs[kind] = json.loads(spec_path.read_text(encoding="utf-8"))
        verify(V17, specs[kind])
        if specs[kind]["concat_sha256"] != report[f"{kind}_concat_sha256"]:
            raise ValueError(f"v17 {kind} concat SHA differs")
    spec = specs["canonical"]
    if spec["concat_sha256"] != report["canonical_concat_sha256"]:
        raise ValueError("v17 canonical concat SHA differs")
    rows = [json.loads(line) for shard in spec["shards"]
            for line in (V17 / shard["path"]).read_text(encoding="utf-8").splitlines()]
    if len(rows) != 128:
        raise ValueError("v17 canonical row count differs")
    return rows, report


def fixed_jobs(concepts: int = 4) -> tuple[list[dict], dict]:
    jobs, source = public_source_jobs()
    result = [jobs[language][index] for index in range(concepts)
              for language in ("ko", "en")]
    return result, source


@contextmanager
def wall_limit(seconds: int):
    """Linux main-thread bound; owned server cleanup still runs on failure."""
    if not 60 <= seconds <= 21600:
        raise ValueError("gate wall limit outside 60..21600 seconds")
    previous = signal.getsignal(signal.SIGALRM)
    def alarm(*_args):
        raise ToolFailure(f"gate wall limit {seconds}s exceeded; partial evidence retained")
    signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def require_report(path: Path, schema: str, status: str) -> dict:
    if not regular(path):
        raise PrerequisiteHold(f"user prerequisite absent/linked: {path.relative_to(ROOT)}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("schema") != schema or report.get("status") != status:
        raise PrerequisiteHold(f"user prerequisite not passed: {path.relative_to(ROOT)}")
    return report


def new_directory(path: Path) -> None:
    if path.exists() or path.is_symlink() or path.parent.is_symlink():
        raise FileExistsError(f"preserve existing/linked output: {path}")


def student_inputs() -> dict:
    for path, expected in ((STUDENT, STUDENT_SHA256), (TOKENIZER, TOKENIZER_SHA256)):
        if not regular(path) or sha256_file(path) != expected:
            raise PrerequisiteHold(f"student input missing/changed: {path.name}")
    return {"parent_sha256": STUDENT_SHA256, "tokenizer_sha256": TOKENIZER_SHA256}


def code_contract(*names):
    paths = ("p106b_gate_runtime.py", "p106b_pipeline.py", "p106b_multi_answer.py") + tuple(names)
    return {name: sha256_file(ROOT / "scripts" / name) for name in paths}


def teacher_inputs():
    if not regular(SERVER) or not regular(MODEL):
        raise PrerequisiteHold("pinned teacher model/server missing/linked")
    return {"teacher_model_sha256": MODEL_SHA256, "server_sha256": sha256_file(SERVER)}


class TeacherSession:
    """One weight copy, explicit slots/context; never started by check-only."""
    def __init__(self, context: int, slots: int = 1, require_free: int = 2048, *,
                 effort: str = "low", thinking_budget: int | None = None):
        if effort not in {"low", "medium", "xhigh", "none"}:
            raise ValueError("unsupported teacher effort label")
        if thinking_budget is not None and (type(thinking_budget) is not int or thinking_budget <= 0):
            raise ValueError("positive numerical thinking budget required")
        self.context, self.slots, self.require_free = context, slots, require_free
        self.effort, self.thinking_budget = effort, thinking_budget
        self.port, self.key = _free_port(), __import__("secrets").token_hex(24)
        self.process = None
        self.stop = threading.Event()
        self.samples, self.errors, self.tail = [], [], []
        self.signals = {"gdn_ar_enabled": None, "gdn_chunked_enabled": None,
                        "kv_cache_space_warnings": 0, "attention_ubatch_failures": 0}
        self.workers = []

    def __enter__(self):
        if not regular(SERVER) or not regular(MODEL) or sha256_file(MODEL) != MODEL_SHA256:
            raise PrerequisiteHold("pinned Prism teacher binary/model absent or changed")
        command = [str(SERVER), "--offline", "--model", str(MODEL), "--host", "127.0.0.1",
                   "--port", str(self.port), "--api-key", self.key, "--no-webui",
                   "--cache-ram", "0", "--verbosity", "4", "--ctx-size", str(self.context),
                   "--parallel", str(self.slots), "--batch-size", "64", "--ubatch-size", "64",
                   "--threads", "8", "--no-warmup", "--fit", "off", "--no-op-offload",
                   "--gpu-layers", "all", "--reasoning", "auto"]
        try:
            self.process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                errors="replace", bufsize=1, start_new_session=True)
            def drain():
                for line in self.process.stdout:
                    capture_server_line(line, self.signals, self.tail, self.key)
            for target, args in ((drain, ()),
                                 (sample_memory, (self.stop, read_memory, self.samples, self.errors))):
                worker = threading.Thread(target=target, args=args, daemon=True)
                worker.start()
                self.workers.append(worker)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise ToolFailure("teacher server exited before health")
                try:
                    _http_json(self.url("/health"), self.key, timeout=3)
                    break
                except (OSError, ValueError):
                    time.sleep(0.25)
            else:
                raise ToolFailure("teacher health timeout")
            require_sampler_health(self.errors)
            if read_memory()[1] < self.require_free:
                raise GateNegative("teacher/student co-resident free below required margin")
            props = _http_json(self.url("/props"), self.key, timeout=5)
            if props.get("total_slots") != self.slots:
                raise ToolFailure("server did not confirm requested slot count; context contract unverified")
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def url(self, route: str) -> str:
        return f"http://127.0.0.1:{self.port}{route}"

    def count_prompt(self, messages: list[dict], per_slot_context: int, maximum: int, *, effort=None) -> dict:
        formatted = _http_json(self.url("/apply-template"), self.key,
                              {"messages": messages, "reasoning_effort": effort or self.effort}, timeout=10)
        if not isinstance(formatted.get("prompt"), str):
            raise ToolFailure("teacher applied template missing")
        encoded = _http_json(self.url("/tokenize"), self.key,
                             {"content": formatted["prompt"], "add_special": False,
                              "parse_special": True}, timeout=10)
        if not isinstance(encoded.get("tokens"), list):
            raise ToolFailure("teacher tokenize response missing")
        size = len(encoded["tokens"])
        return {"input_tokens": size, "context_per_slot": per_slot_context,
                "max_output": maximum, "reserve": 128,
                "decision": "DIRECT" if size + maximum + 128 <= per_slot_context else "COMPRESSION_REQUIRED"}

    def complete(self, messages: list[dict], seed: int, maximum: int, *, effort=None) -> dict:
        self.check_monitor()
        payload = {"messages": messages, **THINKING_SAMPLER,
                   "reasoning_effort": effort or self.effort, "max_tokens": maximum, "seed": seed}
        if self.thinking_budget is not None:
            payload["thinking_budget_tokens"] = self.thinking_budget
        reply = _http_json(self.url("/v1/chat/completions"), self.key,
            payload, timeout=max(240, 600 if maximum > 6144 else 240))
        self.check_monitor()
        return reply

    def check_monitor(self):
        require_sampler_health(self.errors)
        if self.process is not None and self.process.poll() is not None:
            raise ToolFailure("owned teacher exited during pipeline")

    def require_valid_resources(self):
        require_sampler_health(self.errors)
        if not self.samples:
            raise ToolFailure("no VRAM samples; resource gate unmeasured")
        if self.signals["gdn_ar_enabled"] is not True or self.signals["gdn_chunked_enabled"] is not True:
            raise GateNegative("GDN fusion not observed enabled; do not adopt slot/placement change")
        if read_memory()[1] < 512:
            raise GateNegative("co-resident free VRAM below 512MiB pilot stop margin")

    def evidence(self) -> dict:
        return {**self.signals, "sample_errors": list(self.errors),
                "sampled_global_used_peak_mib": max(self.samples) if self.samples else None,
                "server_error_tail": self.tail[-20:], "context_total": self.context,
                "slots": self.slots, "teacher_weights_copies": 1}

    def __exit__(self, *_args):
        self.stop.set()
        _kill_group(self.process)
        for worker in self.workers:
            worker.join(timeout=6)


class EffortView:
    """Per-request controls on one server; no weight duplication or shared mutation."""
    def __init__(self, session, effort):
        if effort not in {"low", "medium", "xhigh"}:
            raise ValueError("unknown paired-panel effort")
        self.session, self.effort = session, effort
        self.thinking_budget = session.thinking_budget
        self.key = session.key

    def count_prompt(self, messages, context, maximum):
        return self.session.count_prompt(messages, context, maximum, effort=self.effort)

    def complete(self, messages, seed, maximum):
        return self.session.complete(messages, seed, maximum, effort=self.effort)


def idle_before_gpu() -> None:
    if _compute_apps() or read_memory()[1] < 14000:
        raise PrerequisiteHold("GPU not idle/free >=14000MiB; no model started")


def write_report(path: Path, report: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


def disposition(exc: BaseException) -> tuple[str, int]:
    if isinstance(exc, KeyboardInterrupt):
        return "INTERRUPTED_USER", 130
    if isinstance(exc, (GateNegative, PrerequisiteHold)):
        return "GATE_NEGATIVE", 8
    if type(exc).__module__.startswith("torch") and type(exc).__name__ == "OutOfMemoryError":
        return "RESOURCE_OOM_NEGATIVE", 8
    return "TOOL_FAILURE", 9


def require_finite(values) -> None:
    if any(not math.isfinite(float(value)) for value in values):
        raise ToolFailure("nonfinite metric/loss; not a valid comparison")
