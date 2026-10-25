#!/usr/bin/env python3
"""Independent IQ2 full-window controller; execution needs new user authority.

The caller must supply an aware deadline, whole-phase cap, source pin and the
original run log explicitly. These inputs record a separately authorized window;
they do not grant permission to run a model. Native v2's original 7200s HOLD and
GPT2's 10800s controller are immutable. Source-only imports open no model.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shlex
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_native_core6 as native
from scripts import p106b_native_window as window
from scripts.p106b_shards import verify as verify_shards
from scripts import p106b_native_iq2_worker_window as worker_window

TAG = "p106b_native_iq2_window_v2_s1337"
SCHEMA = "P106B_NATIVE_IQ2_FULL_WINDOW_V2"
MODEL, MODE = "qwen35_08b_iq2xxs", "full"
OUTPUT = ROOT / "test_result/evidence" / TAG
PRIOR_OUTPUT = native.OUTPUT
NATIVE_SHA = "42713A9E7A181896DAD0A10D0359BFA193264D9DAEF3445A05E970404995D2AD"
WORKER_SHA = "C2B5779556EF1A3467C44C2B6EF6C585AC90C7D4D1EE137B7009F1FB57C42DEC"
PRIOR = {
    "canary": "875557B8580434636A44F4DE34FE9DB7834842FF8321CA0EEA5CC19C6C76A66E",
    "cost": "4EAA4B50622B891D773654C8A97A3BC7CA340EF92E4559A082DFAC4D3D556C66",
    "full": "A98C442B7EE9FD213587C5B48E4D6BD99DAA217FE1A7A729DA85E42928E0B7A9",
}
PRIOR_LOG_SHA = "64D8B34D82C4833651E234562F62D576CA4B19A4527BDB2AC5979C760880D2E6"
SOURCES = ("scripts/p106b_native_iq2_window.py", "scripts/test_p106b_native_iq2_window.py",
    "scripts/p106b_native_window.py", "scripts/p106b_native_iq2_worker_window.py",
    "scripts/test_p106b_native_iq2_worker_window.py", "scripts/codex_smoke.py",
    "scripts/smoke_module.py", "scripts/smoke_execution_contract.py")
AdmissionHold = native.AdmissionHold
digest, read_json, close_report = native.digest, native.read_json, native.close_report
write_json, phase_wall_limit = native.write_json, native.support.phase_wall_limit
asset_identity, Worker = native.asset_identity, native.Worker
original_prerequisites = native.prerequisites
# These reuse the frozen scoring/worker entry points without replacing globals.
model_runtime, idle_admission = window.model_runtime, window.idle_admission
CLOSURE_RESERVE, EXIT_RESERVE = 30, 1


def require(condition, message):
    if not condition:
        raise AdmissionHold(message)


def now_epoch():
    return time.time()


def monotonic_now():
    return time.monotonic()


def remaining(admission, began):
    spent = monotonic_now() - began
    return dict(spent_seconds=spent, whole_remaining_seconds=admission["hard_cap_seconds"] - spent,
        absolute_remaining_seconds=admission["deadline_epoch"] - now_epoch())


def remaining_seconds(admission, began):
    value = remaining(admission, began)
    return min(value["whole_remaining_seconds"], value["absolute_remaining_seconds"])


def check_end(admission, began, stage, *, reserve=0):
    observation = dict(stage=stage, **remaining(admission, began), required_reserve_seconds=reserve)
    if min(observation["whole_remaining_seconds"], observation["absolute_remaining_seconds"]) <= reserve:
        raise TimeoutError("whole IQ2 window/absolute deadline exhausted at " + stage)
    return observation


def work_budget(admission, began):
    available = remaining_seconds(admission, began) - CLOSURE_RESERVE
    require(available > 0, "no positive IQ2 work budget after evidence/cleanup reserve")
    return available


def admit_remaining(prior, admission, began, stage, report):
    forecast = prior.get("forecast_seconds")
    require(type(forecast) in (int, float) and math.isfinite(forecast) and forecast > 0,
        "positive original IQ2 forecast required")
    observation = dict(stage=stage, **remaining(admission, began), forecast_seconds=forecast,
        closure_reserve_seconds=CLOSURE_RESERVE, passed=False)
    report.setdefault("remaining_admission_checks", []).append(observation)
    available = min(observation["whole_remaining_seconds"], observation["absolute_remaining_seconds"])
    require(forecast + CLOSURE_RESERVE <= available,
        "spent+original IQ2 forecast+closure reserve exceeds explicit whole cap or deadline at " + stage)
    observation["passed"] = True


def identity():
    frozen = native.identity()
    require(frozen["sha256"] == NATIVE_SHA, "frozen native v2 identity differs")
    require(frozen["build"]["worker"] == "worker_v2_001" and frozen["build"]["worker_sha256"] == WORKER_SHA,
        "exact singleton worker identity differs")
    files = {name: digest(ROOT / name) for name in SOURCES}
    build = worker_window.build_identity(frozen)
    payload = dict(files=files, frozen_native_sha256=frozen["sha256"], worker_window_build=build)
    return dict(**payload, native_source_identity=frozen,
        sha256=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest().upper())


def validate_execution(model, mode, deadline, cap, *, now=None):
    require(model == MODEL and mode == MODE, "this owner admits only exact Qwen IQ2 full")
    require(type(cap) is int and CLOSURE_RESERVE + EXIT_RESERVE < cap <= worker_window.MAX_PARENT_CAP,
        "explicit positive whole-phase cap with closure/exit reserve required")
    try:
        parsed = datetime.fromisoformat(deadline)
    except (TypeError, ValueError) as exc:
        raise AdmissionHold("explicit ISO8601 deadline required") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, "aware deadline required")
    stop = parsed.timestamp()
    now = now_epoch() if now is None else now
    require(type(now) in (int, float) and math.isfinite(now) and math.isfinite(stop) and now + cap <= stop,
        "explicit whole IQ2 cap does not fit before the supplied deadline")
    return dict(deadline=parsed.isoformat(), deadline_epoch=stop, hard_cap_seconds=cap,
        authorization_scope="CALLER_SUPPLIED_NEW_WINDOW; NOT_PERMISSION_GRANTED_BY_CONTROLLER")


def check_closed_numerical(report):
    proof = report.get("model_proof", {})
    require(report.get("sources_unchanged") is True and report.get("source_assets_unchanged") is True,
        "original model/source exit verification is incomplete")
    require(proof.get("worker_cleanup_complete") is True and proof.get("worker_returncode") == 0
        and not proof.get("cleanup_error") and proof.get("telemetry_errors") == []
        and type(proof.get("resource_sample_count")) is int and proof["resource_sample_count"] > 0,
        "original owned-worker/resource closure is incomplete")
    require(report.get("gpu_idle_after_worker", {}).get("competing_compute_pids") == [],
        "original GPU post-exit point query is incomplete")
    info = proof.get("native_info", {})
    require(info.get("n_batch") == info.get("n_ubatch") == 1 and info.get("vocab_size") == 248320
        and info.get("architecture") == "qwen35" and info.get("context") == 1024,
        "original exact IQ2 singleton runtime identity differs")
    suite = report.get("numerical_canary", {})
    require(suite.get("passed") is True and suite.get("status") == "COMPLETE"
        and suite.get("atol") == native.ATOL and suite.get("rtol") == native.RTOL,
        "original strict numerical contract is incomplete")
    checks, comparisons = suite.get("checks", []), suite.get("comparisons", [])
    require(len(checks) == 6 and len(comparisons) == 19, "original numerical suite is incomplete")
    require(suite.get("boundary_input_tokens") == 1024 and suite.get("boundary_target_logits") == 2,
        "original1024 boundary proof differs")
    for row in comparisons:
        require(row.get("status") == "PASSED" and row.get("atol") == native.ATOL and row.get("rtol") == native.RTOL,
            "original comparison threshold/result differs")
        try:
            native.support.compare_scores(row["actual"], row["expected"])
        except (ValueError, TypeError, KeyError) as exc:
            raise AdmissionHold("original strict score oracle does not reproduce") from exc
    require(all(check.get("future_token", {}).get("passed") is True for check in checks),
        "original causal future-token proof is incomplete")


def recount_cost(cost, target):
    """Recount archived likelihood rows, not rerun tasks or reinterpret metrics."""
    expected = native.official.expected_counts("cost")
    manifests, audits = cost.get("sample_manifests", {}), cost.get("independent_audits", {})
    require(set(manifests) == set(audits) == set(expected), "all six original cost raw manifests/audits required")
    recount = {}
    for task, count in expected.items():
        manifest = manifests[task]
        require(manifest.get("lineage") == dict(tag=native.TAG, model=MODEL, task=task, mode="cost"),
            "original cost sample lineage differs: " + task)
        require(manifest.get("rows") == count and type(manifest.get("limit_bytes")) is int
            and 0 < manifest["limit_bytes"] <= native.MAX_BYTES, "bounded32-row original cost manifest required")
        try:
            verify_shards(target, manifest)
            rows = []
            for spec in manifest["shards"]:
                path = target / spec["path"]
                require(not any(parent.is_symlink() for parent in path.parents)
                    and path.stat().st_size < native.MAX_BYTES, "bounded regular original cost raw required")
                with path.open(encoding="utf-8") as stream:
                    rows.extend(json.loads(line) for line in stream)
            require([row.get("doc_id") for row in rows] == list(range(count)),
                "original cost raw denominator/order differs: " + task)
            choices = 0
            for row in rows:
                filtered, arguments, responses = row["filtered_resps"], row["arguments"], row["resps"]
                require(type(filtered) is list and len(filtered) > 0
                    and len(filtered) == len(arguments) == len(responses), "original cost choice accounting differs")
                for response in filtered:
                    require(type(response) is list and len(response) == 2
                        and type(response[0]) in (int, float) and math.isfinite(response[0])
                        and type(response[1]) is bool, "original cost likelihood is malformed/nonfinite")
                choices += len(filtered)
            recount[task] = dict(rows=len(rows), choice_likelihoods=choices)
            require(all(audits[task].get(key) == value for key, value in recount[task].items()),
                "original independent audit/raw recount differs: " + task)
        except AdmissionHold:
            raise
        except (ValueError, TypeError, KeyError, OSError) as exc:
            raise AdmissionHold("original cost raw verification failed: " + task) from exc
    require(sum(item["rows"] for item in recount.values()) == 192
        and sum(item["choice_likelihoods"] for item in recount.values()) == cost.get("choice_likelihoods") == 576,
        "complete original192-row/576-choice cost recount required")
    return dict(rows=192, choice_likelihoods=576, per_task=recount, raw_sha_verified=True,
        scope="ARCHIVED_RAW_COUNT_AND_HASH; ORIGINAL_OFFICIAL_METRIC_ORACLE_UNCHANGED")


def prior_run_exits(path, reports):
    """Read actual child exits from the archived log; no root-exit JSON exists."""
    require(path is not None, "explicit original --prior-run-log is required")
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and not any(p.is_symlink() for p in path.parents)
        and path.stat().st_size < native.MAX_BYTES, "bounded original run log required")
    require(digest(path) == PRIOR_LOG_SHA, "pinned original IQ2 run log differs")
    sections, current = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("[runlog] cmd="):
            argv = shlex.split(line[len("[runlog] cmd="):])
            def flag(name):
                return argv[argv.index(name) + 1]
            try:
                current = flag("--mode")
                require(current in PRIOR and current not in sections and "scripts/p106b_native_core6.py" in argv
                    and flag("--model") == MODEL and flag("--source-sha256") == NATIVE_SHA
                    and flag("--deadline") == reports[current]["admission"]["deadline"]
                    and int(flag("--max-wall-sec")) == reports[current]["admission"]["hard_cap_seconds"],
                    "original runlog command/source/window differs")
                sections[current] = dict(command=line[len("[runlog] cmd="):], summary=None, child_returncode=None)
            except (ValueError, IndexError, KeyError) as exc:
                raise AdmissionHold("original runlog phase command is malformed") from exc
        elif current is not None and line.startswith("{"):
            value = json.loads(line)
            if "event" not in value and value.get("mode") == current:
                require(sections[current]["summary"] is None, "duplicate original runlog phase summary")
                sections[current]["summary"] = value
        elif current is not None:
            match = re.match(r"^\[runlog\] 종료코드 (-?\d+)\s", line)
            if match:
                require(sections[current]["child_returncode"] is None, "duplicate original child exit")
                sections[current]["child_returncode"] = int(match.group(1))
    require(set(sections) == set(PRIOR), "all original phase actual exits required")
    for mode in ("canary", "cost"):
        evidence, report = sections[mode], reports[mode]
        summary = evidence["summary"] or {}
        require(evidence["child_returncode"] == 0 and summary.get("model") == MODEL
            and summary.get("status") == report["status"] and summary.get("wall_seconds") == report["wall_seconds"],
            "original canary/cost actual child exit0 or summary missing")
    require(sections["full"]["child_returncode"] == 1 and sections["full"]["summary"] is None,
        "preserved original full HOLD child exit1 differs")
    return dict(path=str(path.resolve()), sha256=PRIOR_LOG_SHA, phases=sections,
        evidence_kind="ORIGINAL_RUNLOG_ACTUAL_CHILD_EXITS; NOT_A_SEPARATE_ROOT_EXIT_JSON",
        separate_root_exit_json="NOT_AVAILABLE; NOT_SYNTHESIZED")


def prerequisites(signature, assets, prior_log):
    reports = {}
    for mode, expected in PRIOR.items():
        path = PRIOR_OUTPUT / MODEL / mode / "report.json"
        require(path.is_file() and not path.is_symlink() and not any(p.is_symlink() for p in path.parents)
            and path.stat().st_size < native.MAX_BYTES, "bounded original prerequisite report required: " + mode)
        require(digest(path) == expected, "pinned original report differs: " + mode)
        reports[mode] = read_json(path)
    frozen = signature["native_source_identity"]
    prior = original_prerequisites(MODEL, MODE, frozen, assets)
    require(prior["canary_report_sha256"] == PRIOR["canary"] and prior["cost_report_sha256"] == PRIOR["cost"],
        "original same-IQ2 canary/cost SHA chain differs")
    for mode in ("canary", "cost"):
        check_closed_numerical(reports[mode])
    cost = reports["cost"]
    require(cost.get("actual_counts") == native.official.expected_counts("cost")
        and cost.get("raw_independent_recount") is True, "original complete192-row raw recount required")
    hold = reports["full"]
    require(hold.get("status") == "NATIVE_PREREQUISITE_HOLD" and hold.get("returncode") == 9
        and hold.get("error_type") == "AdmissionHold" and "model_proof" not in hold
        and hold.get("admission", {}).get("hard_cap_seconds") == 7200
        and hold.get("source_identity") == frozen and hold.get("assets") == assets
        and hold.get("sources_unchanged") is True and hold.get("prerequisites") == prior,
        "preserved original HOLD must remain the7200s model-before-load budget decision")
    forecast = prior.get("forecast_seconds")
    require(type(forecast) in (int, float) and math.isfinite(forecast) and forecast > 7200,
        "positive original per-task IQ2 full forecast required")
    return dict(prior, original_full_hold_report_sha256=PRIOR["full"],
        original_report_paths={mode: str(PRIOR_OUTPUT / MODEL / mode / "report.json") for mode in PRIOR},
        original_cost_raw_recount=recount_cost(cost, PRIOR_OUTPUT / MODEL / "cost"),
        original_actual_exit_evidence=prior_run_exits(prior_log, reports))


def terminal_failure(target, context, error, primary=None):
    """Append an immutable veto even when closure has already exhausted the cap."""
    value = dict(schema=SCHEMA, tag=TAG, status="NATIVE_IQ2_WINDOW_TERMINAL_FAILURE", returncode=9,
        model=MODEL, mode=MODE, source_sha256=context["source_sha256"],
        observed_at=datetime.now(timezone.utc).isoformat(), **remaining(context["admission"], context["began"]),
        error_type=type(error).__name__, error=str(error)[:2000],
        original_error=None if primary is None else dict(type=type(primary).__name__, message=str(primary)[:2000]),
        record_scope="FAIL_CLOSED_VETO; MAY_BE_OUT_OF_BUDGET; NEVER_A_COMPLETION_CERTIFICATE")
    path = target / "terminal_failure_receipt.json"
    try:
        if path.exists():
            previous = read_json(path)
            if (previous.get("schema") == SCHEMA and previous.get("tag") == TAG
                    and previous.get("source_sha256") == context["source_sha256"]
                    and previous.get("status") == value["status"] and previous.get("returncode") == 9):
                return previous
            raise ValueError("existing terminal failure receipt is not this execution's valid veto")
        write_json(path, value)
    except BaseException as failure:
        print("[TERMINAL_FAILURE_RECEIPT_ERROR] " + json.dumps(dict(primary=value,
            receipt_error=dict(type=type(failure).__name__, message=str(failure)[:1000]))), file=sys.stderr, flush=True)
    return value


def seal_report(target, report, primary, admission, began, source_sha):
    """A verified receipt remains provisional until actual supervisor exit0."""
    desired_code, desired_status = report["returncode"], report["status"]
    context = dict(target=str(target), admission=admission, began=began, source_sha256=source_sha)
    if desired_code == 0:
        report.update(status="NATIVE_IQ2_WINDOW_COMPUTE_CLOSED_PENDING_TERMINAL", returncode=9,
            candidate_status=desired_status, candidate_returncode=0)
    report.update(ended_at_scope="PRE_REPORT_SERIALIZATION_SNAPSHOT_NOT_FINAL_PROCESS_END",
        terminal_acceptance="REQUIRE_TERMINAL_RECEIPT_PLUS_PROCESS_EXIT0_PLUS_NO_FAILURE_VETO_PLUS_ROOT_HARDCAP")
    try:
        check_end(admission, began, "before_report_write")
        close_report(target / "report.json", report, primary_error=primary)
        check_end(admission, began, "after_report_write")
        persisted = read_json(target / "report.json")
        check_end(admission, began, "after_report_readback")
        if ((target / "report_closure_failure.json").exists() or persisted.get("returncode") != report["returncode"]
                or persisted.get("report_closure_error")):
            raise ValueError("report closure/fallback did not preserve the candidate report")
        report_sha = digest(target / "report.json")
        check_end(admission, began, "after_report_hash", reserve=EXIT_RESERVE)
        receipt = dict(schema=SCHEMA, tag=TAG, status=desired_status, returncode=desired_code,
            model=MODEL, mode=MODE, report_sha256=report_sha, source_sha256=source_sha,
            observation_before_receipt_write=remaining(admission, began),
            deadline_epoch=admission["deadline_epoch"], hard_cap_seconds=admission["hard_cap_seconds"],
            acceptance_requires="SUCCESS_CANDIDATE_ONLY_UNTIL_PROCESS_EXIT0_AND_NO_TERMINAL_FAILURE_RECEIPT",
            external_root_hardcap_required=True, final_exit_reserve_seconds=EXIT_RESERVE,
            atomic_process_exit_or_storage_durability_guaranteed=False)
        write_json(target / "terminal_receipt.json", receipt)
        check_end(admission, began, "after_terminal_write", reserve=EXIT_RESERVE)
        actual = read_json(target / "terminal_receipt.json")
        end = check_end(admission, began, "after_terminal_readback", reserve=EXIT_RESERVE)
        if actual != receipt:
            raise ValueError("terminal receipt readback differs")
        return dict(status=desired_status, returncode=desired_code, terminal_receipt_verified=True,
            terminal_readback_end=end, _terminal_context=context)
    except BaseException as exc:
        terminal_failure(target, context, exc, primary)
        return dict(status="NATIVE_IQ2_WINDOW_TERMINAL_FAILURE", returncode=9, terminal_receipt_verified=False,
            terminal_error_type=type(exc).__name__, terminal_error=str(exc)[:2000], _terminal_context=context)


def execute(model, mode, expected_source, deadline, cap, prior_log):
    began = monotonic_now()
    admission = validate_execution(model, mode, deadline, cap, now=now_epoch())
    with phase_wall_limit(work_budget(admission, began)):
        signature = identity()
        require(signature["sha256"] == expected_source, "independent IQ2 window source pin differs")
        require(signature.get("worker_window_build", {}).get("status") == "READY",
            "별도 날짜 worker가 준비되지 않았습니다")
        require(admission["deadline_epoch"] <= signature["worker_window_build"]["deadline_epoch"],
            "요청 종료시각이 별도 worker의 승인 날짜를 넘었습니다")
        target = OUTPUT / model / mode
        require(not target.exists() and not target.is_symlink() and not any(p.is_symlink() for p in target.parents),
            "existing complete/partial IQ2 window output is preserved")
        target.mkdir(parents=True, exist_ok=False)
    report = dict(schema=SCHEMA, tag=TAG, model=model, mode=mode, status="STARTED", returncode=9,
        source_identity=signature, admission=admission, policy=native.policy(), quality_claim=False,
        training=False, optimizer_updates=0, checkpoint_writes=0, started_at=datetime.now(timezone.utc).isoformat(),
        execution_window_policy=dict(original_hard_cap_seconds=7200, hard_cap_seconds=cap,
            closure_reserve_seconds=CLOSURE_RESERVE, final_exit_reserve_seconds=EXIT_RESERVE,
            authorization="EXPLICIT_CALLER_WINDOW_INPUTS_DO_NOT_GRANT_EXECUTION_PERMISSION",
            external_root_hardcap="REQUIRED; CONFIGURATION_NOT_VERIFIED_BY_CONTROLLER",
            completion_contract="REPORT_ALONE_NEVER_FINAL; TERMINAL_RECEIPT_AND_PROCESS_EXIT0_AND_NO_FAILURE_VETO_REQUIRED",
            change_scope="NEW_IQ2_TIME_WINDOW_ONLY; SCIENTIFIC_CONTRACT_UNCHANGED",
            sample_manifest_origin_tag=native.TAG, sample_manifest_origin_schema=native.SCHEMA,
            owner_tag=TAG, lineage_scope="INNER_MANIFEST_TAG_IS_FROZEN_EVALUATOR_ORIGIN_NOT_THIS_WINDOW_TAG"))
    primary = None
    writer = runtime = assets = terminal = None
    try:
        with phase_wall_limit(work_budget(admission, began)):
            assets = asset_identity(model)
            report["assets"] = assets
            pre = prerequisites(signature, assets, prior_log)
            report["prerequisites"] = pre
            admit_remaining(pre, admission, began, "before_runtime", report)
            runtime = model_runtime()
            report.update(task_specs=runtime.specs, framework_provenance=runtime.provenance,
                framework_commit=runtime.framework_commit, data_manifest_sha256=runtime.data_manifest_sha256)
            report["gpu_idle_before_model"] = idle_admission(runtime)
            writer = runtime.writer(target, "native_wire")
            proof = {}
            report["model_proof"] = proof
            admit_remaining(pre, admission, began, "before_worker", report)
            stop = now_epoch() + remaining_seconds(admission, began) - CLOSURE_RESERVE
            with Worker(assets, signature["worker_window_build"]["build"], stop, writer, proof) as worker:
                lm = runtime.adapter(runtime.TemplateLM)(worker)
                report["numerical_canary"] = {}
                runtime.numerical(lm, runtime.torch, report["numerical_canary"])
                if report["numerical_canary"].get("passed") is not True:
                    raise ValueError("original strict full-phase numerical suite did not close")
                report["pre_evaluation_seconds"] = monotonic_now() - began
                runtime.evaluate(lm, target, report, runtime.tasks, MODE)
            if not proof.get("worker_cleanup_complete") or proof.get("worker_returncode") != 0 or proof.get("cleanup_error"):
                raise ValueError("owned singleton worker cleanup did not close cleanly")
            if proof.get("telemetry_errors") or not proof.get("resource_sample_count"):
                raise ValueError("owned worker resource observation did not close completely")
            if (report.get("actual_counts") != native.official.expected_counts(MODE)
                    or report.get("choice_likelihoods") != 67106 or report.get("raw_independent_recount") is not True):
                raise ValueError("original full19965/67106 accounting did not close")
            report.update(status="NATIVE_IQ2_WINDOW_FULL_COMPLETE", returncode=0)
    except BaseException as exc:
        primary = exc
        report.update(status="NATIVE_IQ2_WINDOW_PREREQUISITE_HOLD" if isinstance(exc, AdmissionHold) else "NATIVE_IQ2_WINDOW_ERROR",
            returncode=8 if isinstance(exc, AdmissionHold) else 9, error_type=type(exc).__name__, error=str(exc)[:2000])
        if "numerical_canary" in report and report["numerical_canary"].get("passed") is not True:
            report["numerical_canary"]["status"] = "FAILED"
    finally:
        def finalize():
            nonlocal primary
            failures = []
            def verify_exit(label, action):
                try:
                    action()
                except BaseException as exc:
                    failures.append(dict(check=label, type=type(exc).__name__, message=str(exc)[:1000]))
                check_end(admission, began, "after_" + label)
            def wire_close():
                if writer is not None and writer._total_rows:
                    report["wire_manifest"] = writer.close(lineage=dict(tag=TAG, model=model, mode=MODE, evaluator_origin_tag=native.TAG))
                    runtime.verify(target, report["wire_manifest"])
            verify_exit("wire_closure", wire_close)
            proof = report.get("model_proof", {})
            if proof.get("model_loaded") or proof.get("owned_pid"):
                verify_exit("idle_after_worker", lambda: report.update(gpu_idle_after_worker=runtime.idle()))
                def check_asset():
                    report["source_assets_unchanged"] = asset_identity(model) == assets
                    if not report["source_assets_unchanged"]:
                        raise ValueError("native model bytes changed")
                verify_exit("model_asset_after_worker", check_asset)
                if not proof.get("worker_cleanup_complete") or proof.get("worker_returncode") != 0 or proof.get("cleanup_error"):
                    failures.append(dict(check="worker_cleanup", type="RuntimeError", message="owned worker did not close cleanly"))
                if proof.get("telemetry_errors") or not proof.get("resource_sample_count"):
                    failures.append(dict(check="resource_observation", type="RuntimeError", message="resource observation missing/failed"))
            def check_sources():
                report["sources_unchanged"] = identity() == signature
                if not report["sources_unchanged"]:
                    raise ValueError("IQ2 window or frozen native source changed")
            verify_exit("source_exit", check_sources)
            def check_prior():
                report["original_prerequisites_unchanged"] = all(digest(PRIOR_OUTPUT / MODEL / item / "report.json") == sha
                    for item, sha in PRIOR.items())
                if not report["original_prerequisites_unchanged"]:
                    raise ValueError("original canary/cost/HOLD bytes changed")
                report["original_cost_raw_exit_recount"] = recount_cost(read_json(PRIOR_OUTPUT / MODEL / "cost/report.json"),
                    PRIOR_OUTPUT / MODEL / "cost")
                report["original_runlog_unchanged"] = digest(prior_log) == PRIOR_LOG_SHA
                if not report["original_runlog_unchanged"]:
                    raise ValueError("original actual-exit run log bytes changed")
            if "prerequisites" in report:
                verify_exit("original_evidence_exit", check_prior)
            else:
                report["original_prerequisite_exit_check"] = "NOT_RUN; ORIGINAL_REPORTS_NOT_ADMITTED"
            report.update(ended_at=datetime.now(timezone.utc).isoformat(), wall_seconds=monotonic_now() - began)
            if failures:
                report.update(status="NATIVE_IQ2_WINDOW_ERROR", returncode=9, exit_verification_errors=failures)
                if primary is None:
                    primary = RuntimeError("IQ2 window exit verification failed: " + failures[0]["check"])
                    report.update(error_type=failures[0]["type"], error=failures[0]["message"])
            return seal_report(target, report, primary, admission, began, signature["sha256"])
        try:
            available = remaining_seconds(admission, began)
            check_end(admission, began, "before_all_evidence_closure")
            with phase_wall_limit(available):
                terminal = finalize()
        except BaseException as exc:
            context = dict(target=str(target), admission=admission, began=began, source_sha256=signature["sha256"])
            terminal_failure(target, context, exc, primary)
            terminal = dict(status="NATIVE_IQ2_WINDOW_TERMINAL_FAILURE", returncode=9, terminal_receipt_verified=False,
                terminal_error_type=type(exc).__name__, terminal_error=str(exc)[:2000], _terminal_context=context)
    result = {key: report.get(key) for key in ("model", "mode", "error_type", "error", "exit_verification_errors")}
    result.update(terminal, wall_seconds=monotonic_now() - began)
    if result.get("terminal_receipt_verified"):
        try:
            check_end(admission, began, "before_execute_return", reserve=EXIT_RESERVE)
        except BaseException as exc:
            context = result["_terminal_context"]
            terminal_failure(target, context, exc, primary)
            result.update(status="NATIVE_IQ2_WINDOW_TERMINAL_FAILURE", returncode=9,
                terminal_receipt_verified=False, terminal_error_type=type(exc).__name__, terminal_error=str(exc)[:2000])
    return result


def supervise(args):
    began = time.monotonic()
    admission = validate_execution(args.model, args.mode, args.deadline, args.max_wall_sec)
    signature = identity()
    require(signature["sha256"] == args.source_sha256, "감독 시작 전 소스 신원이 다릅니다")
    build = signature.get("worker_window_build", {})
    require(build.get("status") == "READY", "별도 worker가 준비되지 않았습니다")
    require(admission["deadline_epoch"] <= build["deadline_epoch"], "별도 worker 날짜를 넘었습니다")
    require(not (OUTPUT / args.model / args.mode).exists(), "기존 전체·부분 평가를 보존합니다")
    child_cap = math.floor(min(args.max_wall_sec-(time.monotonic()-began),
        admission["deadline_epoch"]-now_epoch()) - worker_window.SUPERVISOR_RESERVE)
    require(child_cap > CLOSURE_RESERVE + EXIT_RESERVE, "자식 제어기의 남은 시간이 부족합니다")
    argv = [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()), "--execute",
        "--model", args.model, "--mode", args.mode, "--source-sha256", args.source_sha256,
        "--deadline", args.deadline, "--max-wall-sec", str(child_cap), "--prior-run-log", str(args.prior_run_log)]
    target = OUTPUT / args.model / args.mode
    def verify():
        require(not (target / "terminal_failure_receipt.json").exists(), "controller 종결 거부가 있습니다")
        receipt = worker_window.read_json(target / "terminal_receipt.json")
        require(receipt.get("schema") == SCHEMA and receipt.get("tag") == TAG and receipt.get("returncode") == 0
            and receipt.get("status") == "NATIVE_IQ2_WINDOW_FULL_COMPLETE"
            and receipt.get("model") == MODEL and receipt.get("mode") == MODE
            and receipt.get("source_sha256") == args.source_sha256
            and receipt.get("report_sha256") == digest(target / "report.json"), "controller 종결 신원이 다릅니다")
        return receipt
    return worker_window.supervise_process(argv, worker_binary=native.HEADERS / build["worker"],
        directory=OUTPUT / args.model / "supervisor", deadline_epoch=admission["deadline_epoch"],
        cap=args.max_wall_sec, verify_success=verify, started_monotonic=began, child_cap=child_cap)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    group.add_argument("--supervise", action="store_true")
    parser.add_argument("--model", choices=(MODEL,))
    parser.add_argument("--mode", choices=(MODE,))
    parser.add_argument("--source-sha256")
    parser.add_argument("--deadline")
    parser.add_argument("--max-wall-sec", type=int)
    parser.add_argument("--prior-run-log", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.execute or args.supervise:
            if any(getattr(args, name) is None for name in ("model", "mode", "source_sha256", "deadline", "max_wall_sec", "prior_run_log")):
                parser.error("execute requires explicit IQ2/full/source/new aware deadline/whole cap/original run log")
            result = supervise(args) if args.supervise else execute(args.model, args.mode, args.source_sha256,
                args.deadline, args.max_wall_sec, args.prior_run_log)
        else:
            result = dict(status="SOURCE_ONLY", returncode=0, models=0, backend_initializations=0, tag=TAG,
                source_identity=identity(), model=MODEL, mode=MODE, hard_cap_seconds="EXPLICIT_INPUT_REQUIRED",
                deadline="EXPLICIT_AWARE_INPUT_REQUIRED; NO_REUSE_OF_OLD_AUTHORIZATION", policy=native.policy(),
                original_evaluator_tag=native.TAG, prerequisite_report_sha256=PRIOR,
                original_run_log_sha256=PRIOR_LOG_SHA, runtime_permission="NOT_GRANTED_BY_CONTROLLER")
    except AdmissionHold as exc:
        result = dict(status="NATIVE_IQ2_WINDOW_PREREQUISITE_HOLD", returncode=8, model=args.model, mode=args.mode,
            model_load_attempted=False, error_type=type(exc).__name__, error=str(exc)[:2000])
    except Exception as exc:
        result = dict(status="NATIVE_IQ2_WINDOW_ERROR", returncode=9, model=args.model, mode=args.mode,
            error_type=type(exc).__name__, error=str(exc)[:2000])
    context = result.pop("_terminal_context", None)
    supervisor_context = result.pop("_supervisor_context", None)
    if supervisor_context is not None and result["returncode"] == 0:
        try:
            worker_window.check_supervisor_cli(supervisor_context, "before_cli_output")
        except BaseException as exc:
            result.update(status="SUPERVISOR_FAILURE", returncode=9,
                supervisor_terminal_error=dict(type=type(exc).__name__, message=str(exc)))
            worker_window.append_veto(supervisor_context["directory"], result)
    if context is not None and result["returncode"] != 9:
        result["requires_process_exit0_and_no_failure_veto"] = True
        try:
            check_end(context["admission"], context["began"], "before_cli_output", reserve=EXIT_RESERVE)
        except BaseException as exc:
            terminal_failure(Path(context["target"]), context, exc)
            result.update(status="NATIVE_IQ2_WINDOW_TERMINAL_FAILURE", returncode=9, terminal_error=str(exc)[:2000])
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
    if supervisor_context is not None and result["returncode"] == 0:
        try:
            worker_window.check_supervisor_cli(supervisor_context, "after_cli_output")
        except BaseException as exc:
            result.update(status="SUPERVISOR_FAILURE", returncode=9,
                supervisor_terminal_error=dict(type=type(exc).__name__, message=str(exc)))
            worker_window.append_veto(supervisor_context["directory"], result)
            print(json.dumps(dict(event="SUPERVISOR_TERMINAL_VETO", returncode=9,
                error_type=type(exc).__name__, error=str(exc)), ensure_ascii=False), flush=True)
            return 9
    if context is not None and result["returncode"] != 9:
        try:
            check_end(context["admission"], context["began"], "after_cli_output", reserve=EXIT_RESERVE)
        except BaseException as exc:
            terminal_failure(Path(context["target"]), context, exc)
            print(json.dumps(dict(event="NATIVE_IQ2_WINDOW_TERMINAL_VETO", returncode=9,
                error_type=type(exc).__name__, error=str(exc)[:2000])), flush=True)
            return 9
    return result["returncode"]


if __name__ == "__main__":
    raise SystemExit(main())
