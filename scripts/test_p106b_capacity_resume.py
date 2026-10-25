#!/usr/bin/env python3
"""분리 생산 자원 프로필의 CPU 회귀. 실제 모델과 GPU 호출은 금지한다."""
from __future__ import annotations
from contextlib import contextmanager
from io import StringIO
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ENTRY = ROOT / "handoff/audit/oct26_research/resume_gemma_capacity.py"
spec = importlib.util.spec_from_file_location("capacity_resume_cpu", ENTRY)
resume = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resume)
probe = resume.helpers()
sup = probe.supervisor()
REAL_POPEN, REAL_RUN = subprocess.Popen, subprocess.run


def cpu_popen(command, *args, **kwargs):
    if isinstance(command, str) or Path(command[0]).resolve() != Path(sys.executable).resolve():
        raise AssertionError("CPU Python 외의 프로세스 실행은 금지한다")
    return REAL_POPEN(command, *args, **kwargs)


def budget(seconds=10, reserve=1):
    return sup.Budget(seconds, time.time()+seconds+5, started=time.monotonic(), reserve=reserve)


def quiet(code=8):
    return dict(process_started=True, actual_producer_exit=code, original_error=None,
        cleanup_errors=[], forced_cleanup=False, termination_requested=False,
        parent_witness_errors=[], subreaper_restored=True, controller_group_quiescent=True,
        stop_published=False, deferred_signals=[], residual_at_producer_exit=[])


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="capacity_resume_cpu_")
        self.directory = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(patch.stopall)
        patch.object(subprocess, "Popen", side_effect=cpu_popen).start()
        patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": ""}).start()

    @contextmanager
    def evidence(self, *, change_worker=None, change_review=None, forced=False):
        memory = dict(sample_count=2, sampled_gpu_global_peak_mib=12000,
            sampled_gpu_min_free_mib=4000, baseline_gpu_used_mib=4000,
            owned_server_peak_rss_mib=6000, telemetry_recovery=dict(
                timeout_attempts=0, fatal_calls=0, unobserved_query_window_sec=0.))
        child = dict(returncode=0, generation_attempts=4, completed_responses=4,
                     original_error=None, cleanup_errors=[], cleanup=dict(errors=[]), memory=memory)
        if change_worker:
            change_worker(child)
        report = dict(returncode=0, source_sha256=resume.BASE_SHA,
            status="RESOURCE_OBSERVATION_COMPLETE", original_error=None, cleanup_errors=[],
            supervision=dict(quiet(0), forced_cleanup=forced), worker=child)
        report["supervision"].update(stop_published=False, deferred_signals=[])
        sha = write(self.directory / resume.REPORT, report)
        write(self.directory / Path(resume.REPORT).parent / "worker.json", child)
        checks = []
        for index in range(1, 5):
            name = str(Path(resume.REPORT).parent / f"raw_{index:02d}.json")
            raw_sha = write(self.directory / name, dict(index=index,
                payload=dict(max_tokens=3072, thinking_budget_tokens=1024, temperature=1.),
                reply=dict(choices=[dict(finish_reason="stop", message=dict(content="blue"))])))
            checks.append(dict(raw_file=name, raw_sha256=raw_sha, label_status="LABELS_COMPLETE",
                root_content_readback="합성 원답 판독", rendered_student_turn={"answer": "blue"}))
        review = dict(schema="TINYLM_GEMMA_CAPACITY_ROOT_REVIEW_V1",
            probe_source_sha256=resume.BASE_SHA, report_path=resume.REPORT, report_sha256=sha,
            actual_root_launcher_exit=0, fixture_content_pairs_read=4,
            same_generation_parameters=True, adopt_production_auto=False,
            global_oom_safety="NOT_ESTABLISHED", long_context_or_multiturn_full_load_safe="NOT_ESTABLISHED",
            observed_sampling={"temperature": 1.}, structural_render_checks=checks,
            resource_summary=dict(sample_count=2, sampled_gpu_global_peak_mib=12000,
                sampled_gpu_min_free_mib=4000, baseline_gpu_used_mib=4000,
                timeouts=0, query_gaps=0, actual_cleanup_errors=0))
        if change_review:
            change_review(review)
        review_sha = write(self.directory / resume.REVIEW, review)
        terminal = self.directory / Path(resume.REPORT).parent / "terminal.jsonl"
        terminal.write_text(json.dumps(dict(event="OBSERVATION", returncode=0))+"\n")
        with patch.object(resume, "REPORT_SHA", sha):
            yield review_sha

    def test_valid_four_pair_root_evidence(self):
        with self.evidence() as sha:
            result = resume.proof(self.directory, sha)
        self.assertEqual(len(result["raw_sha256"]), 4)
        self.assertTrue(result["resource_only"])

    def test_wrong_report_and_review_hash(self):
        with self.evidence() as sha:
            with self.assertRaises(ValueError):
                resume.proof(self.directory, "A"*64)
            path = self.directory / resume.REPORT
            path.write_bytes(path.read_bytes()+b" ")
            with self.assertRaises(ValueError):
                resume.proof(self.directory, sha)

    def test_missing_root_review_pair_is_refused(self):
        with self.evidence(change_review=lambda row: row.update(fixture_content_pairs_read=3)):
            with self.assertRaises(ValueError):
                resume.proof(self.directory)

    def test_same_length_raw_mutation_is_refused(self):
        with self.evidence():
            path = self.directory / Path(resume.REPORT).parent / "raw_01.json"
            original = path.read_bytes()
            path.write_bytes(original.replace(b"blue", b"cyan"))
            self.assertEqual(len(original), path.stat().st_size)
            with self.assertRaises(ValueError):
                resume.proof(self.directory)

    def test_probe_forced_cleanup_and_numeric_gap_are_refused(self):
        with self.evidence(forced=True):
            with self.assertRaises(ValueError):
                resume.proof(self.directory)
        self.temp.cleanup()
        self.directory.mkdir()
        with self.evidence(change_worker=lambda row: row["memory"]["telemetry_recovery"].update(timeout_attempts=1)):
            with self.assertRaises(ValueError):
                resume.proof(self.directory)

    def test_probe_terminal_veto_overrides_prior_zero(self):
        with self.evidence():
            path = self.directory / Path(resume.REPORT).parent / "terminal.jsonl"
            with path.open("a") as stream:
                stream.write(json.dumps(dict(event="TERMINAL_VETO", returncode=9))+"\n")
            with self.assertRaises(ValueError):
                resume.proof(self.directory)

    def test_reader_floor_boundary_and_latch(self):
        values = iter([(100, 2048), (101, 2047), (102, 9000)])
        reader = resume.CapacityMemoryReader(lambda: next(values), emit=lambda _: None)
        self.assertEqual(reader(), (100, 2048))
        with self.assertRaises(RuntimeError):
            reader()
        with self.assertRaises(RuntimeError):
            reader()
        snapshot = reader.snapshot()
        self.assertEqual(snapshot["observed_min_free_mib"], 2047)
        self.assertEqual(snapshot["floor_breaches"], 1)
        self.assertTrue(snapshot["floor_latched"])
        self.assertEqual(snapshot["calls"], 2)

    def test_reader_keeps_retry_gap_and_rejects_nonfinite(self):
        calls = []
        def source():
            calls.append(1)
            if len(calls) == 1:
                raise subprocess.TimeoutExpired("fixture", 5)
            return 100, 4096
        reader = resume.CapacityMemoryReader(source, emit=lambda _: None, pause=lambda _: None)
        self.assertEqual(reader(), (100, 4096))
        self.assertEqual(reader.snapshot()["measurement_coverage"], "GAPPED")
        self.assertEqual(reader.snapshot()["timeout_attempts"], 1)
        bad = resume.CapacityMemoryReader(lambda: (100, float("nan")), emit=lambda _: None)
        with self.assertRaises(ValueError):
            bad()

    def test_scoped_aliases_restore_and_fresh_admission(self):
        from scripts import diag_p106b_gemma_deficit_production as producer
        from scripts import diag_p106b_gemma_telemetry_resume as telemetry
        original, original_reader = producer.idle_before_gpu, telemetry.RetryingMemoryReader
        readers, admissions = [], []
        with patch.object(probe, "gpu_snapshot", return_value=dict(used_mib=500, free_mib=11264, compute_apps=[])):
            with self.assertRaises(RuntimeError):
                with resume.resource_scope(budget(), readers, admissions):
                    producer.idle_before_gpu()
                    telemetry.RetryingMemoryReader(lambda: (100, 4096), emit=lambda _: None)
                    raise RuntimeError("원 오류")
        self.assertIs(producer.idle_before_gpu, original)
        self.assertIs(telemetry.RetryingMemoryReader, original_reader)
        self.assertEqual(len(readers), 1)
        self.assertTrue(admissions[0]["admitted"])

    def test_fresh_admission_uses_existing_precondition_type(self):
        from scripts import diag_p106b_gemma_deficit_production as producer
        from scripts.p106b_gate_runtime import PrerequisiteHold
        admissions = []
        with patch.object(probe, "gpu_snapshot", return_value=dict(used_mib=500, free_mib=11263, compute_apps=[])):
            with resume.resource_scope(budget(), [], admissions):
                with self.assertRaises(PrerequisiteHold):
                    producer.idle_before_gpu()
        self.assertFalse(admissions[0]["admitted"])

    def production_fixture(self):
        destination = self.directory / resume.PRODUCTION
        inputs = {"fixture": 1}
        write(destination / "inputs.json", inputs)
        row = dict(schema="P106B_GEMMA_DEFICIT_BATCH_V1", input=inputs, returncode=8,
            status="PRODUCTION_PAUSED", error_type="ProductionBudgetPause",
            cursor=[1, 3], nonpadding_tokens={"train:en": 10}, assistant_targets={"train:en": 5},
            rows={"train:en": 1}, family_tokens={}, task_tokens={}, accepted_groups=0,
            new_train_x_tokens=0, token_target_ready=False)
        for index in range(4):
            write(destination / f"batch_{index:06d}/report.json",
                  dict(row, status="GATE_NEGATIVE" if index == 3 else "PRODUCTION_PAUSED"))
        return destination, inputs, row

    def test_dynamic_four_old_batches_include_empty_gate(self):
        destination, inputs, row = self.production_fixture()
        before = sup.production_snapshot(destination, budget())
        self.assertEqual(before["batches"], 4)
        write(destination / "batch_000004/report.json", row)
        log = self.directory / "producer.log"
        log.write_text("[DEFICIT_FINAL] 8\n")
        result = sup.verify_production(destination, before, inputs, 8, log, budget())
        self.assertEqual(result["status"], "CLOSED_PRODUCTION_PAUSED")
        self.assertEqual(result["accepted_groups"], 0)
        self.assertEqual(result["new_train_x_tokens"], 0)

    def test_empty_new_admission_hold_is_not_production_pause(self):
        destination, inputs, row = self.production_fixture()
        before = sup.production_snapshot(destination, budget())
        write(destination / "batch_000004/report.json",
              dict(row, status="GATE_NEGATIVE", error_type="PrerequisiteHold"))
        result = resume.verify_empty_hold(destination, before, inputs,
            dict(quiet(), owned_sessions=[]), dict(precondition_hold=True,
            admissions=[{"admitted": False}]), budget())
        self.assertEqual(result["status"], "CLOSED_PRE_MODEL_HOLD")
        with self.assertRaises(ValueError):
            resume.verify_empty_hold(destination, before, inputs,
                dict(quiet(), owned_sessions=[{"role": "teacher"}]),
                dict(precondition_hold=True, admissions=[{"admitted": False}]), budget())

    def test_stop_pause_allowed_only_without_controller_term_or_cleanup(self):
        value = dict(quiet(), stop_published=True, deferred_signals=[15])
        self.assertTrue(resume.quiet(value))
        for key, bad in (("termination_requested", True), ("forced_cleanup", True),
                         ("cleanup_errors", [{}]), ("actual_producer_exit", 9),
                         ("actual_producer_exit", False), ("parent_witness_errors", [{}])):
            with self.subTest(key=key):
                self.assertFalse(resume.quiet(dict(value, **{key: bad})))

    def test_worker_parent_pid_guard_before_production(self):
        write(self.directory / "invocation.json", dict(parent_pid=os.getppid()+1,
              parent_starttime=1, source_sha256="A"*64))
        with patch.dict(os.environ, {sup.OWNER_KEY: "a"*64}):
            with self.assertRaises(ValueError):
                resume.worker(SimpleNamespace(output=self.directory), budget(), {"sha256": "A"*64})

    def test_worker_preserves_original_timer_and_passes_same_stop(self):
        from scripts import diag_p106b_supported_production8h as run
        parent = sup.proc.proc_stat(os.getppid())
        write(self.directory / "invocation.json", dict(parent_pid=os.getppid(),
              parent_starttime=parent["starttime"], source_sha256="A"*64))
        captured = []
        def execute(args):
            import signal
            self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0., 0.))
            with run.supported_wall_limit(1):
                self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0], 0)
            captured.append(args)
            return 8
        with patch.object(run, "execute", execute), \
             patch.object(resume, "proof", return_value={}), \
             patch.object(resume, "source_identity", return_value={"sha256": "A"*64}), \
             patch.dict(os.environ, {sup.OWNER_KEY: "a"*64}):
            code = resume.worker(SimpleNamespace(output=self.directory, review_sha256="B"*64),
                                 budget(300, 120), {"sha256": "A"*64})
        self.assertEqual(code, 8)
        self.assertEqual(captured[0].mode, "resume")
        self.assertEqual(captured[0].stop_file, self.directory / "STOP")

    def test_old_file_mutation_survives_primary_failure_as_separate_veto(self):
        destination, inputs, row = self.production_fixture()
        output = self.directory / "new_envelope"
        def supervise(*args, **kwargs):
            path = destination / "batch_000003/report.json"
            path.write_bytes(path.read_bytes()+b" ")
            return quiet(9)
        with patch.object(resume, "ROOT", self.directory), \
             patch.object(resume, "proof", return_value={}), \
             patch.object(resume, "source_identity", return_value={"sha256": "A"*64}), \
             patch.object(probe, "gpu_snapshot", return_value=dict(used_mib=100, free_mib=20000, compute_apps=[])), \
             patch.object(sup, "executable_paths", return_value={}), \
             patch.object(sup, "supervise_process", side_effect=supervise):
            code = resume.parent(SimpleNamespace(output=output, max_wall_sec=300,
                deadline=resume.END.isoformat(), review_sha256="B"*64),
                budget(300, 120), {"sha256": "A"*64}, {})
        saved = probe.read_json(output / "report.json")
        self.assertEqual(code, 9)
        self.assertTrue(saved["original_error"])
        self.assertFalse(saved["old_files_unchanged"])
        self.assertEqual(saved["cleanup_errors"][0]["stage"], "원 배치와 inputs 불변 검산")

    def test_current_started_not_dated_module_started(self):
        output = self.directory / "test_result/evidence" / (resume.PREFIX+"fresh")
        start = time.monotonic()
        calls = []
        with patch.object(resume, "ROOT", self.directory), patch.object(resume, "STARTED", start), \
             patch.object(resume, "source_identity", return_value={"sha256": "A"*64}), \
             patch.object(resume, "proof", return_value={"review_sha256": "B"*64}), \
             patch.object(resume, "parent", side_effect=lambda args, active, *rest: calls.append(active.started) or 8), \
             patch.object(sup, "STARTED", start-100000), \
             patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0"}), patch.object(sys, "stdout", StringIO()):
            code = resume.main(["--execute", "--output", str(output), "--source-sha256", "A"*64,
                                "--review-sha256", "B"*64, "--max-wall-sec", "300"])
        self.assertEqual(code, 8)
        self.assertEqual(calls, [start])

    def test_wrong_base_identity_and_deadline_are_refused(self):
        with patch.object(probe, "source_identity", return_value={"sha256": "A"*64}):
            with self.assertRaises(ValueError):
                resume.source_identity()
        with patch.object(sys, "stdout", StringIO()):
            self.assertEqual(resume.main(["--check-only", "--max-wall-sec", "28801"]), 9)
            self.assertEqual(resume.main(["--check-only", "--deadline", "2026-10-26T08:01:00+00:00"]), 9)

    def test_check_only_isolated_no_torch_gpu_or_writes(self):
        before = set(self.directory.iterdir())
        result = REAL_RUN([sys.executable, "-I", "-B", "-X", "utf8", str(ENTRY), "--check-only"],
                          cwd=self.directory, capture_output=True, text=True, timeout=30,
                          env=dict(os.environ, CUDA_VISIBLE_DEVICES=""))
        self.assertEqual(result.returncode, 0, result.stderr+result.stdout)
        value = json.loads(result.stdout)
        self.assertFalse(value["torch_imported"])
        self.assertEqual((value["gpu_queries"], value["files_written"]), (0, 0))
        self.assertEqual(set(self.directory.iterdir()), before)

    def test_real_cpu_exit_zero_eight_nine_are_preserved(self):
        for code in (0, 8, 9):
            directory = self.directory / str(code)
            directory.mkdir()
            observed = sup.supervise_process([sys.executable, "-B", "-c",
                f"import sys,time; time.sleep(.12); sys.exit({code})"],
                directory, directory/"STOP",
                dict(producer=sys.executable, teacher=sys.executable, memory="/bin/sleep"),
                budget(5, 1), factory=cpu_popen)
            self.assertEqual(observed["actual_producer_exit"], code)
            self.assertEqual(resume.quiet(observed), code in (0, 8))

    def test_real_cpu_stop_self_exit_eight_without_term_is_valid(self):
        stop = self.directory / "STOP"
        code = "import sys,time; from pathlib import Path\nwhile not Path(sys.argv[1]).exists(): time.sleep(.01)\nsys.exit(8)"
        observed = sup.supervise_process([sys.executable, "-B", "-c", code, str(stop)],
            self.directory, stop, dict(producer=sys.executable, teacher=sys.executable, memory="/bin/sleep"),
            budget(2, .8), factory=cpu_popen)
        self.assertTrue(observed["stop_published"])
        self.assertEqual(observed["actual_producer_exit"], 8)
        self.assertFalse(observed["termination_requested"])
        self.assertFalse(observed["forced_cleanup"])
        self.assertTrue(resume.quiet(observed))


if __name__ == "__main__":
    unittest.main()

