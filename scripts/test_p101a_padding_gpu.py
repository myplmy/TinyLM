#!/usr/bin/env python3
"""Root-run stdlib/mock contracts; no torch/model/data/GPU/real-asset access.

Writing this file is not a test PASS. The authorized root separately runs these
tests, existing CPU numerical regressions, and the opt-in actual-parent worker.
Every filesystem fixture is confined to its own temporary directory.
"""
from __future__ import annotations

import argparse
import builtins
import copy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import runpy
import signal
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p101a_padding_gpu as worker


def fake_record(length, token=7, targets=2):
    return SimpleNamespace(x=[token] * length,
        y=[-100] * (length - targets) + [token] * targets,
        segments=[0] * (length - targets) + [1] * targets)


def fake_groups():
    return [[fake_record(2 + ((i * 8 + j) % 140), token=5 + i * 8 + j)
             for j in range(8)] for i in range(16)]


def put(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)
    return path


class ImportAndSourceContract(unittest.TestCase):
    def test_import_never_imports_heavy_packages_or_queries_gpu(self):
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "tokenizers", "transformers", "numpy", "tinylm"}:
                raise AssertionError("source-only import attempted heavy package: " + name)
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded), patch.object(worker.subprocess, "run", side_effect=AssertionError("GPU query")):
            loaded = runpy.run_path(str(ROOT / worker.SCRIPT), run_name="p101a_source_import_fixture")
        self.assertEqual(loaded["SEED"], 1337)
        self.assertEqual(loaded["ABBA"], ("fixed1024", "crop128", "crop128", "fixed1024"))

    def test_check_only_calls_no_execution_or_assets(self):
        stream = io.StringIO()
        with patch.object(worker, "source_manifest", return_value={"scripts/mock.py": "A" * 64}), \
             patch.object(worker, "literal_tolerances", return_value={"provenance": "mock-source"}), \
             patch.object(worker, "execute", side_effect=AssertionError("execute")), \
             patch.object(Path, "open", side_effect=AssertionError("asset/file access after source mocks")), \
             patch.object(worker.subprocess, "run", side_effect=AssertionError("GPU query")), \
             patch("sys.stdout", stream):
            self.assertEqual(worker.main(["--check-only"]), 0)
        result = json.loads(stream.getvalue())
        self.assertEqual(result["status"], "SOURCE_ONLY_READY")
        self.assertEqual((result["model_loads"], result["asset_reads"], result["gpu_calls"], result["checkpoint_writes"]), (0, 0, 0, 0))

    def test_manifest_recurses_only_explicit_local_python_imports(self):
        with tempfile.TemporaryDirectory(prefix="p101a_source_mock_") as temporary:
            root = Path(temporary)
            put(root, "scripts/diag_p101a_sft_mtp.py", "CODE=('scripts/leaf.py',)\nfrom scripts import helper\n")
            put(root, "scripts/leaf.py", "import json\n")
            put(root, "scripts/helper.py", "import tinylm.model\nfrom scripts import diag_p101a_sft_mtp\n")
            put(root, "tinylm/__init__.py", "# source fixture only\n")
            put(root, "tinylm/model.py", "# no real model\n")
            opened = []
            original = worker.digest
            def source_digest(path):
                opened.append(path.relative_to(root).as_posix())
                return original(path)
            with patch.object(worker, "SOURCES", ("scripts/diag_p101a_sft_mtp.py",)), patch.object(worker, "digest", side_effect=source_digest):
                manifest = worker.source_manifest(root)
            self.assertEqual(set(manifest), {"scripts/diag_p101a_sft_mtp.py", "scripts/leaf.py", "scripts/helper.py", "tinylm/__init__.py", "tinylm/model.py"})
            self.assertEqual(set(opened), set(manifest))
            self.assertTrue(all(name.endswith(".py") for name in opened))
            self.assertEqual(worker.identity(manifest), worker.identity(dict(reversed(list(manifest.items())))))

    def test_source_manifest_rejects_asset_CODE_without_reading_asset(self):
        with tempfile.TemporaryDirectory(prefix="p101a_source_mock_") as temporary:
            root = Path(temporary)
            put(root, "scripts/diag_p101a_sft_mtp.py", "CODE=('HF/model.json',)\n")
            with patch.object(worker, "SOURCES", ()):
                with self.assertRaisesRegex(ValueError, "Python-only"):
                    worker.source_manifest(root)

    def test_existing_tolerances_are_ast_literals_not_executed_tests(self):
        with tempfile.TemporaryDirectory(prefix="p101a_tolerance_mock_") as temporary:
            root = Path(temporary)
            put(root, "scripts/test_p070b_cla_routes.py", "import torch\nATOL=1e-5\nRTOL=1e-4\nraise RuntimeError('not executed')\n")
            put(root, "scripts/test_p101a_padding_crop.py", "import torch\nACCUM_ATOL,ACCUM_RTOL=2e-6,1e-5\n")
            rules = worker.literal_tolerances(root)
        self.assertEqual(rules["loss_and_norm"], {"atol": 1e-5, "rtol": 1e-4})
        self.assertEqual(rules["gradients_and_update"], {"atol": 2e-6, "rtol": 1e-5})
        self.assertIn("not GPU calibrated", rules["interpretation"])

    def test_execute_arguments_require_explicit_identity_and_output(self):
        with patch.object(worker, "source_manifest", return_value={}), patch.object(worker, "literal_tolerances", return_value={}), patch("sys.stderr", io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                worker.main(["--execute"])
        self.assertEqual(caught.exception.code, 2)


class ScheduleAndRecordContract(unittest.TestCase):
    def test_exact_schedule_is_four_fresh_blocks_24_updates(self):
        schedule = worker.block_schedule()
        self.assertEqual(tuple(block["policy"] for block in schedule), worker.ABBA)
        self.assertEqual(sum(len(block["updates"]) for block in schedule), 24)
        for block in schedule:
            self.assertEqual(block["updates"], [dict(index=i, phase="warmup" if i < 2 else "measured") for i in range(6)])
        self.assertEqual(len(worker.POLICIES), 2)  # One separate correctness update each.

    def test_all_128_records_order_and_global_target_denominator_are_stable(self):
        groups = fake_groups()
        before = copy.deepcopy(groups)
        plan = worker.update_plan(groups)
        self.assertEqual(plan["rows"], 128)
        self.assertEqual(plan["assistant_targets"], 256)
        self.assertEqual(plan["actual_x_tokens"], sum(len(r.x) for micro in groups for r in micro))
        self.assertEqual(plan["padded_slots"]["fixed1024"], 128 * 1024)
        self.assertLess(plan["padded_slots"]["crop128"], plan["padded_slots"]["fixed1024"])
        self.assertEqual(groups, before)
        self.assertEqual(len(plan["micro_order_sha256"]), 16)
        changed = copy.deepcopy(groups)
        changed[0][0].x[0] += 1
        self.assertNotEqual(worker.update_plan(changed)["ordered_records_sha256"], plan["ordered_records_sha256"])
        changed = copy.deepcopy(groups)
        changed[0].reverse()
        self.assertNotEqual(worker.update_plan(changed)["ordered_records_sha256"], plan["ordered_records_sha256"])

    def test_width_uses_128_ceiling_and_never_reorders_or_truncates(self):
        for length, expected in ((2, 128), (128, 128), (129, 256), (1024, 1024)):
            micro = [fake_record(length, token=8 + i) for i in range(8)]
            before = copy.deepcopy(micro)
            self.assertEqual(worker.width_for(micro, "crop128"), expected)
            self.assertEqual(worker.width_for(micro, "fixed1024"), 1024)
            self.assertEqual(micro, before)
        with self.assertRaises(ValueError):
            worker.width_for([fake_record(1025) for _ in range(8)], "crop128")

    def test_partial_update_or_micro_is_never_silently_accepted(self):
        groups = fake_groups()
        for incomplete in (groups[:-1], groups + groups[:1], [groups[0][:-1]] + groups[1:]):
            with self.assertRaisesRegex(ValueError, "no sample reduction"):
                worker.update_plan(incomplete)

    def test_masks_targets_and_assistant_owners_must_match(self):
        invalid = [fake_record(4) for _ in range(6)]
        invalid[0].y[0] = 11
        invalid[1].segments[-1] = 0
        invalid[2].x[0] = 32768
        invalid[3].y[-1] = 32768
        invalid[4].segments[-1] = -1
        invalid[5].segments.pop()
        for record in invalid:
            with self.subTest(record=record), self.assertRaises(ValueError):
                worker.record_value(record)
        no_targets = SimpleNamespace(x=[1, 2], y=[-100, -100], segments=[0, 0])
        with self.assertRaisesRegex(ValueError, "assistant targets"):
            worker.record_value(no_targets)

    def test_scalar_diagnostic_uses_reference_relative_rule_without_retuning(self):
        tolerance = {"atol": 2e-6, "rtol": 1e-5}
        self.assertTrue(worker.scalar_difference(1.0, 1.000001, tolerance)["close"])
        self.assertFalse(worker.scalar_difference(0.0, .01, tolerance)["close"])
        self.assertFalse(worker.scalar_difference(float("nan"), 0.0, tolerance)["close"])
        worker.canonical(worker.scalar_difference(0.0, 10.0, tolerance))  # No Infinity in evidence JSON.


class AdmissionAndEvidenceContract(unittest.TestCase):
    def test_workspace_cleanup_is_explicit_and_does_not_relax_zero_rule(self):
        clear = Mock()
        cuda = SimpleNamespace(synchronize=Mock(), memory_allocated=Mock(side_effect=[8519680, 0]), empty_cache=Mock())
        torch = SimpleNamespace(cuda=cuda, _C=SimpleNamespace(_cuda_clearCublasWorkspaces=clear))
        result = worker.clear_runtime_workspace(torch)
        clear.assert_called_once_with()
        self.assertEqual(result['before_workspace_clear_bytes'], 8519680)
        self.assertEqual(result['after_workspace_clear_bytes'], 0)
        self.assertTrue(result['remaining_zero'])

    def test_workspace_cleanup_never_calls_missing_api_or_hides_residual(self):
        cuda = SimpleNamespace(synchronize=Mock(), memory_allocated=Mock(return_value=512), empty_cache=Mock())
        with self.assertRaisesRegex(RuntimeError, 'unsupported'):
            worker.clear_runtime_workspace(SimpleNamespace(cuda=cuda, _C=SimpleNamespace()))
        result = worker.clear_runtime_workspace(SimpleNamespace(cuda=cuda, _C=SimpleNamespace(_cuda_clearCublasWorkspaces=Mock())))
        self.assertFalse(result['remaining_zero'])
        self.assertEqual(result['after_workspace_clear_bytes'], 512)

    def test_recovery_namespace_cannot_overwrite_v1_partial(self):
        with tempfile.TemporaryDirectory(prefix='p101a_recovery_mock_') as temporary:
            root = Path(temporary)
            original = f'test_result/evidence/{worker.TAG}/correctness'
            recovered = f'test_result/evidence/{worker.WORKSPACE_TAG}/correctness'
            with self.assertRaises(ValueError):
                worker.output_path(original, 'correctness', root, release_workspace=True)
            self.assertEqual(worker.output_path(recovered, 'correctness', root, release_workspace=True), root/recovered)

    def setUp(self):
        self.now = datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc)
        self.args = argparse.Namespace(deadline="2026-10-23T16:30:00+09:00", max_wall_sec=1200, mode="correctness")

    def test_deadline_timezone_hard_stop_and_1200_second_bound(self):
        self.assertEqual(worker.validate_execution(self.args, self.now), worker.HARD_STOP)
        for deadline in ("2026-10-23T16:30:00", "2026-10-23T16:30:01+09:00", "2026-10-24T10:00:00+09:00", "2026-10-23T13:00:00+09:00"):
            with self.subTest(deadline=deadline), self.assertRaises(ValueError):
                worker.validate_execution(argparse.Namespace(**dict(vars(self.args), deadline=deadline)), self.now)
        for seconds in (59, 1201, 60.5, True):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                worker.validate_execution(argparse.Namespace(**dict(vars(self.args), max_wall_sec=seconds)), self.now)
        with self.assertRaisesRegex(ValueError, "does not fit"):
            worker.validate_execution(self.args, worker.HARD_STOP - timedelta(seconds=1199))

    def test_guard_checks_both_absolute_and_monotonic_time(self):
        with patch.object(worker.time, "perf_counter", return_value=10):
            guard = worker.Guard(worker.HARD_STOP, 1200)
        with patch.object(worker, "utc_now", return_value=self.now), patch.object(worker.time, "perf_counter", return_value=1210):
            with self.assertRaises(TimeoutError):
                guard.check("micro0")
        with patch.object(worker, "utc_now", return_value=worker.HARD_STOP), patch.object(worker.time, "perf_counter", return_value=11):
            with self.assertRaises(TimeoutError):
                guard.check("micro1")

    def test_wall_limit_restores_signal_handler_without_real_alarm(self):
        previous = object()
        with patch.object(worker.signal, "getitimer", return_value=(0, 0)), \
             patch.object(worker.signal, "getsignal", return_value=previous), \
             patch.object(worker.signal, "signal") as handler, patch.object(worker.signal, "setitimer") as timer:
            with self.assertRaisesRegex(RuntimeError, "partial"), worker.wall_limit(1200):
                raise RuntimeError("partial")
        self.assertEqual(timer.call_args_list[0].args, (signal.ITIMER_REAL, 1200))
        self.assertEqual(timer.call_args_list[-1].args, (signal.ITIMER_REAL, 0))
        self.assertEqual(handler.call_args_list[-1].args, (signal.SIGALRM, previous))
        with patch.object(worker.signal, "getitimer", return_value=(1, 0)), self.assertRaisesRegex(ValueError, "another active"):
            with worker.wall_limit(60):
                self.fail("active timer must be preserved")

    def test_gpu_mock_allows_own_empty_context_but_no_foreign_or_allocated_model(self):
        def runner(apps, memory="400, 15976\n"):
            return Mock(side_effect=[SimpleNamespace(returncode=0, stdout=apps), SimpleNamespace(returncode=0, stdout=memory)])
        self.assertFalse(worker.gpu_admission(runner=runner(""))["self_context_allowed"])
        cuda = SimpleNamespace(is_initialized=lambda: True, memory_allocated=lambda: 0)
        fake_torch = SimpleNamespace(cuda=cuda)
        with patch.object(worker.os, "getpid", return_value=321):
            self.assertTrue(worker.gpu_admission(fake_torch, runner=runner("321, python\n"))["self_context_allowed"])
            with self.assertRaisesRegex(ValueError, "foreign"):
                worker.gpu_admission(fake_torch, runner=runner("999, python\n"))
        cuda.memory_allocated = lambda: 1
        with self.assertRaisesRegex(ValueError, "still allocated"):
            worker.gpu_admission(fake_torch, runner=runner(""))
        with self.assertRaisesRegex(ValueError, "14000"):
            worker.gpu_admission(runner=runner("", "2000, 13999\n"))

    def test_exact_output_write_once_and_partial_event_retention(self):
        with tempfile.TemporaryDirectory(prefix="p101a_evidence_mock_") as temporary:
            root = Path(temporary)
            relative = f"test_result/evidence/{worker.TAG}/correctness"
            output = worker.output_path(relative, "correctness", root)
            self.assertEqual(output, root / relative)
            for wrong in (relative + "_retry", "test_result/evidence/other/correctness", "/outside/evidence"):
                with self.assertRaises(ValueError):
                    worker.output_path(wrong, "correctness", root)
            output.mkdir(parents=True)
            with self.assertRaises(FileExistsError):
                worker.output_path(relative, "correctness", root)
            report = output / "report.json"
            worker.write_new(report, {"status": "PARTIAL"})
            original = report.read_bytes()
            with self.assertRaises(FileExistsError):
                worker.write_new(report, {"status": "OVERWRITE"})
            self.assertEqual(report.read_bytes(), original)
            journal = worker.Journal(output / "events.jsonl")
            journal.append({"event": "micro_complete"})
            with patch.object(worker, "MAX_BYTES", journal.bytes), self.assertRaisesRegex(ValueError, "20MB"):
                journal.append({"event": "oversize"})
            journal.close()
            self.assertEqual(json.loads((output / "events.jsonl").read_text()), {"event": "micro_complete"})
            with patch.object(worker, "MAX_BYTES", 2), self.assertRaisesRegex(ValueError, "20MB"):
                worker.write_new(output / "oversize.json", {"too": "large"})
            self.assertFalse((output / "oversize.json").exists())

    def test_protected_escape_and_symlink_paths_are_rejected(self):
        with patch.object(Path, "is_symlink", side_effect=AssertionError("protected path must not be inspected")):
            for protected in ("datasets/TinyDataset/private.py", "../outside.py", "/absolute.py"):
                with self.assertRaises(ValueError):
                    worker.safe_path(protected)
        with tempfile.TemporaryDirectory(prefix="p101a_path_mock_") as temporary:
            root = Path(temporary)
            (root / "real").mkdir()
            (root / "linked").symlink_to(root / "real", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "linked"):
                worker.safe_path("linked/report.json", root)


if __name__ == "__main__":
    unittest.main()
