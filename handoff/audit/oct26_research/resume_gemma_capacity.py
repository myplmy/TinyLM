#!/usr/bin/env python3
"""기존 V3 재개에만 적용하는 분리 자원 정책. 실제 실행은 총괄 소유다.

기존 생성 입력과 파일은 바꾸지 않는다. 입장 alias와 reader만 프로세스 안에서
복원 가능한 범위로 바꾼다. 선행 짧은 probe는 장문·멀티턴·전체 부하·품질이나
미래 OOM 보증이 아니다. 외부 OS timeout과 실제 supervisor 종료 회수가 필요하다.
"""
from __future__ import annotations
import time
STARTED = time.monotonic()
import argparse
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.p106b_gemma_telemetry_resume import RetryingMemoryReader

ENTRY = "handoff/audit/oct26_research/resume_gemma_capacity.py"
TEST = "scripts/test_p106b_capacity_resume.py"
PROBE = "handoff/audit/oct26_research/probe_gemma_capacity.py"
REVIEW = "handoff/audit/oct26_research/capacity_root_review.json"
REPORT = "test_result/evidence/p106b_gemma_capacity_v1_20261026_roota/report.json"
PRODUCTION = "HF/sft_ready/p106b_supported_production8h_v3_s1337"
BASE_SHA = "20E9CC072993D530655C875C81E464E760D1261F34FE3645E1B40620558D4FA5"
REPORT_SHA = "FEFF7FDB9DF30E0FC94156680522D072A6BAC7F43544DBC313000DACF3FE307B"
SCHEMA = "P106B_GEMMA_CAPACITY_RESUME_V1"
PREFIX = "p106b_gemma_capacity_resume_v1_20261026_"
END = datetime(2026, 10, 26, 8, tzinfo=timezone.utc)
FLOOR = 2048
PROBE_MODULE = None


def helpers():
    global PROBE_MODULE
    if PROBE_MODULE is None:
        spec = importlib.util.spec_from_file_location("capacity_frozen_probe", ROOT / PROBE)
        value = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(value)
        PROBE_MODULE = value
    return PROBE_MODULE


def source_identity():
    p = helpers()
    base = p.source_identity()
    p.require(base["sha256"] == BASE_SHA, "동결된 선행 probe 소스가 달라졌다")
    files = {name: hashlib.sha256(p.regular(name, ROOT).read_bytes()).hexdigest().upper()
             for name in (ENTRY, TEST)}
    value = dict(schema=SCHEMA, base_source_sha256=BASE_SHA, files=files,
                 admission_mib=11264, runtime_free_floor_mib=FLOOR,
                 maximum_wall_sec=28800, reserve_sec=120,
                 absolute_deadline=END.isoformat(), generation_info_changed=False)
    return dict(sha256=p.digest(value), **value)


