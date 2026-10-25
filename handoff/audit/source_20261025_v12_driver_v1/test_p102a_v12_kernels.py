"""모델·CUDA·파일 생성 없이 v12 관측기의 권한·시간·증거 경계를 검증한다."""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import types
import unittest
from unittest import mock

from scripts import diag_p102a_v12_kernels as driver


class Clock:
    def __init__(self):
        self.value = 100.
        self.base = datetime(2026, 10, 25, 0, tzinfo=timezone.utc)

    def now(self):
        return self.base + timedelta(seconds=self.value - 100.)

    def tick(self, value):
        self.value += value

    def guard(self, seconds=60):
        return driver.Guard(self.base + timedelta(seconds=300), seconds,
                            now=self.now, clock=lambda: self.value)


class MemoryFile:
    """지연을 모의하며 실제 파일은 만들지 않는다."""
    def __init__(self, value=b"", *, clock=None, write_delay=0., read_delay=0.):
        self.value, self.present = value, bool(value)
        self.clock, self.write_delay, self.read_delay = clock, write_delay, read_delay

    def exists(self):
        return self.present

    def stat(self):
        return types.SimpleNamespace(st_size=len(self.value))

    def open(self, mode="r", encoding=None):
        owner = self
        binary = "b" in mode
        writing = "x" in mode or "a" in mode
        if "x" in mode and self.present:
            raise FileExistsError("기존 파일")
        if writing:
            self.present = True
            initial = self.value if "a" in mode else b""
            base = io.BytesIO if binary else io.StringIO
            class Stream(base):
                def fileno(self):
                    return 12345

                def __exit__(self, *args):
                    value = self.getvalue()
                    owner.value = value if binary else value.encode()
                    if owner.clock:
                        owner.clock.tick(owner.write_delay)
                    self.close()
            stream = Stream(initial if binary else initial.decode())
            stream.seek(0, io.SEEK_END)
            return stream
        if self.clock:
            self.clock.tick(self.read_delay)
        return io.BytesIO(self.value) if binary else io.StringIO(self.value.decode())


def arguments(**changes):
    value = dict(tag=driver.PREFIX + "cpu_mock", source_sha256="A" * 64,
                 original_zip_sha256=driver.ZIP_SHA, warmup=1, measure=2,
                 deadline="2026-10-25T03:00:00+00:00", max_wall_sec=60,
                 expand=False, _worker=False, _started="100")
    value.update(changes)
    return argparse.Namespace(**value)


def observed_report(expand=False):
    masses = [32, 8192] if expand else [32]
    return dict(status="OBSERVATION_COMPLETE_NOT_ADOPTED", intended_exit=0,
        quality_claim=False, adopted=False,
        observations=dict(canary_complete=True, expansion_requested=expand,
            expansion_completed=expand,
            cases=[dict(M=m, K=k, N=n, complete=True) for m in masses for k, n in driver.SHAPES],
            producers=[dict(M=m, complete=True) for m in masses]))


class TestGuard(unittest.TestCase):
    def test_aware_offsets_are_normalized(self):
        self.assertEqual(driver.aware("2026-10-25T12:00:00+09:00"),
                         datetime(2026, 10, 25, 3, tzinfo=timezone.utc))

    def test_naive_time_is_rejected(self):
        with self.assertRaises(ValueError):
            driver.aware("2026-10-25T12:00:00")

    def test_budget_bounds(self):
        for seconds in (59, 901):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                Clock().guard(seconds)

    def test_absolute_deadline_and_hard_stop(self):
        clock = Clock()
        for deadline in (clock.now(), driver.HARD_STOP + timedelta(seconds=1)):
            with self.subTest(deadline=deadline), self.assertRaises(ValueError):
                driver.Guard(deadline, 60, now=clock.now, clock=lambda: clock.value)

    def test_import_and_preparation_are_charged(self):
        clock = Clock()
        with self.assertRaises(TimeoutError):
            driver.Guard(clock.base + timedelta(seconds=300), 60, started=39.,
                         now=clock.now, clock=lambda: clock.value)

    def test_delayed_write_cannot_publish_success(self):
        clock = Clock()
        path = MemoryFile(clock=clock, write_delay=61.)
        with mock.patch.object(driver.os, "fsync"), self.assertRaises(TimeoutError):
            driver.write_new(path, {"nominal": 0}, clock.guard())
        self.assertTrue(path.exists())

    def test_delayed_readback_is_charged(self):
        clock = Clock()
        path = MemoryFile(clock=clock, read_delay=61.)
        with mock.patch.object(driver.os, "fsync"), self.assertRaises(TimeoutError):
            driver.write_new(path, {"nominal": 0}, clock.guard())

    def test_delayed_stdout_is_charged(self):
        clock = Clock()
        class Slow(io.StringIO):
            def flush(self):
                clock.tick(61.)
        with self.assertRaises(TimeoutError):
            driver.emit({"nominal": 0}, clock.guard(), Slow())

    def test_reserved_publication_time_is_enforced(self):
        clock = Clock()
        guard = driver.Guard(clock.base + timedelta(seconds=300), 60, now=clock.now,
                             clock=lambda: clock.value, reserve=15.)
        clock.tick(46.)
        with self.assertRaises(TimeoutError):
            guard.check("계산 종료")


