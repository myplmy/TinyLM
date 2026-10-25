#!/usr/bin/env python3
"""분리된 Gemma V3 자원 관측기. 모델 실행은 총괄만 수행한다.

기존 14000MiB 입장 gate와 생산 코드는 바꾸지 않는다. 11264MiB는 과거
표본 peak와 2048MiB 여유를 올림한 임시 입장 예산이며 미래 OOM 보증이 아니다.
내부 기본 590초, 외부 595초 TERM 뒤 5초 KILL로 총 600초를 제한해야 한다.
부모 SIGKILL 이후 전체 자손의 회수는 보장하지 않는다.
"""
from __future__ import annotations

import time
STARTED = time.monotonic()

import argparse
import ast
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
from unittest.mock import patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[3]
ENTRY = "handoff/audit/oct26_research/probe_gemma_capacity.py"
TEST = "scripts/test_p106b_gemma_capacity_probe.py"
PREFIX = "p106b_gemma_capacity_v1_20261026_"
SCHEMA = "P106B_GEMMA_CAPACITY_PROBE_V1"
END = datetime(2026, 10, 26, 8, tzinfo=timezone.utc)
MAX_BYTES = 20_000_000
ADMISSION_MIB = 11264
MAX_GENERATIONS = 4
SEEDS = (
    ENTRY, TEST, "scripts/diag_p106b_supported_supervisor.py",
    "scripts/p106b_gemma_teacher.py", "scripts/p106b_gemma_task_contract_v3.py",
    "scripts/diag_p106b_supported_production8h.py", "scripts/p106b_memory_stream.py",
    "scripts/p106b_http_errors.py",
)


class Hold(FileNotFoundError):
    """모델 시작 전 자원 선결 보류."""


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest().upper()


def regular(name, root=ROOT):
    name = Path(name)
    require(not name.is_absolute() and ".." not in name.parts
            and name.parts[:2] != ("datasets", "TinyDataset"), "정확한 로컬 상대 경로가 필요하다")
    path = Path(root) / name
    require(path.is_file() and not path.is_symlink()
            and not any(p.is_symlink() for p in path.parents), "일반 소스 파일이 필요하다")
    require(path.stat().st_size < MAX_BYTES, "소스 파일 20MB 상한을 넘었다")
    return path


def production_addendum(root=ROOT):
    tree = ast.parse(regular("scripts/diag_p106b_supported_production8h.py", root).read_text(encoding="utf-8"))
    scope = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "scope")
    payload = next(n for n in ast.walk(scope) if isinstance(n, ast.FunctionDef) and n.name == "payload")
    changes = [n for n in ast.walk(payload) if isinstance(n, ast.AugAssign)]
    require(len(changes) == 1 and isinstance(changes[0].op, ast.Add)
            and ast.dump(changes[0].target) == ast.dump(ast.parse('result["messages"][0]["content"] += ""').body[0].target),
            "원 생산기의 추가 system 경로가 달라졌다")
    value = ast.literal_eval(changes[0].value)
    require(isinstance(value, str) and value, "원 생산기 추가 지시문이 없다")
    return value


def workload():
    """원자료 취득 없이 자원 형상만 관찰하는 한영 QA/JSON 네 요청."""
    cases = []
    for language in ("ko", "en"):
        text = ("가상 자료에서 가람은 파란 상자를, 누리는 빨간 상자를 맡는다."
                if language == "ko" else
                "In this fictional reference, Mina owns the blue box and Jin owns the red box.")
        row = dict(messages=[dict(role="user", content=text)], meta=dict(
            source_repo="CODE_AUTHORED_CAPACITY_FIXTURE", source_revision="V1",
            source_id="capacity:" + language, source_family="RESOURCE_FIXTURE",
            source_license="CODE_AUTHORED", language=language,
            source_sha256=hashlib.sha256(text.encode()).hexdigest().upper()))
        for task in ("qa", "json"):
            cases.append(dict(id=language + "_" + task, source=row,
                              language=language, task=task, seed=1337 + len(cases)))
    return cases


