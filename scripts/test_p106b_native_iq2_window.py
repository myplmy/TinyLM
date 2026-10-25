"""CPU synthetic controller tests; real worker, model and GPU queries stay absent."""
from __future__ import annotations

import ast
import builtins
from contextlib import ExitStack, nullcontext, redirect_stdout
import copy
from datetime import datetime
import io
import json
from pathlib import Path
import runpy
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import p106b_native_iq2_window as run
from scripts.p106b_shards import ShardWriter, verify


CAP = 17400
FORECAST = 15313.504361207166
DEADLINE = "2026-10-25T13:00:00+09:00"
STOP = datetime.fromisoformat(DEADLINE).timestamp()
ORIGINAL_DEADLINE = "2026-10-24T08:40:00+09:00"


def strict_receipt():
    comparison = dict(status="PASSED", atol=run.native.ATOL, rtol=run.native.RTOL,
        actual=[[-2., False]], expected=[[-2., False]])
    return dict(passed=True, status="COMPLETE", atol=run.native.ATOL, rtol=run.native.RTOL,
        boundary_input_tokens=1024, boundary_target_logits=2,
        checks=[dict(future_token=dict(passed=True)) for _ in range(6)],
        comparisons=[copy.deepcopy(comparison) for _ in range(19)])


class IQ2WindowContracts(unittest.TestCase):
    def setUp(self):
        self.frozen = dict(sha256=run.NATIVE_SHA,
            build=dict(worker="worker_v2_001", worker_sha256=run.WORKER_SHA))
        self.window_build = dict(status="READY", deadline_epoch=STOP, worker="synthetic_window/worker",
            build=dict(worker="synthetic_window/worker", worker_sha256="SYNTHETIC_DERIVED_WORKER"))
        self.build_patch = patch.object(run.worker_window, "build_identity", return_value=self.window_build)
        self.build_patch.start(); self.addCleanup(self.build_patch.stop)
        self.signature = dict(sha256="SYNTHETIC_OWNER_SOURCE", native_source_identity=self.frozen,
            worker_window_build=self.window_build)
        spec = run.native.REGISTRY[run.MODEL]
        self.assets = dict(model=run.MODEL, **spec, fixture="SYNTHETIC_NOT_OPENED_MODEL")

    def original_fixture(self, directory):
        """Make independent synthetic receipts/raw/log with no archived data access."""
        base = directory / "original"
        prior = dict(canary_report_sha256="", cost_report_sha256="", forecast_seconds=FORECAST,
            forecast_policy="PER_TASK_FIRST32_X1.3_PLUS_MEASURED_STARTUP_PLUS60; ESTIMATE_ONLY")
        reports = {}
        for mode, status, code in (("canary", "NATIVE_CANARY_COMPLETE", 0),
                ("cost", "NATIVE_LIMITED_COST_DIAGNOSTIC", 0), ("full", "NATIVE_PREREQUISITE_HOLD", 9)):
            target = base / run.MODEL / mode
            target.mkdir(parents=True)
            report = dict(schema=run.native.SCHEMA, tag=run.native.TAG, model=run.MODEL, mode=mode,
                status=status, returncode=code, source_identity=self.frozen, assets=self.assets,
                policy=run.native.policy(), sources_unchanged=True, source_assets_unchanged=True,
                wall_seconds={"canary": 11.182512081002642, "cost": 113.93783275500027, "full": .2}[mode],
                admission=dict(deadline=ORIGINAL_DEADLINE, hard_cap_seconds=7200 if mode == "full" else 600))
            if mode != "full":
                report.update(numerical_canary=strict_receipt(),
                    model_proof=dict(worker_cleanup_complete=True, worker_returncode=0, telemetry_errors=[],
                        resource_sample_count=16, native_info=dict(n_batch=1, n_ubatch=1,
                            vocab_size=248320, architecture="qwen35", context=1024)),
                    gpu_idle_after_worker=dict(competing_compute_pids=[]))
            if mode == "cost":
                report.update(actual_counts=run.native.official.expected_counts("cost"), choice_likelihoods=576,
                    raw_independent_recount=True, sample_manifests={}, independent_audits={})
                for task in report["actual_counts"]:
                    writer = ShardWriter(target, task + "_samples")
                    choice_count = 2 if task in ("piqa", "winogrande", "boolq") else 4
                    for index in range(32):
                        writer.append(dict(doc_id=index, filtered_resps=[[-2., False]] * choice_count,
                            arguments=[["synthetic context", " synthetic target"]] * choice_count,
                            resps=[[[-2., False]]] * choice_count))
                    report["sample_manifests"][task] = writer.close(lineage=dict(tag=run.native.TAG,
                        model=run.MODEL, task=task, mode="cost"))
                    report["independent_audits"][task] = dict(rows=32, choice_likelihoods=32 * choice_count)
            if mode == "full":
                report.update(error_type="AdmissionHold", error="measured full forecast exceeds phase budget or deadline",
                    prerequisites=dict(prior))
            run.write_json(target / "report.json", report)
            if mode == "canary":
                prior["canary_report_sha256"] = run.digest(target / "report.json")
            if mode == "cost":
                prior["cost_report_sha256"] = run.digest(target / "report.json")
            reports[mode] = report
        pins = {mode: run.digest(base / run.MODEL / mode / "report.json") for mode in reports}
        lines = []
        for mode in reports:
            cap = 7200 if mode == "full" else 600
            lines.append("[runlog] cmd=/synthetic/python -B -X utf8 scripts/p106b_native_core6.py --execute"
                f" --model {run.MODEL} --mode {mode} --source-sha256 {run.NATIVE_SHA}"
                f" --deadline {ORIGINAL_DEADLINE} --max-wall-sec {cap}")
            if mode != "full":
                lines.append(json.dumps({key: reports[mode][key] for key in ("mode", "model", "status", "wall_seconds")}))
            lines.append("[runlog] 종료코드 " + ("1" if mode == "full" else "0") + "  소요 0.0분  (synthetic)")
        log = directory / "original_runlog.txt"
        log.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return SimpleNamespace(base=base, reports=reports, pins=pins, prior=prior, log=log, log_sha=run.digest(log))

    def test_explicit_new_aware_window_is_required_and_old_caps_are_unchanged(self):
        now = STOP - CAP
        admitted = run.validate_execution(run.MODEL, run.MODE, DEADLINE, CAP, now=now)
        self.assertEqual(admitted["hard_cap_seconds"], CAP)
        self.assertGreater(admitted["deadline_epoch"], run.native.DEADLINE)
        self.assertIn("NOT_PERMISSION", admitted["authorization_scope"])
        for model, mode, deadline, cap, instant in (
                ("gpt2_q4km", "full", DEADLINE, CAP, now),
                (run.MODEL, "cost", DEADLINE, CAP, now),
                (run.MODEL, "full", DEADLINE, None, now),
                (run.MODEL, "full", DEADLINE, True, now),
                (run.MODEL, "full", DEADLINE, 32.0, now),
                (run.MODEL, "full", DEADLINE, 31, now),
                (run.MODEL, "full", "2026-10-25T16:00:00", CAP, now),
                (run.MODEL, "full", "bad", CAP, now),
                (run.MODEL, "full", None, CAP, now),
                (run.MODEL, "full", DEADLINE, CAP, now + .01),
                (run.MODEL, "full", ORIGINAL_DEADLINE, CAP, now)):
            with self.subTest(deadline=deadline, cap=cap, instant=instant), self.assertRaises(run.AdmissionHold):
                run.validate_execution(model, mode, deadline, cap, now=instant)
        with self.assertRaises(run.AdmissionHold):
            run.native.validate_execution(run.MODEL, run.MODE, ORIGINAL_DEADLINE, CAP, now=run.native.DEADLINE-CAP)
        with self.assertRaises(run.AdmissionHold):
            run.window.validate_execution(run.MODEL, run.MODE, ORIGINAL_DEADLINE, 10800,
                now=run.native.DEADLINE-10800)

    def test_identity_reuses_native_source_worker_and_gpt2_runtime_without_mutation(self):
        with patch.object(run.native, "identity", return_value=self.frozen):
            signature = run.identity()
        self.assertEqual(signature["native_source_identity"], self.frozen)
        self.assertEqual(set(signature["files"]), set(run.SOURCES))
        self.assertIs(run.Worker, run.native.Worker)
        self.assertIs(run.model_runtime, run.window.model_runtime)
        self.assertIs(run.idle_admission, run.window.idle_admission)
        self.assertIs(run.original_prerequisites, run.native.prerequisites)
        tree = ast.parse(Path(run.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    self.assertFalse(isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                        and target.value.id in {"native", "window"}, "production must not replace frozen globals")
        for bad in (dict(self.frozen, sha256="CHANGED"), dict(self.frozen, build=dict(worker="other", worker_sha256=run.WORKER_SHA))):
            with patch.object(run.native, "identity", return_value=bad), self.assertRaises(run.AdmissionHold):
                run.identity()

    def test_import_check_only_and_help_have_no_heavy_import_asset_or_worker(self):
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers", "tokenizers", "datasets", "lm_eval", "tinylm"}:
                raise AssertionError("unexpected heavy import: " + name)
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded), patch.object(run, "identity", return_value=self.signature), \
                patch.object(run, "model_runtime") as runtime, patch.object(run, "Worker") as worker, \
                patch.object(run, "asset_identity") as assets:
            runpy.run_path(str(Path(run.__file__)), run_name="pure_iq2_import")
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(run.main(["--check-only"]), 0)
            proof = json.loads(output.getvalue())
            self.assertEqual((proof["models"], proof["backend_initializations"]), (0, 0))
            self.assertEqual(proof["runtime_permission"], "NOT_GRANTED_BY_CONTROLLER")
            self.assertEqual(proof["hard_cap_seconds"], "EXPLICIT_INPUT_REQUIRED")
            with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as caught:
                run.main(["--help"])
            self.assertEqual(caught.exception.code, 0)
            runtime.assert_not_called(); worker.assert_not_called(); assets.assert_not_called()

    def test_original_pins_raw_192_576_and_actual_child_exits_close_on_synthetic_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.original_fixture(Path(tmp))
            with patch.object(run, "PRIOR_OUTPUT", fixture.base), patch.object(run, "PRIOR", fixture.pins), \
                    patch.object(run, "PRIOR_LOG_SHA", fixture.log_sha), \
                    patch.object(run, "original_prerequisites", return_value=fixture.prior):
                result = run.prerequisites(self.signature, self.assets, fixture.log)
            self.assertEqual(result["forecast_seconds"], FORECAST)
            raw = result["original_cost_raw_recount"]
            self.assertEqual((raw["rows"], raw["choice_likelihoods"]), (192, 576))
            exits = result["original_actual_exit_evidence"]
            self.assertEqual([exits["phases"][mode]["child_returncode"] for mode in ("canary", "cost", "full")], [0, 0, 1])
            self.assertEqual(exits["separate_root_exit_json"], "NOT_AVAILABLE; NOT_SYNTHESIZED")
            self.assertNotIn("model_proof", fixture.reports["full"])

    def test_original_sha_source_postchecks_and_numeric_negatives_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.original_fixture(Path(tmp))
            with ExitStack() as stack:
                for name, value in (("PRIOR_OUTPUT", fixture.base), ("PRIOR", fixture.pins),
                        ("PRIOR_LOG_SHA", fixture.log_sha), ("original_prerequisites", lambda *_: fixture.prior)):
                    stack.enter_context(patch.object(run, name, value))
                with patch.object(run, "digest", return_value="CHANGED"), self.assertRaises(run.AdmissionHold):
                    run.prerequisites(self.signature, self.assets, fixture.log)
                for field in ("sources_unchanged", "source_assets_unchanged"):
                    report = copy.deepcopy(fixture.reports["cost"]); report[field] = False
                    with self.subTest(field=field), self.assertRaises(run.AdmissionHold):
                        run.check_closed_numerical(report)
                for key, bad in (("worker_cleanup_complete", False), ("worker_returncode", 9),
                        ("telemetry_errors", ["TimeoutError"]), ("resource_sample_count", 0), ("cleanup_error", "failed")):
                    report = copy.deepcopy(fixture.reports["canary"]); report["model_proof"][key] = bad
                    with self.subTest(key=key), self.assertRaises(run.AdmissionHold):
                        run.check_closed_numerical(report)
                for change in ("tolerance", "negative", "incomplete", "future", "gpt2_vocab"):
                    report = copy.deepcopy(fixture.reports["canary"]); suite = report["numerical_canary"]
                    if change == "tolerance": suite["atol"] = .1
                    if change == "negative": suite["comparisons"][0]["expected"][0][0] -= 1
                    if change == "incomplete": suite["comparisons"].pop()
                    if change == "future": suite["checks"][0]["future_token"]["passed"] = False
                    if change == "gpt2_vocab": report["model_proof"]["native_info"]["vocab_size"] = 50257
                    with self.subTest(change=change), self.assertRaises(run.AdmissionHold):
                        run.check_closed_numerical(report)

    def test_raw_hash_order_choice_and_manifest_lineage_negatives_hold(self):
        for change in ("bytes", "order", "choice", "lineage", "missing_task", "total"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                fixture = self.original_fixture(Path(tmp)); cost = copy.deepcopy(fixture.reports["cost"])
                target = fixture.base / run.MODEL / "cost"
                if change == "bytes":
                    path = target / cost["sample_manifests"]["piqa"]["shards"][0]["path"]
                    with path.open("a", encoding="utf-8") as stream: stream.write(" ")
                elif change in ("order", "choice"):
                    row = dict(doc_id=1 if change == "order" else 0,
                        filtered_resps=[[-2., False]], arguments=[["c", " t"]], resps=[[[-2., False]]])
                    writer = ShardWriter(target, "altered")
                    for index in range(32): writer.append(dict(row, doc_id=1 if change == "order" else index))
                    cost["sample_manifests"]["piqa"] = writer.close(lineage=dict(tag=run.native.TAG,
                        model=run.MODEL, task="piqa", mode="cost"))
                elif change == "lineage": cost["sample_manifests"]["piqa"]["lineage"]["model"] = "gpt2_q4km"
                elif change == "missing_task": cost["sample_manifests"].pop("piqa")
                else: cost["choice_likelihoods"] = 575
                with self.assertRaises(run.AdmissionHold): run.recount_cost(cost, target)

    def test_missing_or_bad_actual_exit_input_holds_without_fabricating_root_json(self):
        for change in ("missing", "bad_sha", "cost_exit", "full_exit", "source", "summary"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                fixture = self.original_fixture(Path(tmp)); log = fixture.log
                if change == "missing": log = None
                text = fixture.log.read_text(encoding="utf-8")
                if change == "cost_exit": text = text.replace("[runlog] 종료코드 0", "[runlog] 종료코드 7")
                if change == "full_exit": text = text.replace("[runlog] 종료코드 1", "[runlog] 종료코드 0")
                if change == "source": text = text.replace(run.NATIVE_SHA, "0" * 64)
                if change == "summary": text = text.replace("NATIVE_LIMITED_COST_DIAGNOSTIC", "NOT_COMPLETE")
                if change not in ("missing", "bad_sha"):
                    fixture.log.write_text(text, encoding="utf-8")
                pin = fixture.log_sha if change == "bad_sha" else run.digest(fixture.log)
                if change == "bad_sha":
                    with fixture.log.open("a", encoding="utf-8") as stream: stream.write("changed")
                with patch.object(run, "PRIOR_LOG_SHA", pin), self.assertRaises(run.AdmissionHold):
                    run.prior_run_exits(log, fixture.reports)
                self.assertEqual(list(Path(tmp).glob("*root*exit*.json")), [])

    def scenario(self, *, fault=None, cleanup_error=False, admission_hold=False, missing_choice=False,
            malformed_report=False, duplicate_report=False, changed_asset=False, changed_source=False,
            changed_prior=False, changed_raw=False, changed_log=False, late_on=None, deadline_axis="whole",
            readback_changed=False, preflight_spent=0, before_worker_spent=0, writer_spent=0,
            worker_rc=0, sample_count=1, telemetry_error=False):
        calls = []
        frozen_globals = (run.native.TAG, run.native.OUTPUT, run.native.Worker, run.native.execute,
            run.native.validate_execution, run.window.MODEL, run.window.CAP, run.window.OUTPUT)
        clock = dict(mono=0., wall_extra=0.)
        epoch = STOP - CAP - 1000
        old_close, old_read, old_write, old_check = run.close_report, run.read_json, run.write_json, run.check_end
        delayed = False
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            directory = Path(tmp); fixture = self.original_fixture(directory)
            def checkpoint(admission, began, stage, *, reserve=0):
                nonlocal delayed
                match = {"report_write": "before_report_write", "report_read": "after_report_write",
                    "terminal_write": "after_report_hash", "terminal_read": "after_terminal_write"}.get(late_on)
                if not delayed and stage == match:
                    delayed = True; left = .01 if late_on.startswith("report") else 1.01
                    if deadline_axis == "whole": clock["mono"] = CAP - left
                    else: clock["wall_extra"] = STOP - (epoch + clock["mono"]) - left
                return old_check(admission, began, stage, reserve=reserve)
            def slow_close(path, report, primary_error=None):
                old_close(path, report, primary_error=primary_error)
                if late_on == "report_write": clock["mono"] += .1
            def slow_write(path, value):
                old_write(path, value)
                if Path(path).name == "terminal_receipt.json" and late_on == "terminal_write": clock["mono"] += 1.1
            def slow_read(path):
                value = old_read(path)
                if Path(path).name == "report.json" and late_on == "report_read" and "owner" in Path(path).parts:
                    clock["mono"] += .1
                if Path(path).name == "terminal_receipt.json":
                    if late_on == "terminal_read": clock["mono"] += 1.1
                    if readback_changed: value = dict(value, status="SYNTHETIC_READBACK_MISMATCH")
                return value
            def pre(*_):
                clock["mono"] += preflight_spent
                return fixture.prior
            def identity():
                calls.append("identity")
                return dict(self.signature, sha256="CHANGED") if changed_source and calls.count("identity") > 1 else self.signature
            def asset(_):
                calls.append("asset")
                return {} if changed_asset and calls.count("asset") > 1 else self.assets
            def idle():
                calls.append("idle")
                if admission_hold and calls.count("idle") == 1: raise run.AdmissionHold("synthetic GPU busy; no query")
                if calls.count("idle") == 1: clock["mono"] += before_worker_spent
                return dict(competing_compute_pids=[], scope="SYNTHETIC_CPU_NO_GPU_QUERY")
            def numerical(lm, torch, receipt):
                calls.append("numerical"); receipt.update(passed=True, status="COMPLETE", synthetic_cpu_only=True)
                if fault == "unclosed": receipt["passed"] = False
                if fault == "numerical":
                    receipt.update(passed=False, comparisons=[dict(actual=[-2.], expected=[-1.])])
                    raise ValueError("synthetic strict numerical negative")
            def evaluate(lm, target, report, tasks, mode):
                calls.append("evaluate"); self.assertEqual(mode, "full")
                self.assertNotEqual(target, run.native.OUTPUT / run.MODEL / "full")
                if duplicate_report: old_write(target / "report.json", dict(returncode=8, synthetic_cpu_only=True))
                if fault == "evaluate": raise ValueError("synthetic evaluator primary")
                if fault == "wall": raise TimeoutError("synthetic actual work-phase wall expiry")
                if fault == "hold": raise run.AdmissionHold("synthetic evaluator hold")
                report.update(actual_counts=run.native.official.expected_counts("full"),
                    choice_likelihoods=67105 if missing_choice else 67106, raw_independent_recount=True, synthetic_cpu_only=True)
                if changed_prior:
                    with (fixture.base / run.MODEL / "cost/report.json").open("a", encoding="utf-8") as stream: stream.write(" ")
                if changed_raw:
                    raw = fixture.reports["cost"]["sample_manifests"]["piqa"]["shards"][0]["path"]
                    with (fixture.base / run.MODEL / "cost" / raw).open("a", encoding="utf-8") as stream: stream.write(" ")
                if changed_log:
                    with fixture.log.open("a", encoding="utf-8") as stream: stream.write(" ")
            def writer(target, stem):
                calls.append("writer"); clock["mono"] += writer_spent
                return ShardWriter(target, stem)
            def worker(assets, build, stop, wire, proof):
                calls.append("worker"); self.assertEqual(build, self.window_build["build"])
                self.assertLessEqual(stop, STOP - run.CLOSURE_RESERVE)
                class Owned:
                    def __enter__(self):
                        proof.update(model_loaded=True, owned_pid=12345, worker_cleanup_complete=False,
                            resource_sample_count=sample_count, telemetry_errors=["synthetic telemetry"] if telemetry_error else [],
                            fixture="SYNTHETIC_CPU_NOT_A_MODEL")
                        if malformed_report: proof["bad_json"] = object()
                        wire.append(dict(event="SYNTHETIC_CPU_NOT_NATIVE_WIRE"))
                        return object()
                    def __exit__(self, *_):
                        calls.append("cleanup"); proof.update(worker_cleanup_complete=True, worker_returncode=worker_rc)
                        if cleanup_error: proof["cleanup_error"] = "synthetic cleanup error"
                return Owned()
            runtime = SimpleNamespace(tasks={}, specs=[], provenance={}, framework_commit="SYNTHETIC", data_manifest_sha256="SYNTHETIC",
                idle=idle, writer=writer, verify=verify, adapter=lambda _: lambda worker: object(), TemplateLM=object,
                torch=None, numerical=numerical, evaluate=evaluate)
            for name, value in (("OUTPUT", directory / "owner"), ("PRIOR_OUTPUT", fixture.base),
                    ("PRIOR", fixture.pins), ("PRIOR_LOG_SHA", fixture.log_sha), ("identity", identity),
                    ("asset_identity", asset), ("prerequisites", pre), ("model_runtime", lambda: runtime), ("Worker", worker),
                    ("now_epoch", lambda: epoch + clock["mono"] + clock["wall_extra"]),
                    ("monotonic_now", lambda: clock["mono"]), ("phase_wall_limit", lambda _: nullcontext()),
                    ("check_end", checkpoint), ("close_report", slow_close), ("read_json", slow_read), ("write_json", slow_write)):
                stack.enter_context(patch.object(run, name, value))
            result = run.execute(run.MODEL, run.MODE, self.signature["sha256"], DEADLINE, CAP, fixture.log)
            path = directory / "owner" / run.MODEL / "full/report.json"
            report = old_read(path) if path.exists() else {}
            fallback = old_read(path.with_name("report_closure_failure.json")) if path.with_name("report_closure_failure.json").exists() else None
            for name in ("terminal_receipt.json", "terminal_failure_receipt.json"):
                if path.with_name(name).exists(): report["_fixture_" + name] = old_read(path.with_name(name))
        self.assertEqual(frozen_globals, (run.native.TAG, run.native.OUTPUT, run.native.Worker, run.native.execute,
            run.native.validate_execution, run.window.MODEL, run.window.CAP, run.window.OUTPUT))
        return result, report, calls, fallback

    def test_synthetic_success_uses_original_helpers_and_closes_fresh_namespace(self):
        result, report, calls, _ = self.scenario()
        self.assertEqual(result["returncode"], 0)
        self.assertEqual((report["status"], report["returncode"], report["candidate_returncode"]),
            ("NATIVE_IQ2_WINDOW_COMPUTE_CLOSED_PENDING_TERMINAL", 9, 0))
        self.assertTrue(result["terminal_receipt_verified"])
        self.assertEqual(report["_fixture_terminal_receipt.json"]["returncode"], 0)
        self.assertNotIn("_fixture_terminal_failure_receipt.json", report)
        for name in ("worker", "numerical", "evaluate", "cleanup"): self.assertEqual(calls.count(name), 1)
        self.assertEqual([item["stage"] for item in report["remaining_admission_checks"]], ["before_runtime", "before_worker"])
        self.assertEqual(report["execution_window_policy"]["sample_manifest_origin_tag"], run.native.TAG)
        self.assertNotEqual(report["tag"], run.native.TAG)
        self.assertTrue(report["sources_unchanged"]); self.assertTrue(report["source_assets_unchanged"])
        self.assertTrue(report["original_prerequisites_unchanged"]); self.assertTrue(report["original_runlog_unchanged"])
        self.assertEqual(report["original_cost_raw_exit_recount"]["choice_likelihoods"], 576)
        self.assertEqual((sum(report["actual_counts"].values()), report["choice_likelihoods"]), (19965, 67106))

    def test_spent_plus_forecast_and_closure_is_checked_before_runtime_and_immediately_before_worker(self):
        for kwargs in (dict(preflight_spent=2700), dict(before_worker_spent=2700), dict(writer_spent=2700)):
            with self.subTest(kwargs=kwargs):
                result, report, calls, _ = self.scenario(**kwargs)
                self.assertEqual(result["returncode"], 8); self.assertNotIn("worker", calls)
                failed = report["remaining_admission_checks"][-1]
                self.assertFalse(failed["passed"]); self.assertEqual(failed["whole_remaining_seconds"], CAP-2700)
                self.assertGreater(failed["forecast_seconds"] + failed["closure_reserve_seconds"], CAP-2700)
                if "preflight_spent" in kwargs: self.assertNotIn("idle", calls)

    def test_absolute_deadline_and_whole_cap_each_include_closure_reserve(self):
        for whole_left, absolute_left in ((FORECAST + 29, FORECAST + 31), (FORECAST + 31, FORECAST + 29)):
            report = {}; admission = dict(hard_cap_seconds=whole_left, deadline_epoch=absolute_left)
            with patch.object(run, "now_epoch", return_value=0), patch.object(run, "monotonic_now", return_value=0):
                with self.assertRaises(run.AdmissionHold):
                    run.admit_remaining(dict(forecast_seconds=FORECAST), admission, 0, "synthetic", report)
            self.assertFalse(report["remaining_admission_checks"][0]["passed"])

    def test_report_and_terminal_write_read_delays_veto_on_both_clocks(self):
        for axis in ("whole", "absolute"):
            for stage in ("report_write", "report_read", "terminal_write", "terminal_read"):
                with self.subTest(axis=axis, stage=stage):
                    result, report, _, _ = self.scenario(late_on=stage, deadline_axis=axis)
                    self.assertEqual(result["returncode"], 9)
                    self.assertEqual(report["status"], "NATIVE_IQ2_WINDOW_COMPUTE_CLOSED_PENDING_TERMINAL")
                    self.assertEqual(report["_fixture_terminal_failure_receipt.json"]["returncode"], 9)
                    self.assertEqual(result["terminal_error_type"], "TimeoutError")
                    if stage.startswith("terminal"): self.assertEqual(report["_fixture_terminal_receipt.json"]["returncode"], 0)

    def test_terminal_readback_mismatch_vetoes_preserved_success_candidate(self):
        result, report, _, _ = self.scenario(readback_changed=True)
        self.assertEqual(result["returncode"], 9)
        self.assertEqual(report["_fixture_terminal_receipt.json"]["returncode"], 0)
        self.assertEqual(report["_fixture_terminal_failure_receipt.json"]["error_type"], "ValueError")

    def test_work_expiry_worker_failure_zero_samples_and_telemetry_preserve_primary(self):
        for rc, samples, telemetry in ((0, 1, False), (9, 1, False), (0, 0, False), (0, 1, True)):
            with self.subTest(rc=rc, samples=samples, telemetry=telemetry):
                result, report, calls, _ = self.scenario(fault="wall", worker_rc=rc, sample_count=samples, telemetry_error=telemetry)
                self.assertEqual((result["returncode"], report["returncode"]), (9, 9))
                self.assertEqual(report["error_type"], "TimeoutError")
                self.assertEqual(report["error"], "synthetic actual work-phase wall expiry")
                self.assertIn("cleanup", calls)
                if rc or not samples or telemetry: self.assertTrue(report["exit_verification_errors"])
        for kwargs in (dict(worker_rc=9), dict(sample_count=0), dict(telemetry_error=True)):
            result, report, _, _ = self.scenario(**kwargs)
            self.assertEqual(result["returncode"], 9); self.assertTrue(report["exit_verification_errors"])

    def test_real_cpu_signal_wall_timer_expires_without_worker(self):
        with self.assertRaises(TimeoutError):
            with run.phase_wall_limit(.02): time.sleep(.05)

    def test_model_before_load_hold_is_8_and_real_errors_are_9_with_cleanup(self):
        result, report, calls, _ = self.scenario(admission_hold=True)
        self.assertEqual((result["returncode"], report["returncode"]), (8, 8))
        self.assertNotIn("worker", calls); self.assertNotIn("model_proof", report)
        for fault in ("numerical", "unclosed", "evaluate"):
            result, report, calls, _ = self.scenario(fault=fault)
            self.assertEqual((result["returncode"], report["returncode"]), (9, 9))
            self.assertEqual(report["error_type"], "ValueError"); self.assertIn("cleanup", calls)
            self.assertEqual(calls.count("idle"), 2); self.assertTrue(report["source_assets_unchanged"])
            if fault != "evaluate":
                self.assertNotIn("evaluate", calls); self.assertEqual(report["numerical_canary"]["status"], "FAILED")

    def test_cleanup_failure_escalates_hold_without_hiding_original(self):
        result, report, _, _ = self.scenario(fault="hold", cleanup_error=True)
        self.assertEqual(result["returncode"], 9)
        self.assertEqual((report["error_type"], report["error"]), ("AdmissionHold", "synthetic evaluator hold"))
        self.assertTrue(report["exit_verification_errors"])

    def test_asset_source_report_raw_log_drift_and_missing_choice_are_errors(self):
        for kwargs in (dict(changed_asset=True), dict(changed_source=True), dict(changed_prior=True),
                dict(changed_raw=True), dict(changed_log=True), dict(missing_choice=True)):
            with self.subTest(kwargs=kwargs):
                result, report, _, _ = self.scenario(**kwargs)
                self.assertEqual(result["returncode"], 9)
                self.assertNotEqual(report["status"], "NATIVE_IQ2_WINDOW_FULL_COMPLETE")

    def test_report_serialization_fallback_and_existing_partial_never_return_success(self):
        result, report, _, _ = self.scenario(fault="hold", malformed_report=True)
        self.assertEqual(result["returncode"], 9); self.assertEqual(report["original_error"]["type"], "AdmissionHold")
        self.assertIn("report_closure_error", report)
        result, report, _, fallback = self.scenario(fault="hold", duplicate_report=True)
        self.assertEqual(result["returncode"], 9); self.assertEqual(report["returncode"], 8)
        self.assertEqual(fallback["original_error"]["message"], "synthetic evaluator hold")

    def test_existing_output_bad_pin_and_missing_prerequisite_never_start_model(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(run, "OUTPUT", Path(tmp)), \
                patch.object(run, "identity", return_value=self.signature), patch.object(run, "asset_identity") as assets, \
                patch.object(run, "now_epoch", return_value=STOP-CAP-1000), patch.object(run, "model_runtime") as runtime:
            with self.assertRaises(run.AdmissionHold):
                run.execute(run.MODEL, run.MODE, "BAD", DEADLINE, CAP, None)
            target = Path(tmp) / run.MODEL / "full"; target.mkdir(parents=True)
            (target / "partial.txt").write_text("CPU fixture preserved", encoding="utf-8")
            with self.assertRaises(run.AdmissionHold):
                run.execute(run.MODEL, run.MODE, self.signature["sha256"], DEADLINE, CAP, None)
            self.assertEqual((target / "partial.txt").read_text(encoding="utf-8"), "CPU fixture preserved")
            assets.assert_not_called(); runtime.assert_not_called()
        with tempfile.TemporaryDirectory() as tmp, patch.object(run, "OUTPUT", Path(tmp)), \
                patch.object(run, "identity", return_value=self.signature), patch.object(run, "asset_identity", return_value=self.assets), \
                patch.object(run, "now_epoch", return_value=STOP-CAP-1000), \
                patch.object(run, "prerequisites", side_effect=run.AdmissionHold("synthetic missing cost")), \
                patch.object(run, "model_runtime") as runtime, patch.object(run, "Worker") as worker:
            result = run.execute(run.MODEL, run.MODE, self.signature["sha256"], DEADLINE, CAP, None)
            self.assertEqual(result["returncode"], 8)
            report = run.read_json(Path(tmp) / run.MODEL / "full/report.json")
            self.assertEqual(report["error"], "synthetic missing cost"); self.assertNotIn("exit_verification_errors", report)
            runtime.assert_not_called(); worker.assert_not_called()

    def test_veto_is_write_once_and_preserves_first_original_cause(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            context = dict(admission=dict(hard_cap_seconds=CAP, deadline_epoch=STOP), began=time.monotonic(), source_sha256="SYNTHETIC")
            first = run.terminal_failure(target, context, TimeoutError("first veto"), ValueError("original numerical error"))
            second = run.terminal_failure(target, context, TimeoutError("second veto"))
            self.assertEqual(first, second)
            self.assertEqual(second["original_error"]["message"], "original numerical error")

    def test_cli_flush_delay_vetoes_candidate_and_preserves_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp); clock = dict(mono=CAP-1.01)
            context = dict(target=str(target), admission=dict(hard_cap_seconds=CAP, deadline_epoch=STOP),
                began=0, source_sha256=self.signature["sha256"])
            candidate = dict(status="NATIVE_IQ2_WINDOW_FULL_COMPLETE", returncode=0, model=run.MODEL, mode="full",
                terminal_receipt_verified=True, _terminal_context=context)
            run.write_json(target / "terminal_receipt.json", dict(returncode=0, synthetic_only=True))
            before = run.digest(target / "terminal_receipt.json"); printed = []
            def slow_print(*args, **kwargs):
                printed.append(args)
                if len(printed) == 1: clock["mono"] += 1.1
            with patch.object(run, "execute", return_value=candidate), \
                    patch.object(run, "monotonic_now", side_effect=lambda: clock["mono"]), \
                    patch.object(run, "now_epoch", return_value=STOP-100), patch("builtins.print", side_effect=slow_print):
                self.assertEqual(run.main(self.argv()), 9)
            self.assertEqual(run.digest(target / "terminal_receipt.json"), before)
            self.assertEqual(run.read_json(target / "terminal_failure_receipt.json")["returncode"], 9)
            self.assertEqual(json.loads(printed[-1][0])["event"], "NATIVE_IQ2_WINDOW_TERMINAL_VETO")

    def argv(self):
        return ["--execute", "--model", run.MODEL, "--mode", "full", "--source-sha256", "X",
            "--deadline", DEADLINE, "--max-wall-sec", str(CAP), "--prior-run-log", "/synthetic/log.txt"]

    def test_cli_requires_all_explicit_inputs_and_distinguishes_hold_from_error(self):
        argv = self.argv()
        for flag in ("--model", "--mode", "--source-sha256", "--deadline", "--max-wall-sec", "--prior-run-log"):
            missing = list(argv); index = missing.index(flag); del missing[index:index+2]
            with patch.object(run, "execute") as execute, redirect_stdout(io.StringIO()), \
                    patch("sys.stderr", new_callable=io.StringIO), self.assertRaises(SystemExit) as caught:
                run.main(missing)
            self.assertEqual(caught.exception.code, 2); execute.assert_not_called()
        for error, code in ((run.AdmissionHold("CPU fixture hold"), 8), (RuntimeError("CPU fixture bug"), 9)):
            with patch.object(run, "execute", side_effect=error), redirect_stdout(io.StringIO()) as output:
                self.assertEqual(run.main(argv), code); self.assertEqual(json.loads(output.getvalue())["returncode"], code)

    def test_v2_execution_rejects_unready_worker_and_worker_deadline_before_runtime(self):
        for build in (dict(status="NOT_READY"), dict(self.window_build, deadline_epoch=STOP-1)):
            signature = dict(self.signature, worker_window_build=build)
            with tempfile.TemporaryDirectory() as tmp, patch.object(run, "identity", return_value=signature), \
                    patch.object(run, "OUTPUT", Path(tmp)), patch.object(run, "now_epoch", return_value=STOP-CAP-1000), \
                    patch.object(run, "model_runtime") as runtime, self.assertRaises(run.AdmissionHold):
                run.execute(run.MODEL, run.MODE, signature["sha256"], DEADLINE, CAP, None)
            runtime.assert_not_called()
        with self.assertRaises(run.AdmissionHold):
            run.validate_execution(run.MODEL, run.MODE, DEADLINE, 17401, now=STOP-20000)

    def test_supervisor_reserves_parent_budget_and_passes_separate_build_without_global_changes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(run, "OUTPUT", Path(tmp)), \
                patch.object(run, "identity", return_value=self.signature), \
                patch.object(run, "now_epoch", return_value=STOP-CAP-1000), \
                patch.object(run.time, "monotonic", side_effect=[10., 12.]), \
                patch.object(run.worker_window, "supervise_process", return_value=dict(returncode=9)) as supervisor:
            args = SimpleNamespace(model=run.MODEL, mode=run.MODE, source_sha256=self.signature["sha256"],
                deadline=DEADLINE, max_wall_sec=CAP, prior_run_log=Path("/synthetic/log"))
            run.supervise(args)
        argv = supervisor.call_args.args[0]; kw = supervisor.call_args.kwargs
        self.assertEqual(int(argv[argv.index("--max-wall-sec")+1]), CAP-62)
        self.assertEqual(kw["cap"], CAP); self.assertEqual(kw["started_monotonic"], 10.)
        self.assertEqual(kw["worker_binary"], run.native.HEADERS/self.window_build["worker"])
        self.assertIs(run.Worker, run.native.Worker)

    def test_supervisor_cli_flush_delay_appends_veto_and_never_changes_saved_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); clock = dict(value=10.)
            candidate = dict(returncode=0, status="SUPERVISOR_CANDIDATE_PENDING_PROCESS_EXIT",
                _supervisor_context=dict(directory=tmp, monotonic_stop=11., deadline_epoch=time.time()+100))
            run.worker_window.write_once(directory/"supervisor_receipt.json", dict(returncode=0))
            original = run.worker_window.digest(directory/"supervisor_receipt.json")
            printed = []
            def slow_print(*args, **kwargs):
                printed.append(args); clock["value"] = 12.
            argv = self.argv(); argv[0] = "--supervise"
            with patch.object(run, "supervise", return_value=candidate), \
                    patch.object(run.worker_window.time, "monotonic", side_effect=lambda: clock["value"]), \
                    patch("builtins.print", side_effect=slow_print):
                self.assertEqual(run.main(argv), 9)
            self.assertEqual(run.worker_window.digest(directory/"supervisor_receipt.json"), original)
            self.assertTrue(list(directory.glob("supervisor_veto_*.json")))
            self.assertEqual(json.loads(printed[-1][0])["event"], "SUPERVISOR_TERMINAL_VETO")


if __name__ == "__main__":
    unittest.main()
