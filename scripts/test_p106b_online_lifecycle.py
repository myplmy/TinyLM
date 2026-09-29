#!/usr/bin/env python3
"""CPU-only lifecycle/telemetry regressions; no real GPU, server or checkpoint."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diag_p106b_online_rate5 as online


class OnePoll:
    def __init__(self):
        self.calls = 0

    def wait(self, _seconds):
        self.calls += 1
        return self.calls > 1


class OnlineLifecycleTests(unittest.TestCase):
    def test_timeout_is_reported_not_silent_thread_death(self):
        samples, errors = [], []
        def timeout():
            raise online.subprocess.TimeoutExpired(["fixture-memory-reader"], 5)
        online.sample_memory(OnePoll(), timeout, samples, errors)
        self.assertEqual(errors, ["TimeoutExpired"])
        self.assertEqual(samples, [])
        with self.assertRaises(online.ToolFailure):
            online.require_sampler_health(errors)

    def test_low_free_is_resource_negative_not_telemetry_tool_error(self):
        samples, errors = [], []
        online.sample_memory(OnePoll(), lambda: (16000, 511), samples, errors)
        self.assertEqual(samples, [16000])
        with self.assertRaises(online.GateNegative):
            online.require_sampler_health(errors)

    def test_unknown_fusion_is_not_disabled(self):
        signals = {"gdn_ar_enabled": None, "gdn_chunked_enabled": None,
                   "kv_cache_space_warnings": 0, "attention_ubatch_failures": 0}
        online.capture_server_line("failed fixture", signals, [], "secret")
        self.assertIsNone(signals["gdn_ar_enabled"])

    def run_mock_until_exception(self, error):
        """Exercise real execute/finally with fake modules, transports and model factory."""
        class FakeTokenizer:
            @staticmethod
            def from_file(_path):
                return types.SimpleNamespace(token_to_id=lambda _name: 0)
        class FakeThread:
            def __init__(self, *args, **kwargs):
                pass
            def start(self):
                pass
            def join(self, timeout=None):
                pass
        class FakeOptimizer:
            def zero_grad(self, **kwargs):
                pass
        fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(
            synchronize=lambda: None, reset_peak_memory_stats=lambda: None))
        with tempfile.TemporaryDirectory(prefix="p106b_lifecycle_") as temporary:
            directory = Path(temporary) / "new_version"
            manifest = directory / "report.json"
            inputs = {"updates": 1}
            job = {"source_payload": {"source_turns": [{"user_text": "fixture", "assistant_text": "fixture"}]},
                   "teacher_task": "repair", "job_id": "A" * 64, "concept_id": "B" * 64}
            factory = (fake_torch, None, None, FakeOptimizer(), FakeOptimizer(),
                       types.SimpleNamespace(vocab_size=32), 2289, "fixture")
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.dict(sys.modules, {"torch": fake_torch,
                    "tokenizers": types.SimpleNamespace(Tokenizer=FakeTokenizer)}))
                for name, value in {
                    "ROOT": Path(temporary),
                    "check_only": lambda *args: inputs,
                    "_compute_apps": lambda: [],
                    "read_memory": lambda: (1000, 15000),
                    "asset_preflight": lambda **kwargs: {},
                    "public_source_jobs": lambda: ({"ko": [job], "en": [job]}, {}),
                    "paths": lambda *args: (directory, manifest),
                    "student_model_and_optimizers": lambda: factory,
                    "_free_port": lambda: 9999,
                    "_http_json": lambda *args, **kwargs: {},
                    "_kill_group": lambda _server: None,
                }.items():
                    stack.enter_context(patch.object(online, name, value))
                stack.enter_context(patch.object(online.threading, "Thread", FakeThread))
                stack.enter_context(patch.object(online.subprocess, "Popen",
                    return_value=types.SimpleNamespace(poll=lambda: None, stdout=[])))
                stack.enter_context(patch.object(online, "teacher_admission", side_effect=error))
                with contextlib.redirect_stdout(io.StringIO()):
                    code = online.execute("low", 60, "publiclow1")
            return code, json.loads(manifest.read_text(encoding="utf-8"))

    def test_interrupt_manifest_has_reason_phase_and_zero_updates(self):
        code, report = self.run_mock_until_exception(KeyboardInterrupt())
        self.assertEqual(code, 130)
        self.assertEqual(report["status"], "INTERRUPTED_USER")
        self.assertEqual(report["termination_phase"], "TEACHER_TOKEN_ADMISSION")
        self.assertEqual(report["updates_completed"], 0)
        self.assertNotEqual(report["reason"], "not_started")

    def test_admission_error_is_tool_failure_and_manifest_survives(self):
        code, report = self.run_mock_until_exception(ValueError("fixture token API"))
        self.assertEqual(code, 9)
        self.assertEqual(report["status"], "TOOL_FAILURE_PARTIAL")
        self.assertEqual(report["raw_counts"], {"TOKEN_ADMISSION_TOOL_FAILURE": 1})
        self.assertEqual(report["actually_trained_conversations"], 0)


if __name__ == "__main__":
    unittest.main()