def source_identity(root=ROOT):
    """로컬 코드만 고정한다. import, 모델, GPU, 원자료 접근은 하지 않는다."""
    pending, files = list(SEEDS), {}
    while pending:
        name = pending.pop()
        if name in files:
            continue
        path = regular(name, root)
        raw = path.read_bytes()
        files[name] = hashlib.sha256(raw).hexdigest().upper()
        tree = ast.parse(raw.decode("utf-8"))
        package = list(Path(name).parts[:-1])
        modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name.split(".") for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                prefix = package[:len(package) - node.level + 1] if node.level else []
                base = prefix + (node.module.split(".") if node.module else [])
                modules.append(base)
                modules.extend(base + alias.name.split(".") for alias in node.names if alias.name != "*")
        for parts in modules:
            if parts and parts[0] in ("scripts", "tinylm"):
                for relative in (str(Path(*parts)) + ".py", str(Path(*parts) / "__init__.py")):
                    if (Path(root) / relative).is_file() and relative not in files:
                        pending.append(relative)
        require(len(files) < 1000, "예상하지 않은 소스 의존 범위다")
    protocol = dict(schema=SCHEMA, admission_mib=ADMISSION_MIB, generations=MAX_GENERATIONS,
                    context=8192, thinking=1024, max_output=3072, mtp=True,
                    max_wall_sec=600, default_wall_sec=590, reserve_sec=60,
                    absolute_deadline=END.isoformat(), workload_sha256=digest(workload()),
                    addendum_sha256=hashlib.sha256(production_addendum(root).encode()).hexdigest().upper())
    identity = dict(protocol=protocol, files=dict(sorted(files.items())))
    return dict(sha256=digest(identity), **identity)


def supervisor():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts import diag_p106b_supported_supervisor
    return diag_p106b_supported_supervisor


def timed_write(path, value, budget):
    budget.check("새 파일 저장 전")
    raw = canonical(value) + b"\n"
    require(len(raw) < MAX_BYTES, "새 파일 20MB 상한을 넘었다")
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(Path(path).read_bytes() == raw, "저장 후 재읽기가 다르다")
    budget.check("새 파일 저장과 재읽기 후")


def read_json(path):
    raw = Path(path).read_bytes()
    require(len(raw) < MAX_BYTES, "증거 파일 20MB 상한을 넘었다")
    value = json.loads(raw)
    canonical(value)
    return value


def gpu_snapshot(budget, *, runner=subprocess.run):
    """기존 공통 gate를 호출하지 않는 별도 진단 입장 조회."""
    budget.check("입장 계측 전")
    timeout = min(5., budget.remaining() - budget.reserve)
    require(timeout > 0, "입장 조회 뒤 정리 시간이 없다")
    memory = runner(["nvidia-smi", "--id=0", "--query-gpu=memory.used,memory.free",
                     "--format=csv,noheader,nounits"], capture_output=True, text=True,
                    timeout=timeout, check=False)
    require(memory.returncode == 0, "입장 GPU 메모리 조회가 실패했다")
    lines = [line for line in memory.stdout.splitlines() if line.strip()]
    require(len(lines) == 1, "GPU 0의 단일 계측이 필요하다")
    cells = [p.strip() for p in lines[0].split(",")]
    require(len(cells) == 2 and all(p.isdecimal() for p in cells), "유한한 MiB 정수 두 값이 필요하다")
    used, free = map(int, cells)
    timeout = min(5., budget.remaining() - budget.reserve)
    require(timeout > 0, "경쟁 프로세스 조회 시간이 없다")
    apps = runner(["nvidia-smi", "--id=0", "--query-compute-apps=pid,process_name",
                   "--format=csv,noheader,nounits"], capture_output=True, text=True,
                  timeout=timeout, check=False)
    require(apps.returncode == 0, "경쟁 GPU 프로세스 조회가 실패했다")
    active = [line.strip() for line in apps.stdout.splitlines()
              if line.strip() and "No running processes" not in line]
    budget.check("입장 계측 후")
    return dict(used_mib=used, free_mib=free, compute_apps=active,
                monotonic=time.monotonic(), gpu_index=0)


