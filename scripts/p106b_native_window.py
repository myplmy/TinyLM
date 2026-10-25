#!/usr/bin/env python3
"""GPT2-only 10800s full owner; frozen native v2 scoring is not modified.

Original canary/cost and the 7200s model-before-load HOLD remain untouched.
Inner sample manifests retain native v2's origin tag, not this owner's tag.
Source-only/check-only imports never initialize a backend or open a model.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_native_core6 as native

TAG = "p106b_native_window10800_v2_s1337"
SCHEMA = "P106B_NATIVE_FULL_WINDOW_V2"
MODEL, MODE, CAP = "gpt2_q4km", "full", 10800
OUTPUT = ROOT / "test_result/evidence" / TAG
NATIVE_SHA = "42713A9E7A181896DAD0A10D0359BFA193264D9DAEF3445A05E970404995D2AD"
WORKER_SHA = "C2B5779556EF1A3467C44C2B6EF6C585AC90C7D4D1EE137B7009F1FB57C42DEC"
PRIOR = {
    "canary": "BF7581832F8537F61B24E8043A6132004FC25449C29DDB6C5649B5F7D02DBDF0",
    "cost": "354A49E6D145F0057CAD7E95919B7E1625D283D9249B4D2E6F29A5828D26D595",
    "full": "570EE3E8292FB447895122F03A445ACDCB569455A3EF0DD9CA00424492DDB5A9",
}
SOURCES = ("scripts/p106b_native_window.py", "scripts/test_p106b_native_window.py")
AdmissionHold = native.AdmissionHold
digest, read_json, close_report = native.digest, native.read_json, native.close_report
write_json, phase_wall_limit = native.write_json, native.support.phase_wall_limit
asset_identity, Worker = native.asset_identity, native.Worker
CLOSURE_RESERVE, EXIT_RESERVE = 30, 1


def require(condition, message):
    if not condition: raise AdmissionHold(message)


def now_epoch():
    return time.time()


def monotonic_now():
    return time.monotonic()


def remaining(admission, began):
    spent = monotonic_now()-began
    return dict(spent_seconds=spent, whole_remaining_seconds=admission["hard_cap_seconds"]-spent,
        absolute_remaining_seconds=admission["deadline_epoch"]-now_epoch())


def remaining_seconds(admission, began):
    value = remaining(admission, began)
    return min(value["whole_remaining_seconds"], value["absolute_remaining_seconds"])


def check_end(admission, began, stage, *, reserve=0):
    observation = dict(stage=stage, **remaining(admission, began), required_reserve_seconds=reserve)
    if min(observation["whole_remaining_seconds"], observation["absolute_remaining_seconds"]) <= reserve:
        raise TimeoutError("whole window/absolute deadline exhausted at "+stage)
    return observation


def admit_remaining(prior, admission, began, stage, report):
    observation = dict(stage=stage, **remaining(admission, began), forecast_seconds=prior["forecast_seconds"],
        closure_reserve_seconds=CLOSURE_RESERVE, passed=False)
    report.setdefault("remaining_admission_checks", []).append(observation)
    native.support.admit_forecast(prior, admission, now=now_epoch())
    available = min(observation["whole_remaining_seconds"], observation["absolute_remaining_seconds"])
    require(prior["forecast_seconds"]+CLOSURE_RESERVE <= available,
        "spent+original forecast+closure reserve exceeds whole10800s or absolute deadline at "+stage)
    observation["passed"] = True


def terminal_failure(target, context, error, primary=None):
    """Best-effort append-only veto; never overwrite a report or success candidate.

    This failure record may itself finish after the budget. It never certifies
    in-budget work; a failed/absent seal or nonzero supervisor exit forbids PASS.
    """
    value = dict(schema=SCHEMA, tag=TAG, status="NATIVE_WINDOW_TERMINAL_FAILURE", returncode=9,
        model=MODEL, mode=MODE, source_sha256=context["source_sha256"],
        observed_at=datetime.now(timezone.utc).isoformat(), **remaining(context["admission"], context["began"]),
        error_type=type(error).__name__, error=str(error)[:2000],
        original_error=None if primary is None else dict(type=type(primary).__name__, message=str(primary)[:2000]),
        record_scope="FAIL_CLOSED_VETO; MAY_BE_OUT_OF_BUDGET; NEVER_A_COMPLETION_CERTIFICATE")
    path = target/"terminal_failure_receipt.json"
    try:
        if path.exists():
            previous = read_json(path)
            if (previous.get("schema") == SCHEMA and previous.get("tag") == TAG
                    and previous.get("source_sha256") == context["source_sha256"]
                    and previous.get("status") == "NATIVE_WINDOW_TERMINAL_FAILURE" and previous.get("returncode") == 9):
                return previous  # Preserve the first veto/cause; no repeated overwrite attempt.
            raise ValueError("existing terminal failure receipt is not this execution's valid veto")
        write_json(path, value)
    except BaseException as failure:
        print("[TERMINAL_FAILURE_RECEIPT_ERROR] "+json.dumps(dict(primary=value,
            receipt_error=dict(type=type(failure).__name__, message=str(failure)[:1000]))), file=sys.stderr, flush=True)
    return value


def seal_report(target, report, primary, admission, began, source_sha):
    """Write/read both artifacts within the remaining budget, then verify time.

    A receipt's own post-read time cannot be atomically embedded in that same
    immutable receipt. Success therefore ALSO requires process exit0 under the
    external root hardcap, and absence of a terminal-failure veto.
    """
    desired_code, desired_status = report["returncode"], report["status"]
    context = dict(target=str(target), admission=admission, began=began, source_sha256=source_sha)
    if desired_code == 0:
        report.update(status="NATIVE_WINDOW_COMPUTE_CLOSED_PENDING_TERMINAL", returncode=9,
            candidate_status=desired_status, candidate_returncode=0)
    report.update(ended_at_scope="PRE_REPORT_SERIALIZATION_SNAPSHOT_NOT_FINAL_PROCESS_END",
        terminal_acceptance="REQUIRE_TERMINAL_RECEIPT_PLUS_PROCESS_EXIT0_PLUS_NO_FAILURE_VETO_PLUS_ROOT_HARDCAP")
    try:
        check_end(admission, began, "before_report_write")
        close_report(target/"report.json", report, primary_error=primary)
        check_end(admission, began, "after_report_write")
        persisted = read_json(target/"report.json")
        check_end(admission, began, "after_report_readback")
        if ((target/"report_closure_failure.json").exists() or persisted.get("returncode") != report["returncode"]
                or persisted.get("report_closure_error")):
            raise ValueError("report closure/fallback did not preserve the candidate report")
        report_sha = digest(target/"report.json")
        check_end(admission, began, "after_report_hash", reserve=EXIT_RESERVE)
        receipt = dict(schema=SCHEMA, tag=TAG, status=desired_status, returncode=desired_code,
            model=MODEL, mode=MODE, report_sha256=report_sha, source_sha256=source_sha,
            observation_before_receipt_write=remaining(admission, began),
            deadline_epoch=admission["deadline_epoch"], hard_cap_seconds=admission["hard_cap_seconds"],
            acceptance_requires="SUCCESS_CANDIDATE_ONLY_UNTIL_PROCESS_EXIT0_AND_NO_TERMINAL_FAILURE_RECEIPT",
            external_root_hardcap_required=True, final_exit_reserve_seconds=EXIT_RESERVE,
            atomic_process_exit_or_storage_durability_guaranteed=False)
        write_json(target/"terminal_receipt.json", receipt)
        check_end(admission, began, "after_terminal_write", reserve=EXIT_RESERVE)
        actual = read_json(target/"terminal_receipt.json")
        end = check_end(admission, began, "after_terminal_readback", reserve=EXIT_RESERVE)
        if actual != receipt: raise ValueError("terminal receipt readback differs")
        return dict(status=desired_status, returncode=desired_code, terminal_receipt_verified=True,
            terminal_readback_end=end, _terminal_context=context)
    except BaseException as exc:
        terminal_failure(target, context, exc, primary)
        return dict(status="NATIVE_WINDOW_TERMINAL_FAILURE", returncode=9, terminal_receipt_verified=False,
            terminal_error_type=type(exc).__name__, terminal_error=str(exc)[:2000], _terminal_context=context)


def identity():
    frozen = native.identity()
    require(frozen["sha256"] == NATIVE_SHA, "frozen native v2 identity differs")
    require(frozen["build"]["worker"] == "worker_v2_001" and frozen["build"]["worker_sha256"] == WORKER_SHA,
        "exact singleton worker identity differs")
    files = {name: digest(ROOT/name) for name in SOURCES}
    payload = dict(files=files, frozen_native_sha256=frozen["sha256"])
    return dict(**payload, native_source_identity=frozen,
        sha256=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest().upper())


def validate_execution(model, mode, deadline, cap, *, now=None):
    require(model == MODEL and mode == MODE, "this owner admits only GPT2 full; Qwen is outside this window")
    require(type(cap) is int and cap == CAP, "the independently authorized whole-phase cap is exactly10800s")
    try: parsed = datetime.fromisoformat(deadline)
    except (TypeError, ValueError) as exc: raise AdmissionHold("explicit ISO8601 deadline required") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, "aware deadline required")
    stop = parsed.timestamp(); now = time.time() if now is None else now
    require(stop <= native.DEADLINE and now+cap <= stop, "whole10800s window does not fit before08:40KST")
    return dict(deadline=parsed.isoformat(), deadline_epoch=stop, hard_cap_seconds=cap)


def check_closed_numerical(report):
    proof = report.get("model_proof", {})
    require(report.get("sources_unchanged") is True and report.get("source_assets_unchanged") is True,
        "original model/source exit verification is not complete")
    require(proof.get("worker_cleanup_complete") is True and proof.get("worker_returncode") == 0
        and proof.get("telemetry_errors") == [] and type(proof.get("resource_sample_count")) is int
        and proof["resource_sample_count"] > 0, "original owned-worker/resource closure is incomplete")
    require(report.get("gpu_idle_after_worker", {}).get("competing_compute_pids") == [],
        "original GPU post-exit point query is incomplete")
    info = proof.get("native_info", {})
    require(info.get("n_batch") == info.get("n_ubatch") == 1 and info.get("vocab_size") == 50257,
        "original singleton runtime identity differs")
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
        try: native.support.compare_scores(row["actual"], row["expected"])
        except (ValueError, TypeError, KeyError) as exc: raise AdmissionHold("original strict score oracle does not reproduce") from exc
    require(all(check.get("future_token", {}).get("passed") is True for check in checks),
        "original causal future-token proof is incomplete")


def prerequisites(signature, assets):
    reports = {}
    for mode, expected in PRIOR.items():
        path = native.OUTPUT/MODEL/mode/"report.json"
        require(path.is_file() and not path.is_symlink() and path.stat().st_size < native.MAX_BYTES,
            "bounded original prerequisite report required: "+mode)
        require(digest(path) == expected, "pinned original report differs: "+mode)
        reports[mode] = read_json(path)
    frozen = signature["native_source_identity"]
    prior = native.prerequisites(MODEL, MODE, frozen, assets)
    require(prior["canary_report_sha256"] == PRIOR["canary"] and prior["cost_report_sha256"] == PRIOR["cost"],
        "original same-model canary/cost SHA chain differs")
    for mode in ("canary", "cost"): check_closed_numerical(reports[mode])
    cost = reports["cost"]
    require(cost.get("actual_counts") == native.official.expected_counts("cost")
        and cost.get("raw_independent_recount") is True, "original complete192-row raw recount required")
    hold = reports["full"]
    require(hold.get("status") == "NATIVE_PREREQUISITE_HOLD" and hold.get("returncode") == 9
        and hold.get("error_type") == "AdmissionHold" and "model_proof" not in hold
        and hold.get("admission", {}).get("hard_cap_seconds") == 7200
        and hold.get("source_identity") == frozen and hold.get("assets") == assets
        and hold.get("sources_unchanged") is True and hold.get("prerequisites") == prior,
        "the preserved original HOLD must be the7200s model-before-load budget decision")
    forecast = prior.get("forecast_seconds")
    require(type(forecast) in (int, float) and math.isfinite(forecast) and 7200 < forecast <= CAP,
        "original per-task full forecast does not fit this independent window")
    return dict(prior, original_full_hold_report_sha256=PRIOR["full"],
        original_report_paths={mode: str(native.OUTPUT/MODEL/mode/"report.json") for mode in PRIOR})


def model_runtime():
    for key, value in native.official.OFFLINE.items(): os.environ[key] = value
    import tinylm
    from scripts.prepare_p106b_official_eval import configure_hf_cache, COMMIT, MANIFEST_SHA
    configure_hf_cache()
    from scripts.p106b_official_tasks import load_tasks
    from scripts.interactive_research_infer import require_idle_gpu
    from scripts.p106b_shards import ShardWriter, verify
    from lm_eval.api.model import TemplateLM
    import torch
    torch.set_num_threads(4)
    tasks, specs, provenance = load_tasks()
    return SimpleNamespace(tasks=tasks, specs=specs, provenance=provenance, framework_commit=COMMIT,
        data_manifest_sha256=MANIFEST_SHA, idle=require_idle_gpu, writer=ShardWriter, verify=verify,
        adapter=native.adapter_type, TemplateLM=TemplateLM, torch=torch,
        numerical=native.numerical_canary, evaluate=native.evaluate_tasks)


def idle_admission(runtime):
    try: return runtime.idle()
    except RuntimeError as exc:
        # The pinned helper distinguishes an occupied GPU from NVML/parse errors
        # only in this explicit message. Tool errors remain genuine code9 errors.
        if str(exc).startswith("다른 GPU compute PID가 있습니다:"):
            raise AdmissionHold(str(exc)) from exc
        raise


def execute(model, mode, expected_source, deadline, cap):
    began = monotonic_now()
    admission = validate_execution(model, mode, deadline, cap, now=now_epoch())
    # Source verification and exclusive output admission also consume this cap.
    with phase_wall_limit(remaining_seconds(admission, began)-CLOSURE_RESERVE):
        signature = identity()
        require(signature["sha256"] == expected_source, "independent window source pin differs")
        target = OUTPUT/model/mode
        require(not target.exists() and not target.is_symlink() and not any(p.is_symlink() for p in target.parents),
            "existing complete/partial window output is preserved")
        target.mkdir(parents=True, exist_ok=False)
    report = dict(schema=SCHEMA, tag=TAG, model=model, mode=mode, status="STARTED", returncode=9,
        source_identity=signature, admission=admission, policy=native.policy(), quality_claim=False,
        training=False, optimizer_updates=0, checkpoint_writes=0, started_at=datetime.now(timezone.utc).isoformat(),
        execution_window_policy=dict(original_hard_cap_seconds=7200, hard_cap_seconds=CAP,
            closure_reserve_seconds=CLOSURE_RESERVE, final_exit_reserve_seconds=EXIT_RESERVE,
            external_root_hardcap="REQUIRED; CONFIGURATION_NOT_VERIFIED_BY_CONTROLLER",
            completion_contract="REPORT_ALONE_NEVER_FINAL; TERMINAL_RECEIPT_AND_PROCESS_EXIT0_AND_NO_FAILURE_VETO_REQUIRED",
            change_scope="ROOT_TIME_BUDGET_ONLY; SCIENTIFIC_CONTRACT_UNCHANGED",
            sample_manifest_origin_tag=native.TAG, sample_manifest_origin_schema=native.SCHEMA,
            owner_tag=TAG, lineage_scope="INNER_MANIFEST_TAG_IS_FROZEN_EVALUATOR_ORIGIN_NOT_THIS_WINDOW_TAG"))
    primary = None; writer = None; runtime = None; assets = None; terminal = None
    try:
        with phase_wall_limit(remaining_seconds(admission, began)-CLOSURE_RESERVE):
            assets = asset_identity(model); report["assets"] = assets
            pre = prerequisites(signature, assets); report["prerequisites"] = pre
            admit_remaining(pre, admission, began, "before_runtime", report)
            runtime = model_runtime()
            report.update(task_specs=runtime.specs, framework_provenance=runtime.provenance,
                framework_commit=runtime.framework_commit, data_manifest_sha256=runtime.data_manifest_sha256)
            report["gpu_idle_before_model"] = idle_admission(runtime)
            admit_remaining(pre, admission, began, "before_worker", report)
            writer = runtime.writer(target, "native_wire")
            proof = {}; report["model_proof"] = proof
            stop = now_epoch()+remaining_seconds(admission, began)-CLOSURE_RESERVE
            with Worker(assets, signature["native_source_identity"]["build"], stop, writer, proof) as worker:
                lm = runtime.adapter(runtime.TemplateLM)(worker)
                report["numerical_canary"] = {}
                runtime.numerical(lm, runtime.torch, report["numerical_canary"])
                if report["numerical_canary"].get("passed") is not True:
                    raise ValueError("original strict full-phase numerical suite did not close")
                report["pre_evaluation_seconds"] = monotonic_now()-began
                runtime.evaluate(lm, target, report, runtime.tasks, MODE)
            if not proof.get("worker_cleanup_complete") or proof.get("worker_returncode") != 0 or proof.get("cleanup_error"):
                raise ValueError("owned singleton worker cleanup did not close cleanly")
            if proof.get("telemetry_errors") or not proof.get("resource_sample_count"):
                raise ValueError("owned worker resource observation did not close completely")
            if (report.get("actual_counts") != native.official.expected_counts(MODE)
                    or report.get("choice_likelihoods") != 67106 or report.get("raw_independent_recount") is not True):
                raise ValueError("original full19965/67106 accounting did not close")
            report.update(status="NATIVE_WINDOW_FULL_COMPLETE", returncode=0)
    except BaseException as exc:
        primary = exc
        report.update(status="NATIVE_WINDOW_PREREQUISITE_HOLD" if isinstance(exc, AdmissionHold) else "NATIVE_WINDOW_ERROR",
            returncode=8 if isinstance(exc, AdmissionHold) else 9, error_type=type(exc).__name__, error=str(exc)[:2000])
        if "numerical_canary" in report and report["numerical_canary"].get("passed") is not True:
            report["numerical_canary"]["status"] = "FAILED"
    finally:
        def finalize():
            nonlocal primary
            failures = []
            def verify_exit(label, action):
                try: action()
                except BaseException as exc: failures.append(dict(check=label, type=type(exc).__name__, message=str(exc)[:1000]))
                check_end(admission, began, "after_"+label)
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
                    if not report["source_assets_unchanged"]: raise ValueError("native model bytes changed")
                verify_exit("model_asset_after_worker", check_asset)
                if not proof.get("worker_cleanup_complete") or proof.get("worker_returncode") != 0 or proof.get("cleanup_error"):
                    failures.append(dict(check="worker_cleanup", type="RuntimeError", message="owned worker did not close cleanly"))
                if proof.get("telemetry_errors") or not proof.get("resource_sample_count"):
                    failures.append(dict(check="resource_observation", type="RuntimeError", message="resource observation missing/failed"))
            def check_sources():
                report["sources_unchanged"] = identity() == signature
                if not report["sources_unchanged"]: raise ValueError("window or frozen native source changed")
            verify_exit("source_exit", check_sources)
            def check_prior():
                report["original_prerequisites_unchanged"] = all(digest(native.OUTPUT/MODEL/item/"report.json") == sha for item, sha in PRIOR.items())
                if not report["original_prerequisites_unchanged"]: raise ValueError("original canary/cost/HOLD bytes changed")
            if "prerequisites" in report: verify_exit("original_report_exit", check_prior)
            else: report["original_prerequisite_exit_check"] = "NOT_RUN; ORIGINAL_REPORTS_NOT_ADMITTED"
            report.update(ended_at=datetime.now(timezone.utc).isoformat(), wall_seconds=monotonic_now()-began)
            if failures:
                report.update(status="NATIVE_WINDOW_ERROR", returncode=9, exit_verification_errors=failures)
                if primary is None:
                    primary = RuntimeError("window exit verification failed: "+failures[0]["check"])
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
            terminal = dict(status="NATIVE_WINDOW_TERMINAL_FAILURE", returncode=9, terminal_receipt_verified=False,
                terminal_error_type=type(exc).__name__, terminal_error=str(exc)[:2000], _terminal_context=context)
    result = {key: report.get(key) for key in ("model", "mode", "error_type", "error", "exit_verification_errors")}
    result.update(terminal, wall_seconds=monotonic_now()-began)
    if result.get("terminal_receipt_verified"):
        try: check_end(admission, began, "before_execute_return", reserve=EXIT_RESERVE)
        except BaseException as exc:
            context = result["_terminal_context"]
            terminal_failure(target, context, exc, primary)
            result.update(status="NATIVE_WINDOW_TERMINAL_FAILURE", returncode=9,
                terminal_receipt_verified=False, terminal_error_type=type(exc).__name__, terminal_error=str(exc)[:2000])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(); group.add_argument("--check-only", action="store_true"); group.add_argument("--execute", action="store_true")
    parser.add_argument("--model", choices=(MODEL,)); parser.add_argument("--mode", choices=(MODE,))
    parser.add_argument("--source-sha256"); parser.add_argument("--deadline"); parser.add_argument("--max-wall-sec", type=int)
    args = parser.parse_args(argv)
    try:
        if args.execute:
            if any(getattr(args, name) is None for name in ("model", "mode", "source_sha256", "deadline", "max_wall_sec")):
                parser.error("execute requires explicit GPT2/full/source/deadline/whole10800s cap")
            result = execute(args.model, args.mode, args.source_sha256, args.deadline, args.max_wall_sec)
        else:
            result = dict(status="SOURCE_ONLY", returncode=0, models=0, backend_initializations=0, tag=TAG,
                source_identity=identity(), model=MODEL, mode=MODE, hard_cap_seconds=CAP, policy=native.policy(),
                original_evaluator_tag=native.TAG, prerequisite_report_sha256=PRIOR)
    except AdmissionHold as exc:
        result = dict(status="NATIVE_WINDOW_PREREQUISITE_HOLD", returncode=8, model=args.model, mode=args.mode,
            model_load_attempted=False, error_type=type(exc).__name__, error=str(exc)[:2000])
    except Exception as exc:
        result = dict(status="NATIVE_WINDOW_ERROR", returncode=9, model=args.model, mode=args.mode,
            error_type=type(exc).__name__, error=str(exc)[:2000])
    context = result.pop("_terminal_context", None)
    if context is not None and result["returncode"] != 9:
        result["requires_process_exit0_and_no_failure_veto"] = True
        try: check_end(context["admission"], context["began"], "before_cli_output", reserve=EXIT_RESERVE)
        except BaseException as exc:
            terminal_failure(Path(context["target"]), context, exc)
            result.update(status="NATIVE_WINDOW_TERMINAL_FAILURE", returncode=9, terminal_error=str(exc)[:2000])
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
    if context is not None and result["returncode"] != 9:
        try: check_end(context["admission"], context["began"], "after_cli_output", reserve=EXIT_RESERVE)
        except BaseException as exc:
            terminal_failure(Path(context["target"]), context, exc)
            print(json.dumps(dict(event="NATIVE_WINDOW_TERMINAL_VETO", returncode=9,
                error_type=type(exc).__name__, error=str(exc)[:2000])), flush=True)
            return 9
    return result["returncode"]


if __name__ == "__main__": raise SystemExit(main())