def proof(root=None, expected_review=None):
    p, root = helpers(), ROOT if root is None else Path(root)
    review_path = p.regular(REVIEW, root)
    review_sha = hashlib.sha256(review_path.read_bytes()).hexdigest().upper()
    if expected_review is not None:
        p.require(review_sha == expected_review.upper(), "총괄 판독 영수증이 달라졌다")
    review = p.read_json(review_path)
    p.require(review.get("schema") == "TINYLM_GEMMA_CAPACITY_ROOT_REVIEW_V1"
              and review.get("probe_source_sha256") == BASE_SHA
              and review.get("report_path") == REPORT and review.get("report_sha256") == REPORT_SHA
              and review.get("actual_root_launcher_exit") == 0
              and review.get("fixture_content_pairs_read") == 4
              and review.get("same_generation_parameters") is True
              and review.get("adopt_production_auto") is False
              and review.get("global_oom_safety") == "NOT_ESTABLISHED"
              and review.get("long_context_or_multiturn_full_load_safe") == "NOT_ESTABLISHED",
              "실제 네 원답의 총괄 판독과 제한 영수증이 필요하다")
    report_path = p.regular(REPORT, root)
    p.require(hashlib.sha256(report_path.read_bytes()).hexdigest().upper() == REPORT_SHA,
              "선행 실제 report SHA가 다르다")
    report = p.read_json(report_path)
    p.require(report.get("returncode") == 0 and report.get("source_sha256") == BASE_SHA
              and report.get("status") == "RESOURCE_OBSERVATION_COMPLETE"
              and not report.get("original_error") and not report.get("cleanup_errors"),
              "선행 실제 부모 관측이 완결되지 않았다")
    p.require(p.supervision_ok(report["supervision"]), "선행 실제 종료와 정리가 완결되지 않았다")
    worker = report["worker"]
    p.require(worker.get("returncode") == 0 and worker.get("generation_attempts") == 4
              and worker.get("completed_responses") == 4 and not worker.get("original_error")
              and not worker.get("cleanup_errors") and not worker.get("cleanup", {}).get("errors"),
              "선행 실제 자식·원답·정리 조건이 다르다")
    p.require(p.read_json(p.regular(str(Path(REPORT).parent / "worker.json"), root)) == worker,
              "선행 자식 증거와 부모의 포함 값이 다르다")
    p.validate_memory(worker["memory"])
    telemetry = worker["memory"]["telemetry_recovery"]
    p.require(all(type(telemetry.get(key)) is int and telemetry[key] == 0 for key in
              ("timeout_attempts", "fatal_calls"))
              and type(telemetry.get("unobserved_query_window_sec")) in (int, float)
              and math.isfinite(telemetry["unobserved_query_window_sec"])
              and telemetry["unobserved_query_window_sec"] == 0,
              "선행 자원 계측의 누락 구간이 있다")
    summary = review["resource_summary"]
    p.require(all(summary.get(key) == worker["memory"].get(key) for key in
              ("sampled_gpu_global_peak_mib", "sampled_gpu_min_free_mib",
               "baseline_gpu_used_mib", "sample_count"))
              and all(summary.get(key) == 0 for key in ("timeouts", "query_gaps", "actual_cleanup_errors")),
              "총괄 영수증의 자원 수치가 실제 관측과 다르다")
    checks = review.get("structural_render_checks", [])
    p.require(len(checks) == 4, "원답 네 개의 판독 영수증이 필요하다")
    replies, raw_shas = [], {}
    for index, item in enumerate(checks, 1):
        name = str(Path(REPORT).parent / f"raw_{index:02d}.json")
        p.require(item.get("raw_file") == name and item.get("label_status") == "LABELS_COMPLETE"
                  and bool(item.get("root_content_readback")) and bool(item.get("rendered_student_turn")),
                  "총괄의 개별 원답 판독이 누락됐다")
        path = p.regular(name, root)
        actual = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        p.require(actual == item.get("raw_sha256"), "선행 원답의 SHA가 다르다")
        raw = p.read_json(path)
        p.require(raw.get("index") == index and raw["payload"].get("max_tokens") == 3072
                  and raw["payload"].get("thinking_budget_tokens") == 1024,
                  "선행 요청 형상이 다르다")
        p.require(all(raw["payload"].get(k) == v for k, v in review["observed_sampling"].items()),
                  "선행 sampler가 다르다")
        replies.append(raw["reply"])
        raw_shas[name] = actual
    p.require(p.complete_replies(replies), "선행 네 응답이 완결되지 않았다")
    terminal_path = p.regular(str(Path(REPORT).parent / "terminal.jsonl"), root)
    terminals = [json.loads(line) for line in terminal_path.read_text().splitlines() if line.strip()]
    p.canonical(terminals)
    p.require(terminals and all(row.get("returncode") == 0 and row.get("event") != "TERMINAL_VETO"
                              for row in terminals), "선행 종결 거부가 있거나 종결이 없다")
    return dict(review_path=REVIEW, review_sha256=review_sha, probe_report_sha256=REPORT_SHA,
                probe_source_sha256=BASE_SHA, raw_sha256=raw_shas,
                terminal_sha256=hashlib.sha256(terminal_path.read_bytes()).hexdigest().upper(),
                resource_only=True, future_oom_safety="NOT_ESTABLISHED")