def admit(snapshot):
    if snapshot["compute_apps"]:
        raise Hold("기존 GPU compute 프로세스가 있어 시작하지 않는다")
    if snapshot["free_mib"] < ADMISSION_MIB:
        raise Hold("임시 입장 여유 11264MiB가 부족하다")


def production_payload(case, *, tasks=None, root=ROOT):
    if tasks is None:
        from scripts import p106b_gemma_task_contract_v3 as tasks
    payload = tasks.payload(case["source"], case["language"], case["task"], case["seed"])
    payload["messages"][0]["content"] += production_addendum(root)
    require(payload["max_tokens"] == 3072 and payload["thinking_budget_tokens"] == 1024
            and payload["cache_prompt"] is False, "원 생산 요청의 자원 형상이 달라졌다")
    return payload


class Requests:
    """생성 시도 수와 원답을 보존하고 나머지 HTTP 경로는 별도로 센다."""
    def __init__(self, directory, budget, stop_file):
        self.directory, self.budget, self.stop_file = Path(directory), budget, Path(stop_file)
        self.generations = 0
        self.routes = {}
        self.replies = []
        self.metrics = []
        self.events = []

    def limit(self, timeout):
        self.budget.check("HTTP 전")
        if self.stop_file.exists():
            raise TimeoutError("부모 STOP 이후에는 요청하지 않는다")
        remaining = self.budget.remaining() - self.budget.reserve - 20.
        require(remaining > 0, "요청 뒤 정리 예약이 부족하다")
        require(math.isfinite(timeout) and timeout > 0, "유한한 요청 제한이 필요하다")
        return min(float(timeout), 300., remaining)

    def call(self, session, original, route, payload=None, timeout=10):
        timeout = self.limit(timeout)
        require(route in ("/health", "/props", "/apply-template", "/tokenize", "/v1/chat/completions"),
                "허용된 진단 HTTP 경로가 아니다")
        generation = route == "/v1/chat/completions"
        if generation:
            require(self.generations < MAX_GENERATIONS, "생성 HTTP 네 번 상한을 넘었다")
            self.generations += 1
        self.routes[route] = self.routes.get(route, 0) + 1
        began = time.monotonic()
        event = dict(route=route, generation=generation, timeout_sec=timeout,
                     generation_index=self.generations if generation else None)
        try:
            reply = original(session, route, payload, timeout)
            event["wall_sec"] = time.monotonic() - began
            if generation:
                value = dict(index=self.generations, payload=payload, reply=reply,
                             request_wall_sec=event["wall_sec"])
                try:
                    canonical(value)
                except (ValueError, TypeError):
                    value = dict(index=self.generations, payload=payload,
                                 invalid_reply_json=json.dumps(reply, ensure_ascii=False, allow_nan=True),
                                 request_wall_sec=event["wall_sec"], finite_reply=False)
                    timed_write(self.directory / f"raw_{self.generations:02d}.json", value, self.budget)
                    raise ValueError("비유한 원답을 문자열로 보존했다")
                timed_write(self.directory / f"raw_{self.generations:02d}.json", value, self.budget)
                self.replies.append(reply)
                from scripts.p106b_mtp_teacher import response_metrics
                metric = response_metrics(reply, event["wall_sec"])
                require(metric["completion_tokens"] > 0, "응답의 실제 completion 토큰 계측이 필요하다")
                self.metrics.append(metric)
            self.budget.check("HTTP 응답 저장 후")
            if self.stop_file.exists():
                raise TimeoutError("요청 중 부모 STOP이 게시됐다")
            return reply
        except HTTPError as error:
            from scripts.p106b_http_errors import capture_http_error
            evidence = capture_http_error(error, session.key)
            timed_write(self.directory / f"http_error_{self.generations:02d}.json",
                        dict(route=route, evidence=evidence, whole_body_preserved=False), self.budget)
            event["error"] = dict(type=type(error).__name__, http_status=error.code)
            raise
        except BaseException as error:
            event["error"] = dict(type=type(error).__name__)
            raise
        finally:
            self.events.append(event)
            self.events = self.events[-1024:]

    @contextmanager
    def scope(self, lifecycle):
        original = lifecycle.Session.request
        def bounded(session, route, payload=None, timeout=10):
            return self.call(session, original, route, payload, timeout)
        with patch.object(lifecycle.Session, "request", bounded):
            yield