class TestPublication(unittest.TestCase):
    def test_new_json_roundtrip_and_no_overwrite(self):
        path, guard = MemoryFile(), Clock().guard()
        with mock.patch.object(driver.os, "fsync"):
            driver.write_new(path, {"값": [1, 2]}, guard)
            with self.assertRaises(FileExistsError):
                driver.write_new(path, {"값": [3]}, guard)
        self.assertEqual(json.loads(path.value), {"값": [1, 2]})

    def test_nonfinite_json_is_rejected(self):
        with self.assertRaises(ValueError):
            driver.write_new(MemoryFile(), {"bad": float("nan")}, Clock().guard())

    def test_size_cap_precedes_write(self):
        path = MemoryFile()
        with mock.patch.object(driver, "MAX_FILE", 16), self.assertRaises(ValueError):
            driver.write_new(path, {"too_large": "x" * 30}, Clock().guard())
        self.assertFalse(path.exists())

    def test_terminal_veto_is_append_only(self):
        path = MemoryFile()
        with mock.patch.object(driver.os, "fsync"):
            driver.append_terminal(path, {"event": "FINAL_DISPOSITION", "intended_supervisor_exit": 0})
            first = path.value
            driver.append_terminal(path, {"event": "TERMINAL_VETO", "intended_supervisor_exit": 9})
        self.assertTrue(path.value.startswith(first))
        self.assertEqual([json.loads(line)["intended_supervisor_exit"] for line in path.value.splitlines()], [0, 9])

    def test_success_stdout_delay_gets_terminal_veto(self):
        clock = Clock()
        terminal = MemoryFile()
        def slow(*args):
            clock.tick(61.)
            args[1].check("지연된 최종 출력")
        with mock.patch.object(driver, "emit", side_effect=slow), mock.patch.object(driver.os, "fsync"):
            code = driver.finalize_disposition(terminal,
                dict(intended_supervisor_exit=0, actual_worker_exit=0), clock.guard())
        self.assertEqual(code, 9)
        self.assertEqual(json.loads(terminal.value)["event"], "TERMINAL_VETO")

    def test_final_disposition_write_delay_gets_later_veto(self):
        clock = Clock()
        terminal = MemoryFile(clock=clock, write_delay=61.)
        with mock.patch.object(driver, "emit"), mock.patch.object(driver.os, "fsync"):
            code = driver.finalize_disposition(terminal,
                dict(intended_supervisor_exit=0, actual_worker_exit=0), clock.guard())
        self.assertEqual(code, 9)
        rows = [json.loads(line) for line in terminal.value.splitlines()]
        self.assertEqual([row["event"] for row in rows], ["FINAL_DISPOSITION", "TERMINAL_VETO"])

    def test_nominal_report_cannot_hide_actual_exit(self):
        self.assertEqual(driver.decide(observed_report(), 9), 9)
        self.assertEqual(driver.decide(observed_report(), -9), 9)
        self.assertEqual(driver.decide(observed_report(), None), 9)

    def test_complete_observation_is_not_adoption(self):
        self.assertEqual(driver.decide(observed_report(), 0), 0)
        report = observed_report()
        report["adopted"] = True
        self.assertEqual(driver.decide(report, 0), 9)

    def test_incomplete_canary_is_not_success(self):
        report = observed_report()
        report["observations"]["cases"].pop()
        self.assertEqual(driver.decide(report, 0), 9)

    def test_partial_expansion_is_not_success(self):
        report = observed_report(True)
        report["observations"]["expansion_completed"] = False
        self.assertEqual(driver.decide(report, 0), 9)

    def test_wrong_geometry_is_not_success(self):
        report = observed_report()
        report["observations"]["cases"][0]["K"] = 64
        self.assertEqual(driver.decide(report, 0), 9)

    def test_missing_producer_is_not_success(self):
        report = observed_report()
        report["observations"]["producers"][0]["complete"] = False
        self.assertEqual(driver.decide(report, 0), 9)

    def test_partial_kernel_observations_survive_later_failure(self):
        result = {}
        def failed(torch, mods, m, k, n, args, guard, item):
            item.update(M=m, K=k, N=n, complete=False, phases={"native_forward_before": {"seen": True}})
            raise ArithmeticError("모의 원 커널 실패")
        with mock.patch.object(driver, "case", side_effect=failed), self.assertRaises(ArithmeticError):
            driver.observations(None, {}, arguments(), Clock().guard(), result)
        self.assertTrue(result["cases"][0]["phases"]["native_forward_before"]["seen"])
        self.assertFalse(result["cases"][0]["complete"])


