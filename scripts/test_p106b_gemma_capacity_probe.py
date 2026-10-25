#!/usr/bin/env python3
"""Gemma 자원 관측기의 격리 CPU 회귀. 모델과 GPU 호출은 금지한다."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import importlib.util
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ENTRY = ROOT / "handoff/audit/oct26_research/probe_gemma_capacity.py"
spec = importlib.util.spec_from_file_location("capacity_probe_cpu", ENTRY)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
sup = probe.supervisor()
REAL_POPEN = subprocess.Popen
REAL_RUN = subprocess.run


def cpu_popen(command, *args, **kwargs):
    if isinstance(command, str) or Path(command[0]).resolve() != Path(sys.executable).resolve():
        raise AssertionError("모의 호출 외에는 CPU Python 자식만 허용한다")
    return REAL_POPEN(command, *args, **kwargs)


def reply(finish="stop"):
    return dict(choices=[dict(finish_reason=finish, message=dict(content="ANSWER: blue", reasoning_content=""))],
                usage=dict(completion_tokens=3), timings=dict(predicted_n=3, predicted_ms=10,
                draft_n=2, draft_n_accepted=1))


def budget(seconds=10, reserve=1):
    return sup.Budget(seconds, time.time() + seconds + 2, started=time.monotonic(), reserve=reserve)


def quiet(code=0):
    return dict(actual_producer_exit=code, process_started=True, original_error=None,
                cleanup_errors=[], forced_cleanup=False, stop_published=False,
                termination_requested=False, deferred_signals=[], parent_witness_errors=[],
                subreaper_restored=True, controller_group_quiescent=True)


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gemma_capacity_cpu_")
        self.directory = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.addCleanup(patch.stopall)
        patch.object(subprocess, "Popen", side_effect=cpu_popen).start()
        patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": ""}).start()

    def request_owner(self, seconds=60, reserve=1):
        return probe.Requests(self.directory, budget(seconds, reserve), self.directory / "STOP")

    def test_admission_boundary_and_competing_compute(self):
        probe.admit(dict(free_mib=11264, compute_apps=[]))
        for snapshot in (dict(free_mib=11263, compute_apps=[]),
                         dict(free_mib=20000, compute_apps=["123, foreign"])):
            with self.assertRaises(probe.Hold):
                probe.admit(snapshot)

    def test_gpu_snapshot_uses_mock_queries_only(self):
        calls = []
        def run(command, **kwargs):
            calls.append((command, kwargs["timeout"]))
            text = "877, 15000\n" if "--query-gpu=memory.used,memory.free" in command else ""
            return SimpleNamespace(returncode=0, stdout=text)
        result = probe.gpu_snapshot(budget(), runner=run)
        self.assertEqual((result["used_mib"], result["free_mib"]), (877, 15000))
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(0 < timeout <= 5 for _, timeout in calls))

    def test_invalid_gpu_metadata_is_error(self):
        for text in ("NaN, 20000\n", "1, 2\n3, 4\n", "-1, 20000\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                probe.gpu_snapshot(budget(), runner=lambda *a, **k: SimpleNamespace(returncode=0, stdout=text))

    def test_generation_four_transport_limit(self):
        owner = self.request_owner()
        transported = []
        def transport(session, route, payload, timeout):
            transported.append(route)
            return reply() if route == "/v1/chat/completions" else {}
        session = SimpleNamespace(key="SECRET")
        for _ in range(7):
            owner.call(session, transport, "/health")
        for _ in range(4):
            owner.call(session, transport, "/v1/chat/completions", {})
        with self.assertRaisesRegex(ValueError, "네 번"):
            owner.call(session, transport, "/v1/chat/completions", {})
        self.assertEqual(transported.count("/v1/chat/completions"), 4)
        self.assertEqual(owner.generations, 4)
        self.assertEqual(len(owner.metrics), 4)
        self.assertEqual(len(list(self.directory.glob("raw_*.json"))), 4)

    def test_generation_failure_consumes_attempt_and_keeps_http_evidence(self):
        owner = self.request_owner()
        def transport(*_):
            raise HTTPError("http://127.0.0.1", 500, "error", {},
                            BytesIO(b'{"error":{"message":"Bearer SECRET"}}'))
        with self.assertRaises(HTTPError):
            owner.call(SimpleNamespace(key="SECRET"), transport, "/v1/chat/completions", {})
        self.assertEqual(owner.generations, 1)
        value = probe.read_json(self.directory / "http_error_01.json")
        self.assertNotIn("SECRET", json.dumps(value))
        self.assertFalse(value["whole_body_preserved"])

    def test_missing_usage_preserves_reply_and_refuses_complete(self):
        owner = self.request_owner()
        value = reply()
        value.pop("usage")
        with self.assertRaises(ValueError):
            owner.call(SimpleNamespace(key="x"), lambda *_: value, "/v1/chat/completions", {})
        self.assertIn("reply", probe.read_json(self.directory / "raw_01.json"))
        self.assertEqual(owner.metrics, [])

    def test_nonfinite_reply_is_preserved_as_text_and_rejected(self):
        owner = self.request_owner()
        value = dict(reply(), extra=float("nan"))
        with self.assertRaisesRegex(ValueError, "비유한"):
            owner.call(SimpleNamespace(key="x"), lambda *_: value, "/v1/chat/completions", {})
        saved = probe.read_json(self.directory / "raw_01.json")
        self.assertFalse(saved["finite_reply"])
        self.assertIn("NaN", saved["invalid_reply_json"])

    def test_request_timeout_uses_remaining_parent_budget(self):
        owner = self.request_owner(seconds=60, reserve=10)
        actual = owner.limit(300)
        self.assertGreater(actual, 0)
        self.assertLessEqual(actual, 30)
        with self.assertRaises(ValueError):
            owner.limit(float("inf"))

    def test_stop_prevents_any_transport(self):
        owner = self.request_owner()
        owner.stop_file.touch()
        with self.assertRaises(TimeoutError):
            owner.call(SimpleNamespace(), lambda *_: self.fail("HTTP가 호출됐다"), "/health")
        self.assertEqual(owner.routes, {})

    def test_stop_during_response_is_not_success(self):
        owner = self.request_owner()
        def transport(*_):
            owner.stop_file.touch()
            return reply()
        with self.assertRaises(TimeoutError):
            owner.call(SimpleNamespace(key="x"), transport, "/v1/chat/completions", {})
        self.assertTrue((self.directory / "raw_01.json").is_file())

    def test_request_patch_restores_original_method_on_error(self):
        class Session:
            def request(self, route, payload=None, timeout=10):
                return {}
        module = SimpleNamespace(Session=Session)
        original = Session.request
        with self.assertRaises(RuntimeError):
            with self.request_owner().scope(module):
                self.assertIsNot(Session.request, original)
                raise RuntimeError("원 오류")
        self.assertIs(Session.request, original)

    def test_production_payload_reuses_real_v3_and_exact_addendum(self):
        from scripts import p106b_gemma_task_contract_v3 as tasks
        from scripts import p106b_gemma_teacher as gemma
        for case in probe.workload():
            expected = tasks.payload(case["source"], case["language"], case["task"], case["seed"])
            expected["messages"][0]["content"] += probe.production_addendum()
            actual = probe.production_payload(case)
            self.assertEqual(actual, expected)
            self.assertEqual({key: actual[key] for key in gemma.SAMPLER}, gemma.SAMPLER)
            self.assertEqual((actual["max_tokens"], actual["thinking_budget_tokens"]), (3072, 1024))
            self.assertTrue(actual["messages"][0]["content"].startswith("<|think|>"))

    def test_reply_completion_requires_four_nonempty_stop_responses(self):
        self.assertTrue(probe.complete_replies([reply() for _ in range(4)]))
        self.assertFalse(probe.complete_replies([reply() for _ in range(3)]))
        self.assertFalse(probe.complete_replies([reply("length") for _ in range(4)]))
        empty = reply()
        empty["choices"][0]["message"]["content"] = ""
        self.assertFalse(probe.complete_replies([empty for _ in range(4)]))

    def test_memory_requires_real_finite_nonzero_samples(self):
        value = dict(sample_count=1, sampled_gpu_global_peak_mib=8771,
                     sampled_gpu_min_free_mib=4096, baseline_gpu_used_mib=500,
                     owned_server_peak_rss_mib=6500)
        probe.validate_memory(value)
        for key, bad in (("sample_count", 0), ("owned_server_peak_rss_mib", float("inf")),
                         ("sampled_gpu_global_peak_mib", -1), ("sample_count", True)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                probe.validate_memory(dict(value, **{key: bad}))

    def test_cleanup_kill_and_live_thread_are_not_success(self):
        process = SimpleNamespace(poll=lambda: -signal.SIGKILL)
        session = SimpleNamespace(process=process, workers=[])
        memory = SimpleNamespace(process=SimpleNamespace(poll=lambda: -signal.SIGTERM),
                                 worker=SimpleNamespace(is_alive=lambda: True))
        state = probe.cleanup_state(session, memory)
        self.assertEqual(len(state["errors"]), 2)

    def test_supervision_every_veto_beats_child_zero(self):
        self.assertTrue(probe.supervision_ok(quiet()))
        for key, value in (("forced_cleanup", True), ("cleanup_errors", [{}]),
                           ("original_error", {}), ("stop_published", True),
                           ("parent_witness_errors", [{}]), ("subreaper_restored", False),
                           ("controller_group_quiescent", False), ("actual_producer_exit", 8)):
            with self.subTest(key=key):
                changed = dict(quiet(), **{key: value})
                if key == "original_error":
                    changed[key] = {"message": "원 오류"}
                self.assertFalse(probe.supervision_ok(changed))
        self.assertTrue(probe.supervision_ok(quiet(8), 8))

    def test_write_once_size_and_nonfinite_contract(self):
        path = self.directory / "once.json"
        probe.timed_write(path, dict(x=1), budget())
        with self.assertRaises(FileExistsError):
            probe.timed_write(path, dict(x=2), budget())
        with self.assertRaises(ValueError):
            probe.timed_write(self.directory / "nan.json", dict(x=float("nan")), budget())
        with patch.object(probe, "MAX_BYTES", 20), self.assertRaises(ValueError):
            probe.timed_write(self.directory / "large.json", dict(x="a" * 100), budget())

    def test_storage_delay_counts_against_parent_time(self):
        active = budget(.05, .005)
        original = os.fsync
        def delayed(fd):
            original(fd)
            time.sleep(.06)
        with patch.object(os, "fsync", delayed), self.assertRaises(TimeoutError):
            probe.timed_write(self.directory / "delayed.json", dict(x=1), active)
        self.assertTrue((self.directory / "delayed.json").is_file())

    def test_same_length_source_mutation_changes_identity(self):
        source = self.directory / "scripts"
        source.mkdir()
        (source / "one.py").write_text("VALUE=1\n")
        with patch.object(probe, "SEEDS", ("scripts/one.py",)), \
             patch.object(probe, "production_addendum", return_value="fixed"):
            before = probe.source_identity(self.directory)
            (source / "one.py").write_text("VALUE=2\n")
            after = probe.source_identity(self.directory)
        self.assertNotEqual(before["sha256"], after["sha256"])
        self.assertEqual((source / "one.py").stat().st_size, len("VALUE=1\n"))

    def test_source_symlink_is_refused(self):
        target = self.directory / "target.py"
        target.write_text("VALUE=1\n")
        (self.directory / "link.py").symlink_to(target)
        with self.assertRaises(ValueError):
            probe.regular("link.py", self.directory)

    def test_bootstrap_argv_uses_companion_not_dated_entry(self):
        args = SimpleNamespace(output=self.directory, max_wall_sec=590,
                               deadline=probe.END.isoformat())
        command = probe.child_command(args, {"sha256": "A" * 64}, budget())
        self.assertEqual(Path(command[5]), ENTRY)
        self.assertIn("--worker", command)
        self.assertIn("--parent-started", command)
        self.assertFalse(any("supported_supervisor.py" in cell for cell in command))

    def test_main_uses_explicit_fresh_started_value(self):
        fake_root = self.directory
        output = fake_root / "test_result/evidence" / (probe.PREFIX + "fresh")
        output.parent.mkdir(parents=True)
        started = time.monotonic()
        observed = []
        def parent(args, active, receipt):
            observed.append(active.started)
            return 0
        with patch.object(probe, "ROOT", fake_root), patch.object(probe, "STARTED", started), \
             patch.object(probe, "source_identity", return_value={"sha256": "A" * 64}), \
             patch.object(probe, "parent", side_effect=parent), patch.object(sup, "STARTED", started - 100000), \
             patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0"}), patch.object(sys, "stdout", StringIO()):
            code = probe.main(["--execute", "--output", str(output), "--source-sha256", "A" * 64])
        self.assertEqual(code, 0)
        self.assertEqual(observed, [started])

    def test_stdout_delay_creates_append_only_terminal_veto(self):
        output = self.directory / "test_result/evidence" / (probe.PREFIX + "delay")
        output.parent.mkdir(parents=True)
        original_budget = sup.Budget
        class SlowOutput(StringIO):
            delayed = False
            def write(self, text):
                if not self.delayed:
                    self.delayed = True
                    time.sleep(.2)
                return super().write(text)
        def parent(args, active, receipt):
            output.mkdir()
            sup.append_terminal(output, dict(event="OBSERVATION", returncode=0))
            return 0
        with patch.object(probe, "ROOT", self.directory), \
             patch.object(probe, "STARTED", time.monotonic()), \
             patch.object(probe, "source_identity", return_value={"sha256": "A" * 64}), \
             patch.object(probe, "parent", side_effect=parent), \
             patch.object(sup, "Budget", side_effect=lambda *a, **k: original_budget(.1, time.time()+2,
                         started=time.monotonic(), reserve=.01)), \
             patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0"}), \
             patch.object(sys, "stdout", SlowOutput()):
            code = probe.main(["--execute", "--output", str(output), "--source-sha256", "A" * 64])
        self.assertEqual(code, 9)
        events = [json.loads(line) for line in (output / "terminal.jsonl").read_text().splitlines()]
        self.assertEqual([row["returncode"] for row in events], [0, 9])

    def test_stale_pin_refuses_before_any_gpu_or_output(self):
        with patch.object(probe, "source_identity", return_value={"sha256": "A"*64}), \
             patch.object(probe, "gpu_snapshot", side_effect=AssertionError("GPU 금지")), \
             patch.object(sys, "stdout", StringIO()):
            code = probe.main(["--execute", "--source-sha256", "B"*64])
        self.assertEqual(code, 9)

    def test_parent_preserves_primary_and_source_recheck_error(self):
        output = self.directory / "new_parent"
        args = SimpleNamespace(output=output)
        with patch.object(probe, "gpu_snapshot", side_effect=OSError("원 입출력 오류")), \
             patch.object(probe, "source_identity", return_value={"sha256": "B" * 64}):
            code = probe.parent(args, budget(), {"sha256": "A" * 64})
        self.assertEqual(code, 9)
        result = probe.read_json(output / "report.json")
        self.assertEqual(result["original_error"]["type"], "OSError")
        self.assertEqual(result["cleanup_errors"][0]["stage"], "부모 소스 재검산")

    def test_parent_write_failure_carries_original_error(self):
        output = self.directory / "write_failure"
        original = probe.timed_write
        def write(path, value, active):
            if Path(path).name == "report.json":
                raise OSError("후행 저장 오류")
            return original(path, value, active)
        with patch.object(probe, "gpu_snapshot", side_effect=RuntimeError("원 오류")), \
             patch.object(probe, "source_identity", return_value={"sha256": "A" * 64}), \
             patch.object(probe, "timed_write", side_effect=write):
            with self.assertRaises(OSError) as caught:
                probe.parent(SimpleNamespace(output=output), budget(), {"sha256": "A" * 64})
        self.assertEqual(caught.exception.capacity_original_error["type"], "RuntimeError")

    @contextmanager
    def mocked_worker(self, *, transport_error=None, stale=False):
        from scripts import p106b_gemma_teacher as gemma
        from scripts import diag_p106b_mtp_teacher as lifecycle
        from scripts import p106b_memory_stream as memory_module
        from scripts import p106b_gemma_telemetry_resume as telemetry
        class Process:
            code = None
            def poll(self):
                return self.code
        class Session(lifecycle.Session):
            def __init__(self):
                self.process, self.workers, self.key = Process(), [], "SECRET"
            def check(self):
                pass
            def memory(self):
                return dict(sample_count=1, sampled_gpu_global_peak_mib=8771,
                    sampled_gpu_min_free_mib=4096, baseline_gpu_used_mib=500,
                    owned_server_peak_rss_mib=6500)
        class Gemma:
            def __init__(self, mtp):
                self.session = Session()
                if mtp is not True:
                    raise AssertionError("MTP 조건이 달라졌다")
            def __enter__(self):
                return self.session
            def __exit__(self, *_):
                self.session.process.code = -signal.SIGTERM
        class Memory:
            def __init__(self):
                self.process, self.worker = None, None
            def __enter__(self):
                self.process = Process()
                return self
            def __exit__(self, *_):
                self.process.code = -signal.SIGTERM
            def snapshot(self):
                return dict(received_frames=1, continuous_peak_verified=False)
        @contextmanager
        def stream(_):
            yield
        def transport(session, route, payload=None, timeout=10):
            if route == "/apply-template":
                return dict(prompt="synthetic")
            if route == "/tokenize":
                return dict(tokens=[1, 2])
            if transport_error:
                raise transport_error
            return reply()
        parent_pid = os.getppid()
        parent_stat = sup.proc.proc_stat(parent_pid)
        probe.timed_write(self.directory / "invocation.json", dict(parent_pid=parent_pid,
            parent_starttime=parent_stat["starttime"], source_sha256="A" * 64), budget())
        with patch.object(gemma, "GemmaSession", Gemma), patch.object(gemma, "assets", return_value={}), \
             patch.object(lifecycle.Session, "request", transport), \
             patch.object(memory_module, "PersistentMemory", Memory), \
             patch.object(memory_module, "stream_session_scope", stream), \
             patch.object(telemetry, "RetryingMemoryReader", side_effect=lambda memory, **_: memory), \
             patch.object(probe, "gpu_snapshot", return_value=dict(used_mib=500, free_mib=20000, compute_apps=[])), \
             patch.object(probe, "source_identity", return_value={"sha256": ("B" if stale else "A") * 64}), \
             patch.dict(os.environ, {sup.OWNER_KEY: "a" * 64}):
            yield

    def test_mocked_worker_four_requests_raw_metrics_and_normal_cleanup(self):
        with self.mocked_worker():
            code = probe.worker(SimpleNamespace(output=self.directory), budget(120, 20), {"sha256": "A" * 64})
        result = probe.read_json(self.directory / "worker.json")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["generation_attempts"], 4)
        self.assertEqual(len(result["prompt_observations"]), 4)
        self.assertEqual(len(result["request_metrics"]), 4)
        self.assertEqual(result["cleanup_errors"], [])

    def test_mocked_worker_primary_failure_survives_stale_source(self):
        with self.mocked_worker(transport_error=OSError("원 요청 오류"), stale=True):
            code = probe.worker(SimpleNamespace(output=self.directory), budget(120, 20), {"sha256": "A" * 64})
        result = probe.read_json(self.directory / "worker.json")
        self.assertEqual(code, 9)
        self.assertEqual(result["original_error"]["type"], "OSError")
        self.assertEqual(result["cleanup_errors"][-1]["stage"], "자식 소스 재검산")

    def test_deadline_and_window_validation(self):
        with patch.object(sys, "stdout", StringIO()):
            for args in (["--check-only", "--max-wall-sec", "601"],
                         ["--check-only", "--deadline", "2026-10-26T17:01:00+09:00"],
                         ["--check-only", "--deadline", "2026-10-26T08:00:00"]):
                with self.subTest(args=args):
                    self.assertEqual(probe.main(args), 9)

    def test_check_only_fresh_isolated_process_has_no_torch_or_writes(self):
        before = set(self.directory.iterdir())
        result = REAL_RUN([sys.executable, "-I", "-B", "-X", "utf8", str(ENTRY), "--check-only"],
                          cwd=self.directory, env=dict(os.environ, CUDA_VISIBLE_DEVICES=""),
                          capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertFalse(value["torch_imported"])
        self.assertEqual((value["gpu_queries"], value["files_written"]), (0, 0))
        self.assertEqual(set(self.directory.iterdir()), before)
        self.assertGreater(value["code_files"], len(probe.SEEDS))

    def test_real_cpu_controller_natural_exit(self):
        active = budget(5, .8)
        command = [sys.executable, "-B", "-c", "import time; time.sleep(.2)"]
        executables = dict(producer=sys.executable, teacher=sys.executable, memory="/bin/sleep")
        result = sup.supervise_process(command, self.directory, self.directory / "STOP",
                                       executables, active, factory=cpu_popen)
        self.assertTrue(probe.supervision_ok(result), result)
        self.assertFalse(sup.group_alive(result["controller_identity"]["pgid"]))

    def test_real_cpu_leader_first_and_term_ignoring_session_is_veto(self):
        code = (
            "import subprocess,sys,time; "
            "subprocess.Popen([sys.executable,'-B','-c',"
            "'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)'],"
            "start_new_session=True); time.sleep(.25)"
        )
        result = sup.supervise_process([sys.executable, "-B", "-c", code], self.directory,
                 self.directory / "STOP", dict(producer=sys.executable, teacher=sys.executable,
                 memory="/bin/sleep"), budget(6, 1), factory=cpu_popen)
        self.assertEqual(result["actual_producer_exit"], 0)
        self.assertTrue(result["forced_cleanup"])
        self.assertFalse(probe.supervision_ok(result))
        self.assertTrue(result["controller_group_quiescent"])
        self.assertTrue(result["owned_session_cleanup"])
        self.assertTrue(any("SIGKILL" in row["signals"] for row in result["owned_session_cleanup"]))
        for row in result["owned_sessions"]:
            self.assertFalse(sup.group_alive(row["pgid"]))


if __name__ == "__main__":
    unittest.main()