def validate_memory(memory):
    required = ("sample_count", "sampled_gpu_global_peak_mib", "sampled_gpu_min_free_mib",
                "baseline_gpu_used_mib", "owned_server_peak_rss_mib")
    require(all(k in memory and isinstance(memory[k], (int, float))
                and not isinstance(memory[k], bool) and math.isfinite(memory[k])
                and memory[k] >= 0 for k in required), "자원 계측 누락 또는 비유한 수치다")
    require(memory["sample_count"] > 0 and memory["owned_server_peak_rss_mib"] > 0,
            "실제 메모리 표본과 서버 RSS가 필요하다")


def complete_replies(replies):
    if len(replies) != MAX_GENERATIONS:
        return False
    for reply in replies:
        choices = reply.get("choices", [])
        if not isinstance(choices, list) or len(choices) != 1:
            return False
        choice = choices[0]
        message = choice.get("message", {})
        if choice.get("finish_reason") != "stop" or not isinstance(message.get("content"), str) or not message["content"].strip():
            return False
    return True


def cleanup_state(session, memory, *, expect_teacher=True):
    errors = []
    processes = []
    for kind, owner in (("teacher", session), ("memory", memory)):
        if kind == "teacher" and not expect_teacher:
            continue
        if kind == "memory" and owner is None:
            continue
        process = getattr(owner, "process", None)
        code = process.poll() if process is not None else None
        processes.append(dict(role=kind, actual_exit=code))
        if process is None or code is None or code == -signal.SIGKILL:
            errors.append(dict(stage=kind, reason="실제 종료 미확인 또는 강제 KILL"))
        threads = getattr(owner, "workers", []) if kind == "teacher" else [getattr(owner, "worker", None)]
        if any(thread is not None and thread.is_alive() for thread in threads):
            errors.append(dict(stage=kind, reason="계측 또는 로그 thread가 남았다"))
    return dict(processes=processes, errors=errors)