class TestSources(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self):
        files = {name: MemoryFile((name + "=original").encode()) for name in driver.RUNTIME}
        zip_bytes, manifest = MemoryFile(b"fixed zip"), MemoryFile(b"fixed manifest")
        own = {name: MemoryFile((name + "=original").encode()) for name in (*driver.OWN, *driver.SUPERVISION)}
        entries = {"prototype/" + name: file.value for name, file in files.items()}
        def safe(path):
            if path == driver.ORIGINAL:
                return zip_bytes
            if path == driver.ARCHIVE / "v12_manifest.json":
                return manifest
            if path.name in files:
                return files[path.name]
            for name, file in own.items():
                if path == driver.ROOT / name:
                    return file
            raise AssertionError("범위 밖 읽기")
        packed = mock.MagicMock()
        packed.namelist.return_value = list(entries)
        packed.read.side_effect = entries.__getitem__
        with mock.patch.object(driver, "safe_file", side_effect=safe), \
             mock.patch.object(driver, "ZIP_SHA", hashlib.sha256(zip_bytes.value).hexdigest().upper()), \
             mock.patch.object(driver, "MANIFEST_SHA", hashlib.sha256(manifest.value).hexdigest().upper()), \
             mock.patch.object(driver.zipfile, "ZipFile") as constructor:
            constructor.return_value.__enter__.return_value = packed
            yield files, own, zip_bytes, packed

    def test_pinned_sources_match_zip_bytes(self):
        with self.fixture():
            receipt = driver.source_receipt()
            self.assertEqual(len(receipt["runtime_source_sha256"]), 7)
            driver.assert_receipt(receipt, receipt["source_sha256"])

    def test_same_length_dependency_bytes_changed(self):
        with self.fixture() as (files, _, _, _):
            original = files["v12_kernels.py"].value
            files["v12_kernels.py"].value = original.replace(b"original", b"modified")
            self.assertEqual(len(files["v12_kernels.py"].value), len(original))
            with self.assertRaises(ValueError):
                driver.source_receipt()

    def test_same_length_driver_bytes_change_source_signature(self):
        with self.fixture() as (_, own, _, _):
            before = driver.source_receipt()
            path = own[driver.OWN[0]]
            path.value = path.value.replace(b"original", b"modified")
            after = driver.source_receipt()
            with self.assertRaises(ValueError):
                driver.assert_receipt(after, before["source_sha256"])

    def test_changed_original_zip_is_rejected(self):
        with self.fixture() as (_, _, zipped, _):
            zipped.value = b"other zip"
            with self.assertRaises(ValueError):
                driver.source_receipt()

    def test_duplicate_zip_members_are_rejected(self):
        with self.fixture() as (_, _, _, packed):
            packed.namelist.return_value += ["other/v12_kernels.py"]
            with self.assertRaises(ValueError):
                driver.source_receipt()

    def test_check_only_fresh_process_imports_no_torch_or_cuda(self):
        command = [sys.executable, "-B", "-X", "utf8", str(Path(driver.__file__).resolve()), "--check-only"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["torch_imported"])
        self.assertFalse(report["cuda_executed"])
        self.assertEqual(report["files_written"], 0)


