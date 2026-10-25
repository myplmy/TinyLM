"""Synthetic CPU owner tests; no native worker/backend/model is executed."""
from __future__ import annotations
import ast
import builtins
from contextlib import ExitStack, redirect_stdout
import copy
import io
import json
from pathlib import Path
import runpy
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from scripts import p106b_native_window as run
from scripts.p106b_shards import ShardWriter, verify


class WindowContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signature = run.identity()
        cls.reports = {mode: run.read_json(run.native.OUTPUT/run.MODEL/mode/"report.json") for mode in run.PRIOR}
        cls.assets = cls.reports["cost"]["assets"]

    def test_actual_pinned_v2_receipts_reproduce_without_opening_a_model(self):
        prior = run.prerequisites(self.signature, self.assets)
        self.assertAlmostEqual(prior["forecast_seconds"], 8734.441984035791, places=8)
        self.assertEqual(prior["canary_report_sha256"], run.PRIOR["canary"])
        self.assertEqual(prior["cost_report_sha256"], run.PRIOR["cost"])
        self.assertEqual(prior["original_full_hold_report_sha256"], run.PRIOR["full"])
        self.assertEqual(self.reports["full"]["status"], "NATIVE_PREREQUISITE_HOLD")
        self.assertNotIn("model_proof", self.reports["full"])

    def test_full_window_deadline_exact_cap_and_gpt2_only(self):
        now = run.native.DEADLINE-run.CAP
        value = run.validate_execution(run.MODEL, run.MODE, "2026-10-24T08:40:00+09:00", run.CAP, now=now)
        self.assertEqual(value["hard_cap_seconds"], 10800)
        bad = [(run.MODEL, "cost", run.CAP, "2026-10-24T08:40:00+09:00", now),
            ("qwen35_08b_iq2xxs", run.MODE, run.CAP, "2026-10-24T08:40:00+09:00", now),
            (run.MODEL, run.MODE, 7200, "2026-10-24T08:40:00+09:00", now),
            (run.MODEL, run.MODE, 10801, "2026-10-24T08:40:00+09:00", now),
            (run.MODEL, run.MODE, True, "2026-10-24T08:40:00+09:00", now),
            (run.MODEL, run.MODE, run.CAP, "2026-10-24T08:40:00", now),
            (run.MODEL, run.MODE, run.CAP, "2026-10-24T08:41:00+09:00", now),
            (run.MODEL, run.MODE, run.CAP, "bad", now),
            (run.MODEL, run.MODE, run.CAP, "2026-10-24T08:40:00+09:00", now+.01)]
        for model, mode, cap, deadline, instant in bad:
            with self.subTest(model=model, mode=mode, cap=cap, deadline=deadline), self.assertRaises(run.AdmissionHold):
                run.validate_execution(model, mode, deadline, cap, now=instant)
        with self.assertRaises(run.AdmissionHold):
            run.native.validate_execution(run.MODEL, run.MODE, "2026-10-24T08:40:00+09:00", run.CAP, now=now)

    def test_native_frozen_identity_worker_and_no_production_monkeypatch(self):
        self.assertEqual(self.signature["native_source_identity"]["sha256"], run.NATIVE_SHA)
        self.assertEqual(self.signature["native_source_identity"]["build"]["worker_sha256"], run.WORKER_SHA)
        self.assertIs(run.Worker, run.native.Worker)
        source = Path(run.__file__).read_text(); tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    self.assertFalse(isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                        and target.value.id == "native", "production must not assign frozen globals")
        self.assertNotIn("native.execute(", source)
        self.assertNotIn("native.validate_execution(", source)
        self.assertIn("numerical=native.numerical_canary", source)
        self.assertIn("evaluate=native.evaluate_tasks", source)
        self.assertIn("adapter=native.adapter_type", source)

    def test_occupied_gpu_is_hold_but_nvml_tool_error_remains_error(self):
        def busy(): raise RuntimeError("다른 GPU compute PID가 있습니다: 12345")
        def broken(): raise RuntimeError("NVML GPU 점조회 실패: 모델을 열지 않습니다.")
        with self.assertRaises(run.AdmissionHold): run.idle_admission(SimpleNamespace(idle=busy))
        with self.assertRaises(RuntimeError) as caught: run.idle_admission(SimpleNamespace(idle=broken))
        self.assertNotIsInstance(caught.exception, run.AdmissionHold)

    def test_source_only_import_and_help_never_load_runtime_or_model(self):
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers", "tokenizers", "datasets", "lm_eval", "tinylm"}:
                raise AssertionError("unexpected heavy import: "+name)
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded), patch.object(run, "model_runtime") as runtime, \
                patch.object(run, "Worker") as worker, patch.object(run, "asset_identity") as assets:
            runpy.run_path(str(Path(run.__file__)), run_name="pure_window_import")
            text = io.StringIO()
            with redirect_stdout(text): self.assertEqual(run.main(["--check-only"]), 0)
            proof = json.loads(text.getvalue())
            self.assertEqual((proof["models"], proof["backend_initializations"]), (0, 0))
            with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as caught: run.main(["--help"])
            self.assertEqual(caught.exception.code, 0)
            runtime.assert_not_called(); worker.assert_not_called(); assets.assert_not_called()

    def test_original_report_sha_tamper_missing_raw_and_postchecks_rejected(self):
        with patch.object(run, "digest", return_value="CHANGED"):
            with self.assertRaises(run.AdmissionHold): run.prerequisites(self.signature, self.assets)
        for field in ("sources_unchanged", "source_assets_unchanged"):
            report = copy.deepcopy(self.reports["cost"]); report[field] = False
            with self.subTest(field=field), self.assertRaises(run.AdmissionHold): run.check_closed_numerical(report)
        for key, bad in (("worker_cleanup_complete", False), ("worker_returncode", 9), ("telemetry_errors", ["TimeoutError"]),
                ("resource_sample_count", 0)):
            report = copy.deepcopy(self.reports["canary"]); report["model_proof"][key] = bad
            with self.subTest(key=key), self.assertRaises(run.AdmissionHold): run.check_closed_numerical(report)
        report = copy.deepcopy(self.reports["cost"]); report["raw_independent_recount"] = False
        with patch.object(run, "read_json", side_effect=lambda path: report if Path(path).parent.name == "cost" else self.reports[Path(path).parent.name]):
            with self.assertRaises(run.AdmissionHold): run.prerequisites(self.signature, self.assets)

    def test_original_numeric_threshold_and_negative_cannot_be_hidden_by_passed_flag(self):
        for change in ("tolerance", "negative", "incomplete", "future"):
            report = copy.deepcopy(self.reports["canary"]); suite = report["numerical_canary"]
            if change == "tolerance": suite["atol"] = .1
            if change == "negative": suite["comparisons"][0]["expected"][0][0] -= 1
            if change == "incomplete": suite["comparisons"].pop()
            if change == "future": suite["checks"][0]["future_token"]["passed"] = False
            with self.subTest(change=change), self.assertRaises(run.AdmissionHold): run.check_closed_numerical(report)

    def scenario(self, *, fault=None, cleanup_error=False, admission_hold=False, missing_choice=False,
            malformed_report=False, duplicate_report=False, changed_asset=False, changed_source=False, changed_prior=False):
        """Only new-module dependencies are replaced; frozen native globals stay intact."""
        calls = []; frozen_globals = (run.native.TAG, run.native.OUTPUT, run.native.Worker, run.native.execute, run.native.validate_execution)
        target_holder = {}; prior = dict(canary_report_sha256=run.PRIOR["canary"], cost_report_sha256=run.PRIOR["cost"], forecast_seconds=8734.441984035791)
        def fake_identity():
            calls.append("identity")
            if changed_source and calls.count("identity") > 1: return dict(self.signature, sha256="CHANGED")
            return self.signature
        def fake_asset(model):
            calls.append("asset")
            return {} if changed_asset and calls.count("asset") > 1 else self.assets
        def idle():
            calls.append("idle")
            if admission_hold and calls.count("idle") == 1: raise run.AdmissionHold("synthetic GPU busy; no query")
            return {"competing_compute_pids": [], "scope": "SYNTHETIC_CPU_NO_GPU_QUERY"}
        def numerical(lm, torch, receipt):
            calls.append("numerical"); receipt.update(passed=True, status="COMPLETE", synthetic_cpu_only=True)
            if fault == "unclosed": receipt["passed"] = False
            if fault == "numerical":
                receipt.update(passed=False, comparisons=[{"stage": "cpu/strict", "actual": [-2.], "expected": [-1.]}])
                raise ValueError("synthetic strict numerical negative")
        def evaluate(lm, target, report, tasks, mode):
            calls.append("evaluate"); self.assertEqual(mode, "full"); self.assertNotEqual(target, run.native.OUTPUT/run.MODEL/"full")
            target_holder["path"] = target
            if duplicate_report: run.native.write_json(target/"report.json", dict(returncode=8, synthetic_cpu_only=True))
            if fault == "evaluate": raise ValueError("synthetic evaluator primary")
            if fault == "hold": raise run.AdmissionHold("synthetic evaluator hold")
            report.update(actual_counts=run.native.official.expected_counts("full"), choice_likelihoods=67105 if missing_choice else 67106,
                raw_independent_recount=True, synthetic_cpu_only=True)
        def fake_worker(assets, build, stop, writer, proof):
            calls.append("worker"); self.assertEqual(build["worker_sha256"], run.WORKER_SHA)
            self.assertLessEqual(stop, run.native.DEADLINE-30)
            class Owned:
                def __enter__(self):
                    proof.update(model_loaded=True, owned_pid=12345, worker_cleanup_complete=False, resource_sample_count=1,
                        telemetry_errors=[], fixture="SYNTHETIC_CPU_NOT_A_MODEL")
                    if malformed_report: proof["bad_json"] = object()
                    writer.append({"event": "SYNTHETIC_CPU_NOT_NATIVE_WIRE"})
                    return object()
                def __exit__(self, *_):
                    calls.append("cleanup"); proof.update(worker_cleanup_complete=True, worker_returncode=0)
                    if cleanup_error: proof["cleanup_error"] = "synthetic cleanup error"
            return Owned()
        runtime = SimpleNamespace(tasks={}, specs=[], provenance={}, framework_commit="SYNTHETIC", data_manifest_sha256="SYNTHETIC",
            idle=idle, writer=ShardWriter, verify=verify, adapter=lambda _: lambda worker: object(), TemplateLM=object,
            torch=None, numerical=numerical, evaluate=evaluate)
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            for name, value in (("OUTPUT", Path(tmp)), ("identity", fake_identity), ("asset_identity", fake_asset),
                    ("prerequisites", lambda *_: prior), ("model_runtime", lambda: runtime), ("Worker", fake_worker),
                    ("now_epoch", lambda: run.native.DEADLINE-run.CAP-1000)):
                stack.enter_context(patch.object(run, name, value))
            if changed_prior: stack.enter_context(patch.object(run, "digest", return_value="CHANGED"))
            result = run.execute(run.MODEL, run.MODE, self.signature["sha256"], "2026-10-24T08:40:00+09:00", 10800)
            path = Path(tmp)/run.MODEL/"full"/"report.json"
            report = run.read_json(path)
            fallback = run.read_json(path.with_name("report_closure_failure.json")) if path.with_name("report_closure_failure.json").exists() else None
        self.assertEqual(frozen_globals, (run.native.TAG, run.native.OUTPUT, run.native.Worker, run.native.execute, run.native.validate_execution))
        return result, report, calls, fallback

    def test_synthetic_success_reuses_full_helpers_and_keeps_origin_tag(self):
        result, report, calls, _ = self.scenario()
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(calls.count("worker"), 1); self.assertEqual(calls.count("numerical"), 1); self.assertEqual(calls.count("evaluate"), 1)
        self.assertEqual(report["tag"], run.TAG)
        self.assertEqual(report["execution_window_policy"]["sample_manifest_origin_tag"], run.native.TAG)
        self.assertNotEqual(report["tag"], run.native.TAG)
        self.assertTrue(report["sources_unchanged"]); self.assertTrue(report["source_assets_unchanged"])
        self.assertTrue(report["original_prerequisites_unchanged"])
        self.assertEqual(sum(report["actual_counts"].values()), 19965)
        self.assertEqual(report["choice_likelihoods"], 67106)

    def test_model_before_load_hold_is_domain_returncode8(self):
        result, report, calls, _ = self.scenario(admission_hold=True)
        self.assertEqual((result["returncode"], report["returncode"]), (8, 8))
        self.assertNotIn("worker", calls); self.assertNotIn("model_proof", report)

    def test_real_error9_preserves_primary_and_cleanup_and_exit_checks(self):
        for fault in ("numerical", "unclosed", "evaluate"):
            result, report, calls, _ = self.scenario(fault=fault)
            self.assertEqual((result["returncode"], report["returncode"]), (9, 9))
            self.assertEqual(report["error_type"], "ValueError")
            self.assertIn("cleanup", calls); self.assertEqual(calls.count("idle"), 2)
            self.assertTrue(report["source_assets_unchanged"])
            if fault != "evaluate": self.assertNotIn("evaluate", calls); self.assertEqual(report["numerical_canary"]["status"], "FAILED")

    def test_cleanup_failure_escalates_hold_to9_without_hiding_primary(self):
        result, report, _, _ = self.scenario(fault="hold", cleanup_error=True)
        self.assertEqual(result["returncode"], 9)
        self.assertEqual(report["error_type"], "AdmissionHold")
        self.assertEqual(report["error"], "synthetic evaluator hold")
        self.assertTrue(report["exit_verification_errors"])

    def test_asset_source_prior_drift_and_missing_choice_are_errors_not_passes(self):
        for kwargs in ({"changed_asset": True}, {"changed_source": True}, {"changed_prior": True}, {"missing_choice": True}):
            with self.subTest(kwargs=kwargs):
                result, report, _, _ = self.scenario(**kwargs)
                self.assertEqual(result["returncode"], 9)
                self.assertNotEqual(report["status"], "NATIVE_WINDOW_FULL_COMPLETE")

    def test_actual_close_report_fallback_cannot_return_hold8_or_success0(self):
        result, report, _, _ = self.scenario(fault="hold", malformed_report=True)
        self.assertEqual(result["returncode"], 9)
        self.assertEqual(report["original_error"]["type"], "AdmissionHold")
        self.assertEqual(report["returncode"], 9); self.assertIn("report_closure_error", report)
        result, original, _, fallback = self.scenario(fault="hold", duplicate_report=True)
        self.assertEqual(result["returncode"], 9); self.assertEqual(original["returncode"], 8)
        self.assertEqual(fallback["original_error"]["message"], "synthetic evaluator hold")

    def test_existing_partial_and_source_pin_stop_before_asset_or_runtime(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(run, "OUTPUT", Path(tmp)), \
                patch.object(run, "identity", return_value=self.signature), patch.object(run, "asset_identity") as assets, \
                patch.object(run, "now_epoch", return_value=run.native.DEADLINE-run.CAP-1000), \
                patch.object(run, "model_runtime") as runtime:
            with self.assertRaises(run.AdmissionHold):
                run.execute(run.MODEL, run.MODE, "BAD", "2026-10-24T08:40:00+09:00", 10800)
            target = Path(tmp)/run.MODEL/"full"; target.mkdir(parents=True)
            (target/"partial.txt").write_text("CPU fixture preserved")
            with self.assertRaises(run.AdmissionHold):
                run.execute(run.MODEL, run.MODE, self.signature["sha256"], "2026-10-24T08:40:00+09:00", 10800)
            self.assertEqual((target/"partial.txt").read_text(), "CPU fixture preserved")
            assets.assert_not_called(); runtime.assert_not_called()

    def test_unadmitted_prerequisite_is_hold8_not_postflight_drift9(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(run, "OUTPUT", Path(tmp)), \
                patch.object(run, "identity", return_value=self.signature), patch.object(run, "asset_identity", return_value=self.assets), \
                patch.object(run, "now_epoch", return_value=run.native.DEADLINE-run.CAP-1000), \
                patch.object(run, "prerequisites", side_effect=run.AdmissionHold("synthetic missing cost")), \
                patch.object(run, "model_runtime") as runtime, patch.object(run, "Worker") as worker:
            result = run.execute(run.MODEL, run.MODE, self.signature["sha256"], "2026-10-24T08:40:00+09:00", 10800)
            self.assertEqual(result["returncode"], 8)
            report = run.read_json(Path(tmp)/run.MODEL/"full"/"report.json")
            self.assertEqual(report["error"], "synthetic missing cost")
            self.assertNotIn("exit_verification_errors", report)
            runtime.assert_not_called(); worker.assert_not_called()

    def test_cli_pre_admission_hold8_and_genuine_error9(self):
        argv = ["--execute", "--model", run.MODEL, "--mode", "full", "--source-sha256", "X",
            "--deadline", "2026-10-24T08:40:00+09:00", "--max-wall-sec", "10800"]
        for error, code in ((run.AdmissionHold("CPU fixture hold"), 8), (RuntimeError("CPU fixture bug"), 9)):
            with patch.object(run, "execute", side_effect=error), redirect_stdout(io.StringIO()) as text:
                self.assertEqual(run.main(argv), code)
                self.assertEqual(json.loads(text.getvalue())["returncode"], code)


if __name__ == "__main__": unittest.main()
