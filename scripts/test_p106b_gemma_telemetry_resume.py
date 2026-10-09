#!/usr/bin/env python3
"""CPU timeout/lifecycle fixtures; no real GPU, HF or model reads."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_gemma_telemetry_resume import RetryingMemoryReader, MAX_EVENTS
from scripts import diag_p106b_gemma_telemetry_resume as entry
from scripts import diag_p106b_gemma_literal_recovery as literal
from scripts.diag_p106b_online_rate5 import require_sampler_health, ToolFailure


def timeout():
    return subprocess.TimeoutExpired(["nvidia-smi", "fixture"], 5)


class ReaderTests(unittest.TestCase):
    def reader(self, outcomes):
        return RetryingMemoryReader(Mock(side_effect=outcomes), emit=lambda line: None,
                                    pause=lambda seconds: None)

    def test_old_one_timeout_latch_fails_and_new_bounded_reader_recovers(self):
        with self.assertRaises(ToolFailure):
            require_sampler_health(["TimeoutExpired"])
        reader = self.reader([timeout(), (9000, 7062)])
        self.assertEqual(reader(), (9000, 7062))
        proof = reader.snapshot()
        self.assertEqual((proof["timeout_attempts"], proof["recovered_calls"]), (1, 1))
        self.assertEqual(proof["measurement_coverage"], "GAPPED")
        self.assertFalse(proof["continuous_peak_verified"])
        self.assertEqual(proof["oom_safety"], "NOT_ESTABLISHED")

    def test_two_timeouts_then_success_share_three_total_attempts(self):
        reader = self.reader([timeout(), timeout(), (8767, 7295)])
        self.assertEqual(reader(), (8767, 7295))
        self.assertEqual(reader.reader.call_count, 3)
        self.assertEqual(reader.snapshot()["fatal_calls"], 0)

    def test_persistent_three_timeouts_never_become_a_success_or_fake_sample(self):
        reader = self.reader([timeout(), timeout(), timeout(), (1, 16000)])
        with self.assertRaises(subprocess.TimeoutExpired):
            reader()
        proof = reader.snapshot()
        self.assertEqual(reader.reader.call_count, 3)
        self.assertEqual(proof["successful_queries"], 0)
        self.assertIsNone(proof["observed_global_peak_mib"])
        self.assertEqual(proof["fatal_calls"], 1)

    def test_non_timeout_errors_are_immediate_and_not_retried(self):
        for error in (OSError("absent"), RuntimeError("driver failure"),
                      ValueError("bad row"), TimeoutError("server deadline")):
            with self.subTest(error=type(error).__name__):
                reader = self.reader([error, (1, 16000)])
                with self.assertRaises(type(error)):
                    reader()
                self.assertEqual(reader.reader.call_count, 1)
                self.assertEqual(reader.snapshot()["timeout_attempts"], 0)

    def test_low_free_value_passes_to_existing_guard_without_retry(self):
        reader = self.reader([(16000, 62)])
        self.assertEqual(reader(), (16000, 62))
        self.assertEqual(reader.reader.call_count, 1)
        with self.assertRaises(Exception):
            require_sampler_health(["FREE_LT_512"])

    def test_invalid_observation_is_not_counted_or_retried(self):
        for value in (("8767", 7295), (-1, 4), (True, 4)):
            reader = self.reader([value, (1, 16000)])
            with self.assertRaises(ValueError):
                reader()
            self.assertEqual(reader.snapshot()["successful_queries"], 0)
            self.assertEqual(reader.reader.call_count, 1)

    def test_gap_time_includes_failed_attempt_and_successful_retry_not_interpolation(self):
        now = [0.0]
        def read():
            now[0] += 5.0 if now[0] == 0 else 1.0
            if now[0] == 5.0:
                raise timeout()
            return 9000, 7062
        reader = RetryingMemoryReader(read, emit=lambda line: None, clock=lambda: now[0],
                                     pause=lambda seconds: now.__setitem__(0, now[0]+seconds))
        reader()
        self.assertAlmostEqual(reader.snapshot()["unobserved_query_window_sec"], 6.2)
        self.assertEqual(reader.snapshot()["observed_global_peak_mib"], 9000)

    def test_event_history_is_bounded_but_all_attempts_count_and_hash(self):
        reader = self.reader([item for i in range(100) for item in (timeout(), (8767, 7295))])
        for i in range(100):
            reader()
        proof = reader.snapshot()
        self.assertEqual(len(proof["events"]), MAX_EVENTS)
        self.assertEqual(proof["event_count"], 200)
        self.assertEqual(proof["omitted_event_count"], 72)
        self.assertEqual(proof["timeout_attempts"], 100)
        self.assertEqual(len(proof["event_chain_sha256"]), 64)
        self.assertLess(len(json.dumps(proof).encode()), 100000)

    def test_invalid_attempt_setting_is_refused(self):
        for attempts in (0, 4):
            with self.assertRaises(ValueError):
                RetryingMemoryReader(Mock(), max_attempts=attempts)


class EntryTests(unittest.TestCase):
    def test_programmatic_mode_cannot_escape_continuation_scope(self):
        with patch.object(literal.previous, "guarded_dispatch", side_effect=AssertionError("must not dispatch")):
            with self.assertRaises(ValueError):
                entry.run_resume(SimpleNamespace(mode="produce"), execute=True)

    def test_runtime_scope_restores_old_functions_even_on_failure(self):
        before = (entry.memory_source.read_memory, entry.lifecycle.Session.memory)
        reader = RetryingMemoryReader(Mock(return_value=(10, 16000)))
        with self.assertRaises(RuntimeError), entry.telemetry_scope(reader):
            self.assertIs(entry.memory_source.read_memory, reader)
            raise RuntimeError("fixture")
        self.assertEqual(before, (entry.memory_source.read_memory, entry.lifecycle.Session.memory))

    def test_memory_report_attaches_gap_proof_without_weakening_original_checks(self):
        reader = RetryingMemoryReader(Mock(return_value=(8767, 7295)), emit=lambda line: None)
        reader()
        session = SimpleNamespace(check=lambda: None, baseline_used=1430,
                                  samples=[dict(used=8767, free=7295, rss_mib=6861)])
        with entry.telemetry_scope(reader):
            result = entry.lifecycle.Session.memory(session)
        self.assertIn("telemetry_recovery", result)
        self.assertEqual(result["resource_safety"], "NOT_ESTABLISHED")
        self.assertEqual(result["sampled_gpu_global_peak_mib"], 8767)

    def test_literal_scope_and_generation_input_contract_are_not_replaced(self):
        args = SimpleNamespace(mode="resume", max_wall_sec=21600)
        before = literal.previous.PATHS
        with patch.object(literal.previous, "guarded_dispatch", return_value=8) as child:
            self.assertEqual(entry.run_resume(args, execute=True), 8)
        child.assert_called_once_with(args, execute=True)
        self.assertEqual(literal.previous.PATHS, before)

    def test_check_only_cannot_query_memory_execute_subprocess_or_write_receipt(self):
        with patch.object(sys, "argv", ["fixture", "--mode", "resume", "--check-only"]), \
                patch.object(entry, "run_resume", return_value=0) as child, \
                patch.object(entry, "execute_resume", side_effect=AssertionError("GPU forbidden")), \
                patch.object(entry.memory_source, "read_memory", side_effect=AssertionError("query forbidden")), \
                patch.object(entry.subprocess, "run", side_effect=AssertionError("subprocess forbidden")):
            self.assertEqual(entry.main(), 0)
        self.assertFalse(child.call_args.kwargs["execute"])

    def test_new_receipt_is_write_once_separate_from_generation_inputs(self):
        with tempfile.TemporaryDirectory(prefix="p106b_telemetry_fixture_") as tmp, \
                patch.object(entry, "ROOT", Path(tmp)), \
                patch.object(entry, "safe_repo_path", side_effect=lambda path: path), \
                patch.object(entry, "digest", return_value="A"*64), \
                patch.object(entry, "run_resume", return_value=8), redirect_stdout(io.StringIO()):
            args = SimpleNamespace(mode="resume", max_wall_sec=60)
            self.assertEqual(entry.execute_resume(args), 8)
            files = list((Path(tmp)/"test_result/evidence").glob("*.json"))
            self.assertEqual(len(files), 1)
            proof = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(proof["returncode"], 8)
            self.assertFalse(proof["generation_contract_changed"])
            self.assertFalse(proof["original_reports_mutated"])
            self.assertEqual(proof["telemetry"]["calls"], 0)
            self.assertFalse((Path(tmp)/"HF").exists())

    def test_new_actual_entry_is_pipeline_not_just_a_unit_test_command(self):
        with patch.object(sys, "argv", ["fixture", "--mode", "resume", "--execute"]), \
                patch.object(entry, "pipeline", return_value={"returncode":8}) as stages, \
                redirect_stdout(io.StringIO()):
            self.assertEqual(entry.main(), 8)
        self.assertEqual([p[0] for p in stages.call_args.args[0]],
                         ["REGRESSION", "PREFLIGHT", "EXECUTE"])
        self.assertEqual(stages.call_args.kwargs["experiment"], "P106B_GEMMA_TELEMETRY_V1_resume")


if __name__ == "__main__":
    unittest.main()