class TestAdmission(unittest.TestCase):
    def test_bad_tags_and_hashes_are_rejected(self):
        for changes in ({"tag": "dense"}, {"tag": driver.PREFIX + "../x"},
                        {"source_sha256": "short"}, {"original_zip_sha256": "B" * 64}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                driver.validate_args(arguments(**changes))

    def test_interpreter_cannot_replace_cuda(self):
        with mock.patch.dict(os.environ, {"TRITON_INTERPRET": "1"}), self.assertRaises(ValueError):
            driver.validate_args(arguments())

    def test_foreign_gpu_process_is_rejected(self):
        response = types.SimpleNamespace(returncode=0, stdout="987654\n", stderr="")
        with mock.patch.object(driver.subprocess, "run", return_value=response), self.assertRaises(driver.Incomplete):
            driver.admission(Clock().guard())

    def test_empty_gpu_process_list_is_allowed(self):
        response = types.SimpleNamespace(returncode=0, stdout="", stderr="")
        with mock.patch.object(driver.subprocess, "run", return_value=response):
            self.assertEqual(driver.admission(Clock().guard())["foreign_compute_pids"], [])

    def test_unknown_admission_output_is_incomplete(self):
        response = types.SimpleNamespace(returncode=0, stdout="N/A\n", stderr="")
        with mock.patch.object(driver.subprocess, "run", return_value=response), self.assertRaises(driver.Incomplete):
            driver.admission(Clock().guard())

    def test_gpu_query_delay_is_charged(self):
        clock = Clock()
        response = types.SimpleNamespace(returncode=0, stdout="", stderr="")
        def slow(*args, **kwargs):
            clock.tick(61.)
            return response
        with mock.patch.object(driver.subprocess, "run", side_effect=slow), self.assertRaises(TimeoutError):
            driver.admission(clock.guard())

    def test_existing_namespace_is_rejected(self):
        with mock.patch.object(Path, "exists", return_value=True), self.assertRaises(FileExistsError):
            driver.target_path(driver.PREFIX + "occupied")

    def test_cuda_dispatch_rejects_cpu_only_runtime(self):
        fake = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
        with mock.patch.object(driver.importlib, "import_module", return_value=fake), self.assertRaises(driver.Incomplete):
            driver.import_runtime(Clock().guard())

    def test_cuda_dispatch_rejects_other_architecture(self):
        fake = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: True,
                                                               get_device_capability=lambda: (9, 0)))
        with mock.patch.object(driver.importlib, "import_module", return_value=fake), self.assertRaises(driver.Incomplete):
            driver.import_runtime(Clock().guard())

    def test_unsupervised_worker_is_rejected(self):
        with mock.patch.dict(os.environ, {"TINYLM_V12_KERNEL_WORKER": "-1"}), self.assertRaises(ValueError):
            driver.worker(arguments())

    def test_os_wait_includes_worker_delay(self):
        clock = Clock()
        tools = driver.process_tools()
        process = mock.Mock(pid=987654, returncode=None)
        process.poll.side_effect = lambda: process.returncode
        def delay(**kwargs):
            clock.tick(53.)
            raise subprocess.TimeoutExpired("모의 worker", .25)
        process.wait.side_effect = delay
        def stop(*args):
            process.returncode = -9
            return ["GROUP_QUIESCENT"]
        with mock.patch.object(tools, "stop_process_group", side_effect=stop):
            result = driver.run_owned_worker(["모의"], {}, MemoryFile(), clock.guard(),
                                             factory=lambda *a, **k: process, tools=tools)
        self.assertEqual(result["status"], "TIMED_OUT")
        self.assertEqual(result["returncode"], -9)

    def test_os_wait_rejects_oversized_worker_log(self):
        path = mock.Mock()
        path.stat.return_value = types.SimpleNamespace(st_size=driver.MAX_FILE)
        factory = mock.Mock(side_effect=AssertionError("이름공간 입장 전 child 금지"))
        result = driver.run_owned_worker(["모의"], {}, path, Clock().guard(), factory=factory)
        self.assertEqual(result["status"], "TOOL_ERROR")
        self.assertFalse(result["process_started"])
        factory.assert_not_called()

    def test_os_wait_returns_actual_child_exit(self):
        tools = driver.process_tools()
        process = mock.Mock(pid=987654, returncode=9)
        process.poll.return_value = 9
        process.wait.return_value = 9
        with mock.patch.object(tools, "stop_process_group", return_value=["GROUP_QUIESCENT"]):
            result = driver.run_owned_worker(["모의"], {}, MemoryFile(), Clock().guard(),
                                             factory=lambda *a, **k: process, tools=tools)
        self.assertEqual(result["returncode"], 9)

    def test_exited_zero_leader_with_live_group_is_cleaned_and_vetoed(self):
        tools = driver.process_tools()
        process = mock.Mock(pid=987654, returncode=0)
        process.poll.return_value = 0
        process.wait.return_value = 0
        with mock.patch.object(tools, "owned_group_alive", return_value=True), \
             mock.patch.object(tools, "stop_process_group", return_value=["SIGKILL_PROCESS_GROUP", "GROUP_QUIESCENT"]) as stop:
            result = driver.run_owned_worker(["모의"], {}, MemoryFile(), Clock().guard(),
                                             factory=lambda *a, **k: process, tools=tools)
        stop.assert_called_once()
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["status"], "TOOL_ERROR")
        self.assertIn("GROUP_QUIESCENT", result["termination"])

    def test_cleanup_error_preserves_original_failure_and_actual_exit(self):
        tools = driver.process_tools()
        process = mock.Mock(pid=987654, returncode=0)
        process.poll.return_value = 0
        process.wait.return_value = 0
        with mock.patch.object(tools, "owned_group_alive", return_value=True), \
             mock.patch.object(tools, "stop_process_group", side_effect=OSError("모의 cleanup 오류")):
            result = driver.run_owned_worker(["모의"], {}, MemoryFile(), Clock().guard(),
                                             factory=lambda *a, **k: process, tools=tools)
        self.assertEqual(result["returncode"], 0)
        self.assertIn("surviving owned group", result["error"])
        self.assertTrue(result["unsafe_process_state"])
        self.assertIn("CLEANUP_ERROR:OSError", result["termination"])

    def test_adapter_cleanup_error_keeps_prior_receipt(self):
        previous = driver.signal.getsignal(driver.signal.SIGTERM)
        state = {}
        def child(*args, **kwargs):
            kwargs["state_sink"].update(returncode=0, status="TOOL_ERROR", error="최초 오류")
            return kwargs["state_sink"]
        tools = types.SimpleNamespace(run_child=child)
        def signals(sig, handler):
            if handler is previous:
                raise OSError("모의 handler 복구 오류")
        with mock.patch.object(driver.signal, "signal", side_effect=signals):
            driver.run_owned_worker(["모의"], {}, MemoryFile(), Clock().guard(), tools=tools, state=state)
        self.assertEqual(state["returncode"], 0)
        self.assertEqual(state["error"], "최초 오류")
        self.assertTrue(state["unsafe_process_state"])
        self.assertEqual(state["adapter_cleanup_error"]["exception_class"], "OSError")

    def test_os_file_limit_is_below_twenty_megabytes(self):
        library = mock.Mock()
        library.prctl.return_value = 0
        with mock.patch.object(driver.resource, "setrlimit") as setter, \
             mock.patch.object(driver.ctypes, "CDLL", return_value=library):
            driver.worker_limits(os.getppid())
        setter.assert_called_once_with(driver.resource.RLIMIT_FSIZE,
                                       (driver.MAX_FILE - 1, driver.MAX_FILE - 1))
        library.prctl.assert_called_once_with(1, driver.signal.SIGKILL, 0, 0, 0)

    def test_parent_death_race_cannot_leave_a_gpu_worker(self):
        library = mock.Mock()
        library.prctl.return_value = 0
        with mock.patch.object(driver.resource, "setrlimit"), \
             mock.patch.object(driver.ctypes, "CDLL", return_value=library), \
             mock.patch.object(driver.os, "kill") as kill:
            driver.worker_limits(-1)
        kill.assert_called_once_with(os.getpid(), driver.signal.SIGKILL)

    def test_failed_parent_death_setup_is_not_ignored(self):
        library = mock.Mock()
        library.prctl.return_value = -1
        with mock.patch.object(driver.resource, "setrlimit"), \
             mock.patch.object(driver.ctypes, "CDLL", return_value=library), self.assertRaises(OSError):
            driver.worker_limits(os.getppid())

    def fake_cuda(self):
        event = types.SimpleNamespace(record=lambda: None, elapsed_time=lambda other: 2.)
        cuda = types.SimpleNamespace(synchronize=lambda: None, memory_allocated=lambda: 123,
            memory_reserved=lambda: 256, reset_peak_memory_stats=lambda: None,
            max_memory_allocated=lambda: 200, max_memory_reserved=lambda: 300,
            Event=lambda **kwargs: event)
        return types.SimpleNamespace(cuda=cuda)

    def test_mock_timing_keeps_first_warmup_and_measured_separate(self):
        clock = Clock()
        def call():
            clock.tick(.01)
            return "모의 결과"
        with mock.patch.object(driver.time, "perf_counter", side_effect=lambda: clock.value):
            value, receipt = driver.measure(self.fake_cuda(), call, clock.guard(), warmup=1, rounds=2)
        self.assertEqual(value, "모의 결과")
        self.assertEqual([r["phase"] for r in receipt["samples"]],
                         ["first_call_compile_autotune", "warmup", "measured", "measured"])
        self.assertTrue(all(r["peak_allocated_absolute"] == 200 for r in receipt["samples"]))

    def test_mock_kernel_delay_cannot_escape_overall_budget(self):
        clock = Clock()
        def call():
            clock.tick(61.)
        with self.assertRaises(TimeoutError):
            driver.measure(self.fake_cuda(), call, clock.guard(), warmup=1, rounds=2)

    def test_missing_chosen_autotune_tile_is_incomplete(self):
        with self.assertRaises(driver.Incomplete):
            driver.chosen(types.SimpleNamespace())