def worker(args, budget, receipt):
    sup = supervisor()
    invocation = read_json(args.output / "invocation.json")
    token = os.environ.get(sup.OWNER_KEY, "")
    require(bool(re.fullmatch("[0-9a-f]{64}", token)) and os.getppid() == invocation["parent_pid"],
            "소유 감독자의 직접 자식만 worker를 실행한다")
    current = sup.proc.proc_stat(os.getppid())
    require(current["starttime"] == invocation["parent_starttime"], "감독 부모 PID가 재사용되었다")
    require(invocation["source_sha256"] == receipt["sha256"], "worker 소스 신원이 다르다")
    from scripts import p106b_gemma_teacher as gemma
    from scripts import diag_p106b_mtp_teacher as lifecycle
    from scripts.p106b_memory_stream import PersistentMemory, stream_session_scope
    from scripts.p106b_gemma_telemetry_resume import RetryingMemoryReader
    require(gemma.CONTEXT == 8192 and gemma.THINKING == 1024 and gemma.MAX_OUTPUT == 3072,
            "Gemma 원형 형상이 달라졌다")
    result = dict(schema=SCHEMA, status="STARTING", original_error=None, cleanup_errors=[],
                  source_sha256=receipt["sha256"], generation_attempts=0, model_started=False,
                  semantic_truth="NOT_REVIEWED", future_oom_safety="NOT_ESTABLISHED",
                  profile_difference="CODE_AUTHORED_QA_JSON_ONLY_NO_QUOTA_OR_MULTITURN")
    requests = Requests(args.output, budget, args.output / "STOP")
    context = gemma.GemmaSession(True)
    session, memory, memory_data = None, None, None
    memory_owner = PersistentMemory()
    result["prompt_observations"] = []
    code = 9
    try:
        result["asset_identity"] = gemma.assets(False)
        with requests.scope(lifecycle):
            with memory_owner as memory:
                reader = RetryingMemoryReader(memory, emit=lambda _: None)
                with stream_session_scope(reader):
                    result["immediately_before_model"] = gpu_snapshot(budget)
                    admit(result["immediately_before_model"])
                    result["model_started"] = True
                    with context as session:
                        for case in workload():
                            session.check()
                            payload = production_payload(case)
                            prompt = session.request("/apply-template", {"messages": payload["messages"]})["prompt"]
                            ids = session.request("/tokenize", dict(content=prompt, add_special=False, parse_special=True))["tokens"]
                            require(isinstance(ids, list) and len(ids) + 3072 + 128 <= 8192,
                                    "원 생산기의 문맥 예약을 넘었다")
                            result["prompt_observations"].append(dict(case_id=case["id"], input_tokens=len(ids),
                                applied_prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest().upper()))
                            session.request("/v1/chat/completions", payload, timeout=300)
                            session.check()
                        memory_data = session.memory()
                        validate_memory(memory_data)
                        result["memory"] = memory_data
                        result["memory_stream"] = memory.snapshot()
                    result["teacher_actual_exit"] = session.process.poll()
            result["cleanup"] = cleanup_state(session, memory)
            result["cleanup_errors"].extend(result["cleanup"]["errors"])
        code = 0 if complete_replies(requests.replies) and not result["cleanup_errors"] else 8
        result["status"] = "RESOURCE_OBSERVATION_COMPLETE" if code == 0 else "INCOMPLETE_OBSERVATION"
    except BaseException as error:
        result["original_error"] = sup.error_record(error, "자식 자원 관측", token)
        result["status"] = "PRE_MODEL_HOLD" if isinstance(error, Hold) and not result["model_started"] else "ERROR"
        code = 8 if result["status"] == "PRE_MODEL_HOLD" else 9
    finally:
        if session is None:
            session = getattr(context, "session", None)
        if result["model_started"] or memory_owner.process is not None:
            audit = cleanup_state(session, memory_owner, expect_teacher=result["model_started"])
            result["cleanup"] = audit
            result["cleanup_errors"].extend(error for error in audit["errors"] if error not in result["cleanup_errors"])
        if result["cleanup_errors"]:
            code = 9
        result.update(returncode=code, generation_attempts=requests.generations,
                      completed_responses=len(requests.replies), routes=requests.routes,
                      request_metrics=requests.metrics, http_events=requests.events,
                      elapsed_sec=time.monotonic() - budget.started)
        try:
            require(source_identity()["sha256"] == receipt["sha256"], "worker 완료 전 소스가 달라졌다")
        except BaseException as error:
            result["cleanup_errors"].append(sup.error_record(error, "자식 소스 재검산", token))
            code = result["returncode"] = 9
        try:
            timed_write(args.output / "worker.json", result, budget)
        except BaseException as error:
            error.capacity_original_error = result["original_error"]
            error.capacity_cleanup_errors = result["cleanup_errors"]
            raise
    return code


