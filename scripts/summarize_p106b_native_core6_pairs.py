#!/usr/bin/env python3
"""Native GPT2의 원9/PENDING·terminal0·root 종료0을 보존하는 사후 보조 통계.

원 보고서를 HF 성공 보고서로 바꾸지 않는다. 기존7모델 admission, CaseContracts,
recount_model, paired_intervals를 직접 재사용하며 GPT2와의7쌍만 추가한다.
실제 실행은 root의 외부120초 감독과 실제 프로세스 exit0 확인을 함께 요구한다.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import re
import resource
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import tinylm  # noqa: F401 -- HF import보다 먼저 기존 process-local 경로 정책을 적용한다.
from scripts import summarize_p106b_core6_pairs as shared
from scripts import p106b_native_window as window

TAG, SCHEMA = "p106b_native_core6_pairs_v2_s1337", "P106B_NATIVE_CORE6_PAIRS_V2"
OWN_FILES = ("scripts/summarize_p106b_native_core6_pairs.py", "scripts/test_summarize_p106b_native_core6_pairs.py")
SHARED_SHA = "085A18CF0382C31F98BA4B9BC4C4B598DEFAF2D1BD0ECB6A9E911196C7B3485D"
WINDOW_SHA = "5BA4870D37800DE70A004305D644DD4263F9785B763B299647F1316DDE29A525"
REPORT_SHA = "5848997902688F3CA561419A28AD71031C1FCB864AEB6397E0EEDAEAD114020A"
TERMINAL_SHA = "D35B1A100A49D333A09596085C3630AD2086E83424C7B6F2B5F238981FA08DAD"
ROOT_AUDIT_SHA = "4CB2D9DB5BEE6763E6B3F289536A4790BAC2DB01936C4F06333478E4A3A98FE3"
REPORT_REL = "test_result/evidence/p106b_native_window10800_v2_s1337/gpt2_q4km/full/report.json"
ROOT_AUDIT_REL = "handoff/audit/WIP_20261024_GPT2_FULL_ROOT_CLOSURE.json"
ORIGINAL_PINS = dict(window.PRIOR)
MODEL, PEERS = "gpt2_q4km", tuple(shared.MODELS)
MAX_BYTES, RESAMPLES, SEED = 20_000_000, 100000, 20261024
SUPERVISOR_ENV = "P106B_NATIVE_PAIRS_ROOT_SUPERVISED"
COMPLETE, PENDING = "NATIVE_CORE6_PAIRS_CPU_COMPLETE", "NATIVE_CORE6_PAIRS_PENDING_TERMINAL"
SCOPE = ("이미 GPT2 점수를 관찰한 뒤 추가한 사후 보조 분석. 고정6과제 내 case-paired "
         "percentile95, 고정6과제 동일가중, 다중비교 미보정이며 학습seed/과제 모집단 불확실성이 아니다. "
         "native Q4/F32-KV/singleton과 HF FP32/no-KV/배치/사전학습은 일치하지 않는다. "
         "한국어·대화·새 지능·학습 성과·모델 채택을 주장하지 않는다.")
verify_strict_numerical = window.check_closed_numerical
verify_original_prerequisites = window.prerequisites
# Direct original function/class references; tests may replace only these new-module bindings.
admit_peer = shared.admit_report
read_tasks = shared.load_readonly_tasks
CaseContracts = shared.CaseContracts
recount_model = shared.recount_model
paired_intervals = shared.paired_intervals
canonical, digest, read_json = shared.canonical, shared.digest, shared.read_json
write_json, close_report = window.write_json, window.close_report


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source_identity():
    original, owner = shared.source_identity(), window.identity()
    require(original["sha256"] == SHARED_SHA and owner["sha256"] == WINDOW_SHA,
            "frozen statistical helper/native owner source changed")
    files = {name: digest(ROOT / name) for name in OWN_FILES}
    payload = dict(files=files, shared_source_sha256=SHARED_SHA, native_window_source_sha256=WINDOW_SHA,
                   root_audit_sha256=ROOT_AUDIT_SHA, native_report_sha256=REPORT_SHA, native_terminal_sha256=TERMINAL_SHA)
    return dict(**payload, sha256=shared.digest_bytes(canonical(payload)), shared=original, window=owner)


class Evidence:
    def __init__(self):
        self.inputs, self.absent = shared.Inputs(), set()

    def json(self, path, expected=None):
        path = shared.regular(path)
        require(path.stat().st_size < MAX_BYTES, "evidence JSON must be below20MB before hashing")
        self.inputs.add(path, expected)
        value = read_json(path)
        canonical(value)  # Overflow such as1e309 and unknown objects cannot enter a receipt.
        return value

    def no_file(self, path):
        path = Path(path)
        require(not path.exists() and not path.is_symlink(), "failure/veto evidence forbids adoption: " + str(path))
        self.absent.add(path)

    def unchanged(self):
        self.inputs.unchanged()
        for path in self.absent:
            require(not path.exists() and not path.is_symlink(), "late failure/veto evidence appeared")
        return True


def native_bundle(source, evidence, root=ROOT):
    """A separate native admission; the original report object is never rewritten."""
    root = Path(root)
    path = root / REPORT_REL
    if not path.is_file():
        raise shared.IncompleteFull("the pinned native full is not present")
    report = evidence.json(path, REPORT_SHA)
    terminal_path = path.parent / "terminal_receipt.json"
    terminal = evidence.json(terminal_path, TERMINAL_SHA)
    audit = evidence.json(root / ROOT_AUDIT_REL, ROOT_AUDIT_SHA)
    for name in ("terminal_failure_receipt.json", "report_closure_failure.json"):
        evidence.no_file(path.parent / name)
    expected = dict(schema=window.SCHEMA, tag=window.TAG, model=MODEL, mode="full", returncode=9,
        status="NATIVE_WINDOW_COMPUTE_CLOSED_PENDING_TERMINAL", candidate_returncode=0,
        candidate_status="NATIVE_WINDOW_FULL_COMPLETE", source_identity=source["window"],
        sources_unchanged=True, source_assets_unchanged=True, original_prerequisites_unchanged=True,
        actual_counts=shared.COUNTS, choice_likelihoods=67106, raw_independent_recount=True,
        framework_commit=shared.assets.COMMIT, data_manifest_sha256=shared.assets.MANIFEST_SHA,
        training=False, optimizer_updates=0, checkpoint_writes=0, policy=window.native.policy())
    require(all(report.get(key) == value for key, value in expected.items()),
            "exact native9/PENDING candidate and unchanged scientific contract required")
    require(type(report["returncode"]) is int and type(report["candidate_returncode"]) is int,
            "native status codes cannot be boolean stand-ins")
    require(report.get("token_lengths_summary", {}).get("requests") == 67106,
            "all67106 complete native choice likelihoods required")
    for key in ("sample_manifests", "independent_audits", "official_results"):
        require(set(report.get(key, {})) == set(shared.COUNTS), "all six closed native artifacts required")
    admission = report.get("admission", {})
    require(admission.get("hard_cap_seconds") == 10800 and admission.get("deadline_epoch") == window.native.DEADLINE,
            "original independent10800s/08:40 window differs")
    terminal_expected = dict(schema=window.SCHEMA, tag=window.TAG, model=MODEL, mode="full", returncode=0,
        status="NATIVE_WINDOW_FULL_COMPLETE", report_sha256=REPORT_SHA, source_sha256=WINDOW_SHA,
        deadline_epoch=admission["deadline_epoch"], hard_cap_seconds=10800,
        acceptance_requires="SUCCESS_CANDIDATE_ONLY_UNTIL_PROCESS_EXIT0_AND_NO_TERMINAL_FAILURE_RECEIPT",
        external_root_hardcap_required=True, final_exit_reserve_seconds=1,
        atomic_process_exit_or_storage_durability_guaranteed=False)
    require(all(terminal.get(key) == value for key, value in terminal_expected.items()), "native terminal0 lineage differs")
    require(type(terminal["returncode"]) is int, "terminal code must be integer0")
    observation = terminal.get("observation_before_receipt_write", {})
    for key in ("spent_seconds", "whole_remaining_seconds", "absolute_remaining_seconds"):
        require(type(observation.get(key)) in (int, float) and math.isfinite(observation[key]) and observation[key] > 0,
                "native terminal time observation is incomplete")
    require(observation["spent_seconds"] < 10800 and observation["whole_remaining_seconds"] > 1
            and observation["absolute_remaining_seconds"] > 1, "native terminal exceeded its original time window")
    root_expected = dict(schema="ROOT_GPT2_FULL_CLOSURE_V1", report_path=REPORT_REL,
        report_sha256=REPORT_SHA, terminal_sha256=TERMINAL_SHA, actual_parent_exit=0,
        primary_report_returncode=9, primary_report_status=report["status"], terminal_returncode=0,
        terminal_status=terminal["status"], raw_recount=True, counts=shared.COUNTS, choices=67106,
        host_gpu_compute_query_exit=0, host_competing_compute_pids=[], worker_cleanup_complete=True,
        worker_returncode=0, training=False, checkpoint_writes=0)
    require(all(audit.get(key) == value for key, value in root_expected.items()), "root actual exit0/cleanup receipt differs")
    require(type(audit["actual_parent_exit"]) is int and audit.get("report_bytes") == path.stat().st_size,
            "actual parent exit or native report bytes differ")
    proof = report.get("model_proof", {})
    require(proof.get("owned_pid") in audit.get("owned_host_pids_absent", []), "root did not close this worker PID")
    for key in ("monotonic_wall_seconds", "calendar_elapsed_seconds"):
        require(type(audit.get(key)) in (int, float) and math.isfinite(audit[key]) and 0 < audit[key] < 10800,
                "original root wall observations exceed10800s")
    for key in ("started_at", "ended_at"):
        require(audit.get(key) == report.get(key), "root/native original timestamps differ")
    begin, end = (datetime.fromisoformat(report[key]) for key in ("started_at", "ended_at"))
    require(begin.tzinfo is not None and end.tzinfo is not None
            and begin <= end and end.timestamp() < admission["deadline_epoch"], "original aware08:40 time bounds differ")
    assets, spec = report.get("assets", {}), window.native.REGISTRY[MODEL]
    require(assets == dict(model=MODEL, path=str(root / spec["path"]),
        **{key: spec[key] for key in ("architecture", "revision", "bytes", "sha256")},
        acquisition_manifest_sha256=assets.get("acquisition_manifest_sha256")), "original GPT2 Q4 asset contract differs")
    asset_manifest = evidence.json(root / Path(spec["path"]).parent / "manifest.json", assets["acquisition_manifest_sha256"])
    require(all(asset_manifest.get(key) == spec[key] for key in ("revision", "bytes"))
            and asset_manifest.get("sha256", "").upper() == spec["sha256"], "GPT2 acquisition receipt differs")
    # Model weight bodies are not consumed by statistics; original root/full provenance owns them.
    for mode, sha in ORIGINAL_PINS.items():
        evidence.json(root / "test_result/evidence" / window.native.TAG / MODEL / mode / "report.json", sha)
    try:
        verify_strict_numerical(report)
        prior = verify_original_prerequisites(source["window"], assets)
    except (window.AdmissionHold, KeyError, TypeError) as exc:
        raise ValueError("strict original numerical/prerequisite closure failed") from exc
    require(report.get("prerequisites") == prior, "original canary/cost/HOLD chain differs")
    for name, manifest in report["sample_manifests"].items():
        require(manifest.get("lineage") == dict(tag=window.native.TAG, model=MODEL, task=name, mode="full"),
                "native inner manifest must retain the frozen native-v2 origin tag")
    return path, report, dict(root_audit=audit, terminal=terminal, primary_returncode=9,
        primary_status=report["status"], actual_parent_exit=0, native_policy=report["policy"],
        current_model_weight_bodies_read=False, time_difference_cause=audit.get("clock_difference_cause"))


def collect(source, *, root=ROOT):
    evidence = Evidence()
    native_path, native_report, closure = native_bundle(source, evidence, root)
    reports = {}
    for peer in PEERS:
        path = shared.report_path(peer, root)
        if not path.is_file():
            raise shared.IncompleteFull("existing fixed peer full is not closed: " + peer)
        report = evidence.json(path)
        admit_peer(peer, report)
        reports[peer] = (path, report)
    tasks, task_proof = read_tasks(evidence.inputs)
    from scripts.p106b_official_tasks import task_requests
    contracts = {name: CaseContracts(tasks[name], shared.COUNTS[name], task_requests) for name in shared.PRIMARY}
    reports[MODEL] = (native_path, native_report)
    models, correspondence = {}, None
    for model, (path, report) in reports.items():
        counted = recount_model(model, path, report, tasks, evidence.inputs, task_requests, contracts)
        if correspondence is None:
            correspondence = counted["correspondence"]
        require(counted["correspondence"] == correspondence,
                "full ordered document/prompt/choices/gold correspondence differs")
        require(counted["rows"] == 19965 and counted["choice_likelihoods"] == 67106,
                "each original full must contain19965 rows and67106 choices")
        models[model] = counted
    pairs = {peer + "__" + MODEL: dict(left_model=peer, right_model=MODEL,
        **paired_intervals(models[peer]["values"], models[MODEL]["values"], draws=RESAMPLES, seed=SEED)) for peer in PEERS}
    require(len(pairs) == 7, "only the seven new GPT2 pairs are part of this analysis")
    summaries = {model: {key: value for key, value in counted.items() if key != "values"} for model, counted in models.items()}
    def final_check():
        require(source_identity() == source, "paired adapter/frozen source changed during execution")
        return evidence.unchanged()
    final_check()
    return dict(models=summaries, pairs=pairs, native_closure=closure, task_proof=task_proof,
        ordered_correspondence=correspondence, primary_metrics=shared.PRIMARY, task_counts=shared.COUNTS,
        input_files=evidence.inputs.files, source_unchanged=True, inputs_unchanged=True,
        interpretation=SCOPE, posthoc_after_observed_scores=True, existing21_pairs_recomputed=False,
        resamples=RESAMPLES, seed=SEED, multiple_comparisons_corrected=False,
        native_primary_report_modified=False, model_weight_bodies_read=False), final_check


def output_path(stamp, root=ROOT):
    require(isinstance(stamp, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_\-]{0,79}", stamp), "safe explicit output stamp required")
    target = Path(root) / "test_result/evidence" / TAG / stamp
    if target.exists() or any(path.is_symlink() for path in (target, *target.parents)):
        raise FileExistsError("prior/partial/linked output is preserved")
    return target


def veto(target, source_sha, error):
    if target is None:
        return
    try:
        path = Path(target) / "terminal_failure_receipt.json"
        require(not any(part.is_symlink() for part in (path, *path.parents)),
                "linked veto path is preserved; never follow it for failure storage")
        if path.exists():
            previous = read_json(path)
            require(previous.get("schema") == SCHEMA and previous.get("tag") == TAG
                    and previous.get("status") == "CPU_TERMINAL_VETO" and previous.get("returncode") == 9
                    and previous.get("source_sha256") == source_sha, "existing foreign veto is preserved")
            return  # Preserve the first cause without replacing or obscuring it.
        write_json(path, dict(schema=SCHEMA, tag=TAG,
            status="CPU_TERMINAL_VETO", returncode=9, source_sha256=source_sha,
            error_type=type(error).__name__, error=str(error)[:2000],
            scope="FAIL_CLOSED; MAY_FINISH_AFTER_BUDGET; NEVER_A_COMPLETION_CERTIFICATE"))
    except BaseException as closure_error:
        print(canonical(dict(event="CPU_VETO_STORAGE_ERROR", original_type=type(error).__name__,
            original_error=str(error)[:1000], closure_error=str(closure_error)[:1000])).decode(), file=sys.stderr, flush=True)


def bounded_run(expected_source, *, target=None, max_wall_sec=120, clock=time.monotonic):
    started, started_at = clock(), datetime.now(timezone.utc).isoformat()
    def budget():
        elapsed = clock() - started
        require(type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0, "invalid monotonic CPU observation")
        if elapsed >= max_wall_sec - 1:
            raise TimeoutError("whole CPU reservation, including report/terminal write and readback, is exhausted")
        return elapsed
    reserved, report = False, dict(schema=SCHEMA, tag=TAG, returncode=9, status="STARTED",
        source_sha256=expected_source, started_at=started_at, models_loaded=0, gpu_calls=0,
        optimizer_updates=0, checkpoint_writes=0, quality_claim=False, adoption_decision=False,
        external_root_hardcap_required=True, actual_process_exit0_required=True,
        supervisor_environment_is_not_observed_control_proof=True, atomic_process_exit_or_storage_guaranteed=False)
    try:
        with shared.cpu_wall_limit(max_wall_sec):
            require(os.environ.get(SUPERVISOR_ENV) == "1", "root external120s supervisor acknowledgement is required")
            source = source_identity()
            require(source["sha256"] == expected_source, "source-only pin differs")
            report["source_identity"] = source
            if target is not None:
                target = Path(target)
                if target.exists() or any(path.is_symlink() for path in (target, *target.parents)):
                    raise FileExistsError("prior output is preserved")
                target.mkdir(parents=True, exist_ok=False)
                reserved = True
            counted, final_check = collect(source)
            report.update(counted, status=PENDING, candidate_status=COMPLETE, candidate_returncode=0,
                cpu_wall_cap_seconds=max_wall_sec, elapsed_before_report=budget(),
                peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
            result = dict(status="CPU_READ_ONLY_COMPLETE_NOT_PERSISTED", returncode=0, pairs=7,
                source_sha256=expected_source, adoption_allowed=False, root_actual_exit0_required=True)
            if reserved:
                close_report(target / "report.json", report)
                budget()
                fallback = target / "report_closure_failure.json"
                require(not (fallback.exists() or fallback.is_symlink()), "report fallback is not a closed result")
                require(read_json(target / "report.json") == report, "report closed readback differs")
                final_check()
                report_sha = digest(target / "report.json")
                terminal = dict(schema=SCHEMA, tag=TAG, status=COMPLETE, returncode=0,
                    source_sha256=expected_source, report_sha256=report_sha,
                    report_returncode=9, report_status=PENDING, observed_elapsed_before_terminal=budget(),
                    cpu_wall_cap_seconds=max_wall_sec, actual_process_exit0_required=True,
                    external_root_hardcap_required=True, acceptance="TERMINAL_PLUS_REAL_EXIT0_PLUS_NO_VETO",
                    atomic_process_exit_or_storage_guaranteed=False)
                write_json(target / "terminal_receipt.json", terminal)
                budget()
                require(read_json(target / "terminal_receipt.json") == terminal
                        and digest(target / "report.json") == report_sha, "terminal/report final readback differs")
                final_check()
                failure = target / "terminal_failure_receipt.json"
                require(not (failure.exists() or failure.is_symlink()), "terminal veto forbids adoption")
                result.update(status=COMPLETE, report_sha256=report_sha, terminal_receipt_verified=True,
                              output=str(target), adoption_allowed="ROOT_ACTUAL_EXIT0_AND_HARDCAP_STILL_REQUIRED")
            budget()
        budget()
        return result, budget
    except BaseException as exc:
        if reserved:
            if not (target / "report.json").exists():
                report.update(status="CPU_RECOUNT_FAILED", returncode=8 if isinstance(exc, shared.IncompleteFull) else 9,
                              error_type=type(exc).__name__, error=str(exc)[:2000])
                try:
                    close_report(target / "report.json", report, primary_error=exc)
                except BaseException as storage_error:
                    print(canonical(dict(event="CPU_REPORT_STORAGE_ERROR", original_error=str(exc)[:1000],
                        storage_error=str(storage_error)[:1000])).decode(), file=sys.stderr, flush=True)
            veto(target, expected_source, exc)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-only", action="store_true")
    mode.add_argument("--read-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--source-sha256")
    parser.add_argument("--output-stamp")
    parser.add_argument("--max-wall-sec", type=int, default=120)
    args = parser.parse_args(argv)
    if args.check_only:
        print(canonical(dict(schema=SCHEMA, tag=TAG, status="SOURCE_ONLY", source_identity=source_identity(),
            peers=list(PEERS), native_model=MODEL, resamples=RESAMPLES, seed=SEED,
            raw_reads=0, models_loaded=0, gpu_calls=0, evidence_writes=0)).decode())
        return 0
    if args.source_sha256 is None or args.execute and not args.output_stamp or args.read_only and args.output_stamp:
        parser.error("source pin is required; execute needs a new output stamp; read-only has no output")
    target = None
    try:
        target = output_path(args.output_stamp) if args.execute else None
        result, budget = bounded_run(args.source_sha256, target=target, max_wall_sec=args.max_wall_sec)
        print(canonical(dict(**result, models_loaded=0, gpu_calls=0, quality_claim=False)).decode(), flush=True)
        budget()
        return 0
    except BaseException as exc:
        if target is not None and target.is_dir() and not isinstance(exc, FileExistsError):
            veto(target, args.source_sha256, exc)
        code = 8 if isinstance(exc, shared.IncompleteFull) else 9
        print(canonical(dict(status="INCOMPLETE_FULL_HOLD" if code == 8 else "CPU_NATIVE_PAIRS_ERROR",
            returncode=code, error_type=type(exc).__name__, error=str(exc)[:2000], models_loaded=0, gpu_calls=0)).decode(), file=sys.stderr)
        return code


if __name__ == "__main__":
    raise SystemExit(main())