@unittest.skipUnless(sys.platform.startswith("linux"), "Linux 소유 그룹 실제 CPU 검사")
class TestOwnedProcessIntegration(unittest.TestCase):
    def test_real_cpu_descendant_is_removed_after_zero_leader_exits(self):
        # 고아 자손의 좀비까지 이 검사 프로세스가 회수하고 원 subreaper 설정을 복구한다.
        libc = driver.ctypes.CDLL(None, use_errno=True)
        previous = driver.ctypes.c_int()
        if libc.prctl(37, driver.ctypes.byref(previous), 0, 0, 0) != 0:
            self.fail("원 subreaper 설정 조회 실패")
        if libc.prctl(36, 1, 0, 0, 0) != 0:
            self.fail("CPU 검사 자손 회수 설정 실패")
        source = """import os, signal, time
r, w = os.pipe()
pid = os.fork()
if pid == 0:
    os.close(r)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    os.write(w, b'ready')
    os.close(w)
    os.close(1)
    os.close(2)
    time.sleep(30)
    os._exit(0)
os.close(w)
os.read(r, 5)
os.close(r)
print(pid, flush=True)
os._exit(0)
"""
        state = {}
        started = time.monotonic()
        base = datetime(2026, 10, 25, 0, tzinfo=timezone.utc)
        guard = driver.Guard(base + timedelta(seconds=15), 60, started=started,
            clock=time.monotonic, now=lambda: base + timedelta(seconds=time.monotonic() - started))
        threads, processes = [], []
        def factory(argv, **options):
            process = subprocess.Popen(argv, **options, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            processes.append(process)
            def reap():
                try:
                    pid = int(process.stdout.readline().strip())
                    state["descendant_pid"] = pid
                    until = time.monotonic() + 8.
                    while time.monotonic() < until:
                        try:
                            done, status = os.waitpid(pid, os.WNOHANG)
                            if done == pid:
                                state.update(reaped=True, descendant_status=status)
                                return
                        except ChildProcessError:
                            pass
                        time.sleep(.005)
                    state["reap_timeout"] = True
                except BaseException as error:
                    state["reap_error"] = repr(error)
            thread = threading.Thread(target=reap, daemon=True)
            threads.append(thread)
            thread.start()
            return process
        tools = driver.process_tools()
        try:
            receipt = driver.run_owned_worker([sys.executable, "-B", "-c", source],
                dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONDONTWRITEBYTECODE="1"),
                MemoryFile(), guard, factory=factory, tools=tools)
            for thread in threads:
                thread.join(2.)
            self.assertEqual(receipt["returncode"], 0)
            self.assertEqual(receipt["status"], "TOOL_ERROR")
            self.assertIn("surviving owned group", receipt["error"])
            self.assertIn("SIGKILL_PROCESS_GROUP", receipt["termination"])
            self.assertIn("GROUP_QUIESCENT", receipt["termination"])
            self.assertFalse(receipt["unsafe_process_state"])
            self.assertTrue(state.get("reaped"), state)
            self.assertTrue(os.WIFSIGNALED(state["descendant_status"]))
            self.assertEqual(os.WTERMSIG(state["descendant_status"]), driver.signal.SIGKILL)
            self.assertEqual(tools._OWNED_GROUPS, {})
        finally:
            for process in processes:
                if process.poll() is None or not state.get("reaped"):
                    try:
                        tools._register_owned(process, start_new_session=True)
                        tools.stop_process_group(process, time.monotonic() + 3., time.monotonic)
                    finally:
                        tools._forget_owned(process)
                process.wait(timeout=2.)
            for thread in threads:
                thread.join(2.)
            for process in processes:
                process.stdout.close()
                process.stderr.close()
            if libc.prctl(36, previous.value, 0, 0, 0) != 0:
                self.fail("원 subreaper 설정 복구 실패")