def supervision_ok(value, expected=0):
    return (value.get("actual_producer_exit") == expected and value.get("process_started") is True
            and not value.get("original_error") and not value.get("cleanup_errors")
            and not value.get("forced_cleanup") and not value.get("stop_published")
            and not value.get("termination_requested") and not value.get("deferred_signals")
            and not value.get("parent_witness_errors") and value.get("subreaper_restored") is True
            and value.get("controller_group_quiescent") is True)


def child_command(args, receipt, budget):
    return [str(Path(sys.executable).resolve()), "-I", "-B", "-X", "utf8", str(ROOT / ENTRY),
            "--worker", "--output", str(args.output), "--source-sha256", receipt["sha256"],
            "--max-wall-sec", str(args.max_wall_sec), "--deadline", args.deadline,
            "--parent-started", str(budget.started)]


def parent(args, budget, receipt):
    sup = supervisor()
    require(not args.output.exists() and not args.output.is_symlink(), "기존 증거 이름공간을 보존한다")
    args.output.mkdir()
    report = dict(schema=SCHEMA, source_sha256=receipt["sha256"], original_error=None,
                  cleanup_errors=[], returncode=9, status="STARTING",
                  admission_mib=ADMISSION_MIB, budget_basis=dict(sampled_global_peak_mib=8771,
                  margin_mib=2048, sum_mib=10819, rounded_mib=11264),
                  continuous_peak_verified=False, future_oom_safety="NOT_ESTABLISHED",
                  external_os_timeout_required=True, actual_supervisor_exit="ROOT_MUST_COLLECT",
                  parent_sigkill_descendants_guaranteed=False)
    code = 9
    try:
        timed_write(args.output / "source.json", receipt, budget)
        parent_stat = sup.proc.proc_stat(os.getpid())
        timed_write(args.output / "invocation.json", dict(parent_pid=os.getpid(),
                    parent_starttime=parent_stat["starttime"], source_sha256=receipt["sha256"]), budget)
        report["admission"] = gpu_snapshot(budget)
        admit(report["admission"])
        result = sup.supervise_process(child_command(args, receipt, budget), args.output,
                                       args.output / "STOP", sup.executable_paths(), budget)
        report["supervision"] = result
        if (args.output / "worker.json").is_file():
            report["worker"] = read_json(args.output / "worker.json")
        observed = report.get("worker", {})
        if supervision_ok(result) and observed.get("returncode") == 0:
            require(observed.get("source_sha256") == receipt["sha256"]
                    and observed.get("generation_attempts") == 4 and observed.get("completed_responses") == 4,
                    "네 생성 원답의 완결 증거가 필요하다")
            require(len(observed.get("request_metrics", [])) == 4
                    and len(observed.get("prompt_observations", [])) == 4,
                    "네 요청의 토큰 및 prompt 계측이 필요하다")
            validate_memory(observed["memory"])
            for index in range(1, 5):
                raw = read_json(args.output / f"raw_{index:02d}.json")
                require(raw["index"] == index and "reply" in raw, "원답 저장 검산이 다르다")
            roles = [row["role"] for row in result.get("owned_sessions", [])]
            require(roles.count("teacher") == 1 and roles.count("memory") == 1,
                    "실제 교사·계측 별도 세션을 각각 한 개 확인해야 한다")
            report["after_cleanup"] = gpu_snapshot(budget)
            require(not report["after_cleanup"]["compute_apps"], "종료 뒤 GPU compute 프로세스가 남았다")
            code, report["status"] = 0, "RESOURCE_OBSERVATION_COMPLETE"
        elif supervision_ok(result, 8) and observed.get("returncode") == 8:
            code, report["status"] = 8, observed["status"]
        else:
            report["status"] = "ERROR"
    except BaseException as error:
        report["original_error"] = sup.error_record(error, "부모 자원 관측")
        code = 8 if isinstance(error, Hold) else 9
        report["status"] = "PRE_MODEL_HOLD" if code == 8 else "ERROR"
    try:
        require(source_identity()["sha256"] == receipt["sha256"], "부모 완료 전 소스가 달라졌다")
    except BaseException as error:
        report["cleanup_errors"].append(sup.error_record(error, "부모 소스 재검산"))
        code = 9
        report["status"] = "ERROR"
    report.update(returncode=code, elapsed_sec=time.monotonic() - budget.started)
    try:
        timed_write(args.output / "report.json", report, budget)
    except BaseException as error:
        error.capacity_original_error = report["original_error"]
        error.capacity_cleanup_errors = report["cleanup_errors"]
        raise
    sup.append_terminal(args.output, dict(event="OBSERVATION", returncode=code,
                        status=report["status"], elapsed_sec=time.monotonic() - budget.started))
    budget.check("종결 원장 저장 후")
    return code


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    group.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-sha256")
    parser.add_argument("--max-wall-sec", type=int, default=590)
    parser.add_argument("--deadline", default=END.isoformat())
    parser.add_argument("--parent-started", type=float, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    directory, sup, budget = None, None, None
    try:
        require(120 <= args.max_wall_sec <= 600, "전체 시간은 120..600초 범위다")
        deadline = datetime.fromisoformat(args.deadline.replace("Z", "+00:00"))
        require(deadline.tzinfo is not None and deadline <= END, "26일 17시 이내의 명시 시각이 필요하다")
        receipt = source_identity()
        if args.check_only:
            if args.source_sha256:
                require(args.source_sha256.upper() == receipt["sha256"], "소스 신원이 달라졌다")
            print(json.dumps(dict(schema=SCHEMA, source_sha256=receipt["sha256"],
                  code_files=len(receipt["files"]), protocol=receipt["protocol"],
                  torch_imported="torch" in sys.modules, gpu_queries=0, files_written=0),
                  ensure_ascii=False, allow_nan=False), flush=True)
            return 0
        require(args.source_sha256 and args.source_sha256.upper() == receipt["sha256"], "실행에는 정확한 소스 신원이 필요하다")
        require(args.output is not None and args.output.is_absolute()
                and args.output.parent == ROOT / "test_result/evidence"
                and re.fullmatch(PREFIX + "[A-Za-z0-9_]+", args.output.name), "새 증거 이름공간이 필요하다")
        require(not args.output.is_symlink() and not any(p.is_symlink() for p in args.output.parents),
                "증거 경로의 링크를 허용하지 않는다")
        require(os.environ.get("CUDA_VISIBLE_DEVICES") in (None, "0"), "실행 GPU 0 선택을 명확히 해야 한다")
        directory = args.output
        sup = supervisor()
        started = args.parent_started if args.worker else STARTED
        require(started is not None, "부모 시작 시각이 필요하다")
        budget = sup.Budget(args.max_wall_sec, deadline.timestamp(), started=started, reserve=60)
        with sup.total_budget(budget), sup.termination_guard():
            code = worker(args, budget, receipt) if args.worker else parent(args, budget, receipt)
            print(json.dumps(dict(schema=SCHEMA, status="OBSERVED" if code == 0 else "HOLD_OR_ERROR",
                  returncode=code, generation_limit=4, future_oom_safety="NOT_ESTABLISHED"),
                  ensure_ascii=False), flush=True)
            budget.check("작은 stdout 출력 후")
        budget.check("타이머와 신호 복구 후")
        return code
    except BaseException as error:
        record = dict(event="TERMINAL_VETO", returncode=9, error_type=type(error).__name__,
                      message=str(error)[:1200], original_error=getattr(error, "capacity_original_error", None),
                      cleanup_errors=getattr(error, "capacity_cleanup_errors", []))
        if directory is not None and directory.is_dir() and sup is not None:
            try:
                sup.append_terminal(directory, record)
            except BaseException:
                pass
        print(json.dumps(dict(schema=SCHEMA, returncode=9, error_type=type(error).__name__),
                         ensure_ascii=False), flush=True)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())