class CapacityMemoryReader(RetryingMemoryReader):
    """기존 재시도와 누락 기록을 유지하며 낮은 여유는 되살리지 않는다."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.floor_breaches = 0
        self.floor_latched = False

    def __call__(self):
        with self.lock:
            if self.floor_latched:
                raise RuntimeError("자원 하한 중단 이후 계측을 정상으로 되살리지 않는다")
            used, free = super().__call__()
            if free < FLOOR:
                self.floor_breaches += 1
                self.floor_latched = True
                self.event("CAPACITY_FLOOR", free_mib=free, required_free_mib=FLOOR)
                raise RuntimeError("실측 GPU 여유가 2048MiB 아래여서 중단한다")
            return used, free

    def snapshot(self):
        with self.lock:
            return dict(super().snapshot(), resource_profile=SCHEMA, minimum_free_required_mib=FLOOR,
                        floor_breaches=self.floor_breaches, floor_latched=self.floor_latched)


@contextmanager
def resource_scope(budget, readers, admissions):
    p = helpers()
    from scripts import diag_p106b_gemma_deficit_production as producer
    from scripts import diag_p106b_gemma_telemetry_resume as telemetry
    from scripts.p106b_gate_runtime import PrerequisiteHold
    class Reader(CapacityMemoryReader):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            readers.append(self)
    def admission():
        value = p.gpu_snapshot(budget)
        value["admitted"] = False
        admissions.append(value)
        try:
            p.admit(value)
        except p.Hold as error:
            raise PrerequisiteHold(str(error)) from error
        value["admitted"] = True
    with patch.object(producer, "idle_before_gpu", admission), \
         patch.object(telemetry, "RetryingMemoryReader", Reader):
        yield


def quiet(result):
    return (result.get("process_started") is True and type(result.get("actual_producer_exit")) is int
            and result.get("actual_producer_exit") in (0, 8)
            and not result.get("original_error") and not result.get("cleanup_errors")
            and not result.get("forced_cleanup") and not result.get("termination_requested")
            and not result.get("parent_witness_errors") and result.get("subreaper_restored") is True
            and not result.get("residual_at_producer_exit")
            and result.get("controller_group_quiescent") is True)


def verify_empty_hold(destination, before, inputs, supervision, child, budget):
    """입장 단계의 닫힌 빈 GATE_NEGATIVE를 정상 생산 pause와 구분한다."""
    p, sup = helpers(), helpers().supervisor()
    directories = sorted(destination.glob("batch_*"))
    if not (supervision["actual_producer_exit"] == 8 and child.get("precondition_hold") is True
            and len(directories) == before["batches"] + 1):
        return None
    p.require(not any(row.get("role") == "teacher" for row in supervision.get("owned_sessions", [])),
              "교사 시작 뒤의 실패를 모델 시작 전 HOLD로 세지 않는다")
    p.require(any(row.get("admitted") is False for row in child.get("admissions", [])),
              "새 입장 조회가 거부된 증거가 필요하다")
    directory = directories[-1]
    p.require(directory.name == "batch_%06d" % before["batches"], "빈 HOLD의 새 배치 번호가 다르다")
    budget.check("새 빈 HOLD 배치 검산")
    p.require(set(sup.batch_files(directory, budget)) == {"report.json"}, "빈 HOLD에 원답 또는 미완 파일이 있다")
    report = p.read_json(directory / "report.json")
    previous = before["reports"][-1]
    p.require(report.get("schema") == "P106B_GEMMA_DEFICIT_BATCH_V1" and report.get("input") == inputs
              and report.get("returncode") == 8 and report.get("status") == "GATE_NEGATIVE"
              and report.get("error_type") == "PrerequisiteHold" and report.get("accepted_groups") == 0
              and report.get("new_train_x_tokens") == 0
              and not report.get("raw_manifest") and not report.get("candidate_manifest"),
              "입장 거부로 닫힌 빈 배치 계약이 다르다")
    for key in ("cursor", "nonpadding_tokens", "assistant_targets", "rows", "family_tokens", "task_tokens"):
        p.require(report.get(key) == previous.get(key), "빈 HOLD가 기존 누적 상태를 바꿨다: " + key)
    return dict(status="CLOSED_PRE_MODEL_HOLD", new_batches=1, accepted_groups=0,
                report_sha256=sup.proc.digest(directory / "report.json"), cursor=report["cursor"])


def worker(args, budget, receipt):
    p, sup = helpers(), helpers().supervisor()
    invocation = p.read_json(args.output / "invocation.json")
    token = os.environ.get(sup.OWNER_KEY, "")
    p.require(re.fullmatch("[0-9a-f]{64}", token) and os.getppid() == invocation["parent_pid"],
              "소유 부모의 직접 자식만 생산 worker를 시작한다")
    p.require(sup.proc.proc_stat(os.getppid())["starttime"] == invocation["parent_starttime"],
              "생산 부모 PID가 재사용됐다")
    p.require(invocation["source_sha256"] == receipt["sha256"], "worker 소스 신원이 다르다")
    proof(expected_review=args.review_sha256)
    from scripts import diag_p106b_supported_production8h as run
    readers, admissions = [], []
    result = dict(schema=SCHEMA, source_sha256=receipt["sha256"], original_error=None,
                  cleanup_errors=[], generation_info_changed=False, precondition_hold=False,
                  semantic_quality="NOT_REVIEWED", future_oom_safety="NOT_ESTABLISHED")
    code = 9
    try:
        budget.check("생산 원형 진입 전")
        # 자식의 원 생산기가 자신의 ITIMER_REAL을 소유한다. 부모가 전체 시간을 감독한다.
        deadline = time.time() + budget.remaining() - budget.reserve
        remaining = int(budget.remaining() - budget.reserve)
        p.require(remaining >= 60, "원형 생산과 정상 게시 시간이 부족하다")
        production_args = SimpleNamespace(mode="resume", stop_file=args.output / "STOP",
            max_wall_sec=min(28800, remaining), deadline_utc=datetime.fromtimestamp(deadline, timezone.utc).isoformat())
        with resource_scope(budget, readers, admissions):
            code = run.execute(production_args)
        p.require(type(code) is int and code in (0, 8, 9), "원 생산기 실제 종료 계약이 다르다")
    except (FileNotFoundError, FileExistsError) as error:
        result["original_error"] = sup.error_record(error, "생산 선결", token)
        result["precondition_hold"] = True
        print("[HOLD] " + type(error).__name__, flush=True)
        code = 8
    except BaseException as error:
        result["original_error"] = sup.error_record(error, "생산 실행", token)
        code = 9
    snapshots = [reader.snapshot() for reader in readers]
    result["precondition_hold"] |= code == 8 and any(row.get("admitted") is False for row in admissions)
    if any(row.get("floor_latched") for row in snapshots):
        code = 9
    result.update(returncode=code, admissions=admissions, memory_readers=snapshots,
                  elapsed_sec=time.monotonic() - budget.started)
    try:
        p.require(source_identity()["sha256"] == receipt["sha256"], "자식 완료 전 소스가 달라졌다")
        proof(expected_review=args.review_sha256)
    except BaseException as error:
        result["cleanup_errors"].append(sup.error_record(error, "자식 원형 재검산", token))
        code = result["returncode"] = 9
    try:
        p.timed_write(args.output / "worker.json", result, budget)
    except BaseException as error:
        error.capacity_original_error = result["original_error"]
        error.capacity_cleanup_errors = result["cleanup_errors"]
        raise
    return code


def parent(args, budget, receipt, evidence):
    p, sup = helpers(), helpers().supervisor()
    p.require(not args.output.exists() and not args.output.is_symlink(), "새 감독 증거 이름공간이 필요하다")
    args.output.mkdir()
    result = dict(schema=SCHEMA, source_sha256=receipt["sha256"], prior_probe=evidence,
                  resource_policy=dict(entry_free_mib=11264, runtime_free_floor_mib=FLOOR),
                  generation_info_changed=False, original_error=None, cleanup_errors=[],
                  future_oom_safety="NOT_ESTABLISHED", actual_supervisor_exit="ROOT_MUST_COLLECT",
                  external_os_timeout_required=True, parent_sigkill_descendants_guaranteed=False)
    code = 9
    before, inputs_path, inputs_sha = None, None, None
    try:
        p.timed_write(args.output / "source.json", receipt, budget)
        p.timed_write(args.output / "resource_envelope.json", result, budget)
        before = sup.production_snapshot(ROOT / PRODUCTION, budget)
        inputs_path = p.regular(PRODUCTION + "/inputs.json", ROOT)
        inputs_sha = hashlib.sha256(inputs_path.read_bytes()).hexdigest().upper()
        inputs = p.read_json(inputs_path)
        result["before"] = dict(batches=before["batches"], files=before["files"], inputs_sha256=inputs_sha)
        p.timed_write(args.output / "production_before.json", result["before"], budget)
        owner = sup.proc.proc_stat(os.getpid())
        p.timed_write(args.output / "invocation.json", dict(parent_pid=os.getpid(),
            parent_starttime=owner["starttime"], source_sha256=receipt["sha256"]), budget)
        result["admission"] = p.gpu_snapshot(budget)
        p.admit(result["admission"])
        command = [str(Path(sys.executable).resolve()), "-I", "-B", "-X", "utf8", str(ROOT / ENTRY),
                   "--worker", "--output", str(args.output), "--max-wall-sec", str(args.max_wall_sec),
                   "--deadline", args.deadline, "--source-sha256", receipt["sha256"],
                   "--review-sha256", args.review_sha256, "--parent-started", str(budget.started)]
        observed = sup.supervise_process(command, args.output, args.output / "STOP",
                                         sup.executable_paths(), budget)
        result["supervision"] = observed
        if (args.output / "worker.json").is_file():
            result["worker"] = p.read_json(args.output / "worker.json")
        p.require(quiet(observed), "실제 생산 종료 또는 소유 프로세스 정리가 완결되지 않았다")
        child = result.get("worker", {})
        p.require(child.get("returncode") == observed["actual_producer_exit"]
                  and child.get("source_sha256") == receipt["sha256"] and not child.get("cleanup_errors"),
                  "실제 자식 종료와 새 정책 증거가 다르다")
        p.require(hashlib.sha256(inputs_path.read_bytes()).hexdigest().upper() == inputs_sha,
                  "원 생산 inputs가 달라졌다")
        verified = verify_empty_hold(ROOT / PRODUCTION, before, inputs, observed, child, budget)
        if verified is None:
            verified = sup.verify_production(ROOT / PRODUCTION, before, inputs,
                        observed["actual_producer_exit"], args.output / "producer.log", budget)
        result["production"] = verified
        p.require(not any(row.get("floor_latched") for row in child.get("memory_readers", [])),
                  "실행 중 자원 하한을 위반했다")
        result["after_cleanup"] = p.gpu_snapshot(budget)
        p.require(not result["after_cleanup"]["compute_apps"], "종료 뒤 GPU compute 프로세스가 남았다")
        code = observed["actual_producer_exit"]
        result["status"] = verified["status"]
    except BaseException as error:
        result["original_error"] = sup.error_record(error, "생산 감독")
        code = 8 if isinstance(error, p.Hold) else 9
        result["status"] = "PRE_MODEL_HOLD" if code == 8 else "ERROR"
    try:
        if before is not None:
            for name, wanted in before["files"].items():
                budget.check("원 배치 후행 불변 검산")
                p.require(sup.proc.digest(sup.bounded_file(ROOT / PRODUCTION / name)) == wanted,
                          "원 배치가 달라졌다: " + name)
        if inputs_path is not None:
            p.require(hashlib.sha256(inputs_path.read_bytes()).hexdigest().upper() == inputs_sha,
                      "원 생산 inputs가 달라졌다")
        result["old_files_unchanged"] = before is not None
    except BaseException as error:
        result["cleanup_errors"].append(sup.error_record(error, "원 배치와 inputs 불변 검산"))
        result["old_files_unchanged"] = False
        result["status"] = "ERROR"
        code = 9
    try:
        p.require(source_identity()["sha256"] == receipt["sha256"], "부모 완료 전 소스가 달라졌다")
        proof(expected_review=args.review_sha256)
    except BaseException as error:
        result["cleanup_errors"].append(sup.error_record(error, "부모 원형 재검산"))
        result["status"] = "ERROR"
        code = 9
    result.update(returncode=code, elapsed_sec=time.monotonic() - budget.started)
    try:
        p.timed_write(args.output / "report.json", result, budget)
    except BaseException as error:
        error.capacity_original_error = result["original_error"]
        error.capacity_cleanup_errors = result["cleanup_errors"]
        raise
    sup.append_terminal(args.output, dict(event="OBSERVATION", returncode=code,
                        status=result["status"], elapsed_sec=time.monotonic() - budget.started))
    budget.check("생산 감독 종결 게시 후")
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    group.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-sha256")
    parser.add_argument("--review-sha256")
    parser.add_argument("--max-wall-sec", type=int, default=28800)
    parser.add_argument("--deadline", default=END.isoformat())
    parser.add_argument("--parent-started", type=float, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    sup, directory = None, None
    try:
        p = helpers()
        p.require(300 <= args.max_wall_sec <= 28800, "전체 생산 시간은 300..28800초다")
        deadline = datetime.fromisoformat(args.deadline.replace("Z", "+00:00"))
        p.require(deadline.tzinfo is not None and deadline <= END, "26일 17시 이내의 명시 마감이 필요하다")
        receipt = source_identity()
        evidence = proof(expected_review=args.review_sha256)
        if args.check_only:
            if args.source_sha256:
                p.require(args.source_sha256.upper() == receipt["sha256"], "새 소스 신원이 다르다")
            print(json.dumps(dict(schema=SCHEMA, source_sha256=receipt["sha256"], prior_probe=evidence,
                  torch_imported="torch" in sys.modules, gpu_queries=0, files_written=0,
                  production_replay="NOT_RUN", model_loaded=False), ensure_ascii=False), flush=True)
            return 0
        p.require(args.source_sha256 and args.source_sha256.upper() == receipt["sha256"]
                  and args.review_sha256 and args.review_sha256.upper() == evidence["review_sha256"],
                  "실행에는 새 소스와 총괄 판독 영수증의 정확 SHA가 필요하다")
        p.require(args.output is not None and args.output.is_absolute()
                  and args.output.parent == ROOT / "test_result/evidence"
                  and re.fullmatch(PREFIX + "[A-Za-z0-9_]+", args.output.name)
                  and not any(x.is_symlink() for x in [args.output, *args.output.parents]),
                  "새 감독 출력과 STOP 이름공간이 필요하다")
        p.require(os.environ.get("CUDA_VISIBLE_DEVICES") in (None, "0"), "실행 GPU 0을 명확히 선택해야 한다")
        directory, sup = args.output, p.supervisor()
        started = args.parent_started if args.worker else STARTED
        p.require(started is not None, "현재 부모 시작 시각이 필요하다")
        budget = sup.Budget(args.max_wall_sec, deadline.timestamp(), started=started, reserve=120)
        # 부모의 total_budget이 준비부터 종료까지 감독한다. 원 생산기 타이머와 경합하지 않는다.
        timer = nullcontext() if args.worker else sup.total_budget(budget)
        with timer, sup.termination_guard():
            code = worker(args, budget, receipt) if args.worker else parent(args, budget, receipt, evidence)
            print(json.dumps(dict(schema=SCHEMA, returncode=code, future_oom_safety="NOT_ESTABLISHED")),
                  flush=True)
            budget.check("작은 stdout 출력 후")
        budget.check("감독 타이머와 신호 복구 후")
        return code
    except BaseException as error:
        if directory is not None and directory.is_dir() and sup is not None:
            try:
                sup.append_terminal(directory, dict(event="TERMINAL_VETO", returncode=9,
                    error_type=type(error).__name__, message=str(error)[:1200],
                    original_error=getattr(error, "capacity_original_error", None),
                    cleanup_errors=getattr(error, "capacity_cleanup_errors", [])))
            except BaseException:
                pass
        print(json.dumps(dict(schema=SCHEMA, returncode=9, error_type=type(error).__name__)), flush=True)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())