class TestCpuTensors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        driver.source_receipt()
        import torch
        cls.torch = torch
        sys.path.insert(0, str(driver.ARCHIVE))
        cls.core = __import__("v12_code_reuse")
        torch.set_num_threads(2)

    def test_original_g128_ternary_pack_and_alias(self):
        t = self.torch
        codes = t.tensor([-1, 0, 1, 0] * 32).repeat(2, 2)
        weight = codes.float() * .03125
        packed = self.core.pack_cpu(weight, t.bfloat16, 128, 2, True, True)
        restored = (packed.high.reshape(2, 2, 128).float() * packed.sh[:, :, None]).reshape(2, 256)
        self.assertTrue(t.equal(restored, weight.bfloat16().float()))
        self.assertEqual(packed.rows.codes.untyped_storage().data_ptr(), packed.columns.codes.untyped_storage().data_ptr())

    def test_original_high_low_boundary_uses_negative_128(self):
        t = self.torch
        value = t.zeros((1, 128), dtype=t.bfloat16)
        value[0, 0], value[0, 1], value[0, 2] = 127., .5, -.5
        packed = self.core.pack_cpu(value, t.bfloat16, 128, 2, binary=True)
        self.assertEqual(float(packed.sh[0, 0]), 1.)
        self.assertEqual(int(packed.low[0, 1]), -128)
        self.assertEqual(int(packed.low[0, 2]), -128)

    def test_original_cpu_adjoint_strided_matches_copied(self):
        t = self.torch
        generator = t.Generator().manual_seed(1337)
        rows = self.core.quantize_rows(t.randn((8, 128), generator=generator))
        right = t.randint(-127, 128, (128, 16), generator=generator, dtype=t.int8).T
        a = self.core.gradient_cpu(rows, right, t.bfloat16, t.float32)
        b = self.core.gradient_cpu(rows, right.contiguous(), t.bfloat16, t.float32)
        self.assertTrue(t.equal(a, b))

    def test_int32_reduction_bound_precedes_matmul(self):
        t = self.torch
        limit = self.core.INT32_K_LIMIT
        rows = self.core.Rows(t.zeros((1, limit + 1), dtype=t.int8), t.ones(1))
        with self.assertRaises(OverflowError):
            self.core.gradient_cpu(rows, t.zeros((1, limit + 1), dtype=t.int8), t.bfloat16, t.float32)

    def test_native_difference_is_reported_without_acceptance_threshold(self):
        t = self.torch
        report = driver.approximation(t, t.tensor([1., 2.]), t.tensor([1., 1.]))
        self.assertGreater(report["relative_l2"], .05)
        self.assertIsNone(report["acceptance_threshold"])
        self.assertFalse(report["quality_claim"])

    def test_nonfinite_cannot_be_a_numeric_observation(self):
        t = self.torch
        with self.assertRaises(FloatingPointError):
            driver.approximation(t, t.tensor([float("inf")]), t.ones(1))

    def test_dtype_and_rounding_mismatch_is_not_exact(self):
        t = self.torch
        with self.assertRaises(ArithmeticError):
            driver.exact(t, t.ones(1, dtype=t.bfloat16), t.ones(1), "모의 dtype")
        with self.assertRaises(ArithmeticError):
            driver.exact(t, t.tensor([1.]), t.tensor([1.001]), "모의 반올림")

    def test_implementation_mismatch_preserves_actual_numeric_detail(self):
        t = self.torch
        with self.assertRaises(driver.NumericMismatch) as caught:
            driver.exact(t, t.tensor([1., 2.]), t.tensor([1., 1.]), "모의 원식")
        self.assertEqual(caught.exception.detail["differing_elements"], 1)
        self.assertEqual(caught.exception.detail["max_abs"], 1.)

    def test_original_nonternary_weight_is_rejected(self):
        t = self.torch
        weight = t.ones((2, 128)) * .03125
        weight[0, 0] = .0625
        with self.assertRaises(ValueError):
            self.core.pack_cpu(weight, t.bfloat16, 128, 2, True, True)

    def test_original_swiglu_cpu_vjp_matches_native(self):
        t = self.torch
        swiglu = __import__("v12_swiglu")
        generator = t.Generator().manual_seed(1337)
        g = t.randn((2, 256), generator=generator).bfloat16().requires_grad_()
        u = t.randn((2, 256), generator=generator).bfloat16().requires_grad_()
        dy = t.randn((2, 256), generator=generator).bfloat16()
        native = t.nn.functional.silu(g) * u
        expected = t.autograd.grad(native, (g, u), dy)
        actual = swiglu._SwiGLU.apply(g, u, "cpu_int8", 128)[0]
        gradients = t.autograd.grad(actual, (g, u), dy)
        self.assertTrue(t.equal(native, actual))
        self.assertTrue(all(t.equal(a, b) for a, b in zip(expected, gradients)))

    def test_original_cuda_kernel_refuses_cpu_without_fallback(self):
        t = self.torch
        kernels = __import__("v12_kernels")
        rows = self.core.quantize_rows(t.ones((8, 128)))
        with mock.patch.object(t.cuda, "get_device_capability", side_effect=AssertionError("CPU 검사에서 GPU 조회 금지")):
            with self.assertRaises(RuntimeError):
                kernels.gradient_gemm(rows, t.zeros((16, 128), dtype=t.int8), t.bfloat16, t.float32)

    def test_both_primitive_forward_arms_disable_graph_creation(self):
        t = self.torch
        value = t.ones(4, requires_grad=True)
        modes = []
        for callback in (lambda: t.nn.functional.silu(value) * value, lambda: value * value):
            def observe():
                modes.append(t.is_grad_enabled())
                return callback()
            result = driver.primitive_forward(t, observe)
            self.assertFalse(result.requires_grad)
        self.assertEqual(modes, [False, False])
        self.assertTrue(t.is_grad_enabled())


if __name__ == "__main__":
    unittest.main()
