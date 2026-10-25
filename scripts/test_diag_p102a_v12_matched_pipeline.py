"""새 companion의 CPU 계약·원식 연결·실제 자식 진입점을 검증한다. 모델과 CUDA 실행은 없다."""
from __future__ import annotations

import argparse
import builtins
import contextlib
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types
import unittest
from unittest import mock

PATH = Path(__file__).with_name("diag_p102a_v12_matched_pipeline.py").resolve()
SPEC = importlib.util.spec_from_file_location("_matched_cpu_driver", PATH)
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)


class Clock:
    def __init__(self):
        self.value = 100.
        self.start = datetime(2026, 10, 25, tzinfo=timezone.utc)

    def tick(self, seconds):
        self.value += seconds

    def guard(self, reserve=0):
        return driver.original().module.Guard(self.start + timedelta(minutes=5), 60,
            started=100., now=lambda: self.start + timedelta(seconds=self.value - 100.),
            clock=lambda: self.value, reserve=reserve)


class MemoryFile:
    """저장·재읽기·지연은 메모리로만 모의한다."""
    def __init__(self, value=b"", clock=None, write_delay=0., read_delay=0.):
        self.value = value
        self.clock, self.write_delay, self.read_delay = clock, write_delay, read_delay
        self.present = bool(value)

    def exists(self):
        return self.present

    def stat(self):
        return types.SimpleNamespace(st_size=len(self.value))

    def read_bytes(self):
        if self.clock:
            self.clock.tick(self.read_delay)
        return self.value

    def open(self, mode="r", encoding=None):
        owner = self
        binary = "b" in mode
        if "x" in mode and self.present:
            raise FileExistsError("기존 파일")
        if "x" in mode or "a" in mode:
            self.present = True
            initial = self.value if "a" in mode else b""
            parent = io.BytesIO if binary else io.StringIO

            class Stream(parent):
                def fileno(self):
                    return 12345

                def __exit__(self, *unused):
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
    fields = dict(tag=driver.PREFIX + "cpu_mock", deadline="2026-10-25T03:00:00+00:00",
                  max_wall_sec=870, warmup=2, measure=5, expand=False, source_sha256="A" * 64,
                  original_zip_sha256=driver.original().module.ZIP_SHA, _worker=False, _started="100")
    fields.update(changes)
    return argparse.Namespace(**fields)


def phase():
    return {"samples": [{"phase": kind, "synchronized_wall_ms": 1., "cuda_event_interval_ms": .5}
        for kind in ["first_call_compile_autotune"] + ["warmup"] * 2 + ["measured"] * 5]}


def exact():
    return {"bitwise_equal": True, "elements": 8, "dtype": "torch.bfloat16"}


def observed_report(expanded=False):
    masses = (32, 8192) if expanded else (32,)
    cases, producers = [], []
    for m in masses:
        for k, n in driver.original().module.SHAPES:
            checks = {name: [exact()] for name in (
                "native_before_after", "int_full_weight_pack_cold_reuse_exact", "hybrid_weight_pack_cold_reuse_exact",
                "hybrid_forward_native", "hybrid_gradients_original_int", "same_row_codes_and_scales")}
            if m == 32:
                checks["full_original_cpu_reference"] = [exact()]
            cases.append(dict(M=m, K=k, N=n, complete=True, full_cpu_reference=m == 32,
                              phases={name: phase() for name in driver.PIPELINE_PHASES}, implementation_checks=checks))
        producers.append(dict(M=m, complete=True, max_bf16_ulps=0, original_v12_local_ulp_limit=1,
            primitive_forward_grad_enabled=False, vjp_autograd_measured_separately=True,
            phases={name: phase() for name in driver.PRODUCER_PHASES},
            implementation_checks={name: [exact()] for name in
                ("native_before_after", "fused_pack_own_y_exact", "original_cpu_pack", "original_vjp_exact")}))
    return dict(status="OBSERVATION_COMPLETE_NOT_ADOPTED", intended_exit=0, quality_claim=False, adopted=False,
        model_created=False, checkpoint_reads=0, checkpoint_writes=0,
        observations=dict(companion_contract=driver.CONTRACT, cases=cases, producers=producers,
            canary_complete=True, expansion_requested=expanded, expansion_completed=expanded))


def prior_evidence():
    closure = dict(actual_root_exit=0, actual_worker_exit=0, source_sha256=driver.ORIGINAL_SOURCE_SHA,
                   source_receipt_unchanged=True, status="OBSERVATION_COMPLETE_NOT_ADOPTED",
                   quality_claim=False, adopted=False)
    report = dict(sources={"source_sha256": driver.ORIGINAL_SOURCE_SHA},
                  status="OBSERVATION_COMPLETE_NOT_ADOPTED", intended_exit=0,
                  quality_claim=False, adopted=False, model_created=False, checkpoint_reads=0, checkpoint_writes=0)
    events = [dict(event="WORKER_ACTUAL_EXIT", actual_worker_exit=0, intended_supervisor_exit=0, error=None),
              dict(event="FINAL_DISPOSITION", actual_worker_exit=0, intended_supervisor_exit=0)]
    return closure, report, events


class TestSourcesAndBootstrap(unittest.TestCase):
    def test_real_source_receipt_pins_original_zip_runtime_and_prior_closure(self):
        receipt = driver.source_receipt()
        self.assertEqual(receipt["original_sources"]["source_sha256"], driver.ORIGINAL_SOURCE_SHA)
        self.assertEqual(set(receipt["companion_source_sha256"]), set(driver.OWN))
        self.assertEqual(len(receipt["original_sources"]["runtime_source_sha256"]), 7)
        self.assertEqual(receipt["prior_evidence_sha256"], driver.EVIDENCE)

    def test_same_length_companion_bytes_make_old_identity_stale(self):
        owner = driver.original()
        before = driver.source_receipt(owner=owner)
        digest = owner.module.digest
        current = PATH.read_bytes()
        changed = current.replace(b"MAX_WALL = 870", b"MAX_WALL = 869", 1)
        self.assertNotEqual(current, changed)
        self.assertEqual(len(current), len(changed))
        with mock.patch.object(owner.module, "digest", side_effect=lambda path, guard=None:
                hashlib.sha256(changed).hexdigest().upper() if path == PATH else digest(path, guard)):
            after = driver.source_receipt(owner=owner)
        with self.assertRaises(ValueError):
            owner.module.assert_receipt(after, before["source_sha256"])

    def test_runtime_field_change_cannot_keep_old_aggregate_sha(self):
        owner = driver.original()
        receipt = owner.source_receipt()
        receipt["runtime_source_sha256"]["v12_kernels.py"] = "0" * 64
        with mock.patch.object(owner, "source_receipt", return_value=receipt), self.assertRaises(ValueError):
            driver.source_receipt(owner=owner)

    def test_delayed_prior_evidence_read_is_inside_same_budget(self):
        owner, clock = driver.original(), Clock()
        name = next(iter(driver.EVIDENCE))
        path = driver.ROOT / name
        delayed = MemoryFile(path.read_bytes(), clock=clock, read_delay=61.)
        safe = owner.module.safe_file
        with mock.patch.object(owner.module, "safe_file", side_effect=lambda value:
                delayed if value == path else safe(value)), self.assertRaises(TimeoutError):
            driver.source_receipt(clock.guard(), owner=owner)

    def test_original_driver_stale_is_rejected_before_cached_module_use(self):
        fake = mock.MagicMock()
        fake.is_symlink.return_value = False
        fake.resolve.return_value = fake
        fake.stat.return_value = types.SimpleNamespace(st_size=4)
        fake.read_bytes.return_value = b"edit"
        with mock.patch.object(driver, "ORIGINAL_DRIVER", fake), self.assertRaises(ValueError):
            driver.original()

    def test_prior_evidence_hash_drift_is_rejected(self):
        changed = dict(driver.EVIDENCE)
        changed[next(iter(changed))] = "0" * 64
        with mock.patch.object(driver, "EVIDENCE", changed), self.assertRaises(ValueError):
            driver.source_receipt()

    def test_prior_actual_exit_boolean_is_not_integer_zero(self):
        values = prior_evidence()
        values[0]["actual_root_exit"] = False
        with self.assertRaises(ValueError):
            driver.check_prior_evidence(*values)

    def test_prior_later_terminal_veto_is_not_hidden(self):
        values = prior_evidence()
        values[2].append(dict(event="TERMINAL_VETO", intended_supervisor_exit=9))
        with self.assertRaises(ValueError):
            driver.check_prior_evidence(*values)

    def test_prior_worker_failure_is_not_relabelled_complete(self):
        for change in ("error", "actual_worker_exit", "intended_supervisor_exit"):
            values = prior_evidence()
            values[2][0][change] = {"exception": "모의 원 오류"} if change == "error" else 9
            with self.subTest(change=change), self.assertRaises(ValueError):
                driver.check_prior_evidence(*values)

    def test_private_callbacks_restore_on_exception_without_public_module_patch(self):
        owner = driver.original()
        names = ("__file__", "STARTED", "PREFIX", "parser", "validate_args", "source_receipt",
                 "environment_metadata", "observations", "decide", "worker", "supervise",
                 "run_owned_worker", "worker_limits", "finalize_disposition")
        before = {name: getattr(owner.module, name) for name in names}
        public = types.SimpleNamespace(marker="다른 소유 모듈")
        with mock.patch.dict(sys.modules, {"scripts.diag_p102a_v12_kernels": public}):
            with self.assertRaisesRegex(RuntimeError, "모의 관측 오류"):
                with driver.linked(owner) as base:
                    self.assertEqual(base.__file__, str(PATH))
                    self.assertEqual(base.PREFIX, driver.PREFIX)
                    self.assertIs(base.worker, before["worker"])
                    self.assertIs(base.supervise, before["supervise"])
                    self.assertIs(base.run_owned_worker, before["run_owned_worker"])
                    self.assertIs(base.worker_limits, before["worker_limits"])
                    self.assertIs(base.finalize_disposition, before["finalize_disposition"])
                    raise RuntimeError("모의 관측 오류")
            self.assertIs(sys.modules["scripts.diag_p102a_v12_kernels"], public)
        self.assertTrue(all(getattr(owner.module, name) is value for name, value in before.items()))
        self.assertFalse(driver._LINK_ACTIVE)

    def test_nested_adapter_cannot_corrupt_restore_state(self):
        with driver.linked(), self.assertRaises(RuntimeError):
            with driver.linked():
                pass
        self.assertFalse(driver._LINK_ACTIVE)

    def test_fresh_isolated_check_only_bootstraps_companion_without_torch(self):
        result = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", str(PATH), "--check-only"],
            capture_output=True, text=True, timeout=30,
            env=dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertFalse(value["torch_imported"])
        self.assertFalse(value["cuda_executed"])
        self.assertEqual(value["files_written"], 0)
        self.assertEqual(value["sources"]["contract"], driver.CONTRACT)
        self.assertEqual(value["environment"]["bootstrap"]["entrypoint"], str(PATH))
        self.assertEqual(value["environment"]["bootstrap"]["observations_module"], "__main__")

    def test_fresh_direct_worker_is_actual_exit9_before_cuda(self):
        result = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", str(PATH), "--_worker",
            "--tag", driver.PREFIX + "cpu_unowned", "--deadline", "2026-10-25T04:00:00+00:00",
            "--source-sha256", "A" * 64, "--original-zip-sha256", driver.original().module.ZIP_SHA,
            "--_started", "100"], capture_output=True, text=True, timeout=30,
            env={key: value for key, value in dict(os.environ, CUDA_VISIBLE_DEVICES="").items()
                 if key != "TINYLM_V12_KERNEL_WORKER"})
        self.assertEqual(result.returncode, 9)
        self.assertIn("감독 프로세스를 거치지 않은 worker", result.stderr)


class TestContractAndPublication(unittest.TestCase):
    def test_main_final_publication_occurs_after_private_restore(self):
        owner, clock, terminal = driver.original(), Clock(), MemoryFile()

        def call_main(argv):
            guard = owner.module.Guard(clock.start + timedelta(minutes=5), 60, started=100.,
                now=lambda: clock.start + timedelta(seconds=clock.value - 100.), clock=lambda: clock.value)
            return owner.module.finalize_disposition(terminal,
                dict(intended_supervisor_exit=0, actual_worker_exit=0), guard)

        def output(value, guard):
            self.assertFalse(driver._LINK_ACTIVE)
            guard.check("모의 최종 출력")

        with mock.patch.object(owner.module, "main", side_effect=call_main), \
             mock.patch.object(owner.module, "emit", side_effect=output), \
             mock.patch.object(owner.module.os, "fsync"):
            self.assertEqual(driver.main(["--execute"]), 0)
        self.assertEqual(json.loads(terminal.value.splitlines()[-1])["event"], "FINAL_DISPOSITION")

    def test_delayed_private_restore_cannot_publish_success(self):
        for parent in (False, True):
            owner, clock, terminal = driver.original(), Clock(), MemoryFile()
            original_file = owner.module.__file__

            def call_main(argv):
                guard = owner.module.Guard(clock.start + timedelta(minutes=5), 60, started=100.,
                    now=lambda: clock.start + timedelta(seconds=clock.value - 100.), clock=lambda: clock.value)
                if parent:
                    return owner.module.finalize_disposition(terminal,
                        dict(intended_supervisor_exit=0, actual_worker_exit=0), guard)
                return 0

            def setter(obj, name, value):
                builtins.setattr(obj, name, value)
                if obj is owner.module and name == "__file__" and value == original_file:
                    clock.tick(61.)

            with mock.patch.object(owner.module, "main", side_effect=call_main), \
                 mock.patch.object(driver, "setattr", side_effect=setter, create=True), \
                 mock.patch.object(owner.module.os, "fsync"), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(driver.main(["--execute"]), 9)
            self.assertFalse(driver._LINK_ACTIVE)
            if parent:
                events = [json.loads(line) for line in terminal.value.splitlines()]
                self.assertEqual([item["event"] for item in events], ["TERMINAL_VETO"])
                self.assertEqual(events[0]["actual_worker_exit"], 0)

    def test_terminal_error_keeps_primary_error_and_secondary_cleanup_error(self):
        owner, terminal = driver.original(), MemoryFile()

        def call_main(argv):
            return owner.module.finalize_disposition(terminal,
                dict(intended_supervisor_exit=0, actual_worker_exit=0), Clock().guard())

        errors = io.StringIO()
        with mock.patch.object(owner.module, "main", side_effect=call_main), \
             mock.patch.object(owner, "finalize_disposition", side_effect=ValueError("모의 최초 종결 오류")), \
             mock.patch.object(owner.module, "append_terminal", side_effect=OSError("모의 추가 저장 오류")), \
             contextlib.redirect_stderr(errors):
            self.assertEqual(driver.main(["--execute"]), 9)
        value = json.loads(errors.getvalue())
        self.assertEqual(value["exception"], "모의 최초 종결 오류")
        self.assertEqual(value["terminal_cleanup_error"]["exception"], "모의 추가 저장 오류")

    def test_exact_warmup_measure_and_maximum_budget_are_required(self):
        with driver.linked() as base:
            base.validate_args(arguments())
            for changes in ({"warmup": 1}, {"measure": 4}, {"max_wall_sec": 871},
                            {"max_wall_sec": 59}, {"tag": "p102a_v12_kernel_v1_s1337_old"}):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    base.validate_args(arguments(**changes))

    def test_parser_default_stays_within_870_and_2_5(self):
        with driver.linked() as base:
            args = base.parser().parse_args(["--check-only"])
        self.assertEqual((args.max_wall_sec, args.warmup, args.measure), (870, 2, 5))

    def test_complete_observation_is_not_adoption(self):
        for expanded in (False, True):
            self.assertEqual(driver.decide(observed_report(expanded), 0, driver.original()), 0)

    def test_actual_worker_exit9_overrides_nominal_success(self):
        self.assertEqual(driver.decide(observed_report(), 9, driver.original()), 9)

    def test_missing_hybrid_or_cpu_reference_vetoes_completion(self):
        for name in ("hybrid_forward_native", "full_original_cpu_reference"):
            report = observed_report()
            del report["observations"]["cases"][0]["implementation_checks"][name]
            self.assertEqual(driver.decide(report, 0, driver.original()), 9)

    def test_false_or_empty_exact_check_is_not_pass(self):
        for value in ([], {"bitwise_equal": False}, [{"bitwise_equal": False}]):
            report = observed_report()
            report["observations"]["cases"][0]["implementation_checks"]["hybrid_forward_native"] = value
            self.assertEqual(driver.decide(report, 0, driver.original()), 9)

    def test_missing_large_shape_and_producer_are_not_complete(self):
        for key in ("cases", "producers"):
            report = observed_report(True)
            report["observations"][key].pop()
            self.assertEqual(driver.decide(report, 0, driver.original()), 9)

    def test_missing_or_nonfinite_timing_sample_is_not_complete(self):
        for missing in (True, False):
            report = observed_report()
            samples = report["observations"]["cases"][0]["phases"][driver.PIPELINE_PHASES[0]]["samples"]
            if missing:
                samples.pop()
            else:
                samples[-1]["synchronized_wall_ms"] = float("nan")
            self.assertEqual(driver.decide(report, 0, driver.original()), 9)

    def test_producer_ulp_limit_cannot_be_relaxed_or_negative(self):
        for key, value in (("max_bf16_ulps", 2), ("max_bf16_ulps", -1), ("original_v12_local_ulp_limit", 2),
                           ("primitive_forward_grad_enabled", True)):
            report = observed_report()
            report["observations"]["producers"][0][key] = value
            self.assertEqual(driver.decide(report, 0, driver.original()), 9)

    def test_delayed_write_and_readback_consume_same_parent_budget(self):
        base = driver.original().module
        for write, read in ((61., 0.), (0., 61.)):
            clock = Clock()
            path = MemoryFile(clock=clock, write_delay=write, read_delay=read)
            with mock.patch.object(base.os, "fsync"), self.assertRaises(TimeoutError):
                base.write_new(path, {"status": "모의 결과"}, clock.guard())

    def test_delayed_stdout_and_terminal_write_append_veto(self):
        base = driver.original().module
        for delay in ("stdout", "terminal"):
            clock, terminal = Clock(), MemoryFile()
            if delay == "terminal":
                terminal.clock, terminal.write_delay = clock, 61.

            class SlowOutput(io.StringIO):
                def flush(self):
                    if delay == "stdout":
                        clock.tick(61.)

            with mock.patch.object(base.os, "fsync"), contextlib.redirect_stdout(SlowOutput()):
                code = base.finalize_disposition(terminal,
                    dict(intended_supervisor_exit=0, actual_worker_exit=0), clock.guard())
            self.assertEqual(code, 9)
            events = [json.loads(line) for line in terminal.value.splitlines()]
            self.assertEqual(events[-1]["event"], "TERMINAL_VETO")
            self.assertEqual(events[-1]["actual_worker_exit"], 0)

    def test_new_json_cannot_overwrite_and_nonfinite_cannot_publish(self):
        base = driver.original().module
        path = MemoryFile()
        with mock.patch.object(base.os, "fsync"):
            base.write_new(path, {"value": 1}, Clock().guard())
            with self.assertRaises(FileExistsError):
                base.write_new(path, {"value": 2}, Clock().guard())
        with self.assertRaises(ValueError):
            base.write_new(MemoryFile(), {"value": float("inf")}, Clock().guard())

    def test_twenty_megabyte_limit_is_checked_before_write(self):
        base, path = driver.original().module, MemoryFile()
        with mock.patch.object(base, "MAX_FILE", 32), self.assertRaises(ValueError):
            base.write_new(path, {"value": "x" * 64}, Clock().guard())
        self.assertFalse(path.present)

    def test_real_cpu_child_uses_owned_group_tool_and_actual_zero_exit(self):
        base = driver.original().module
        tools = base.process_tools()
        began = time.monotonic()
        start = datetime(2026, 10, 25, tzinfo=timezone.utc)
        guard = base.Guard(start + timedelta(seconds=20), 60, started=began,
            now=lambda: start + timedelta(seconds=time.monotonic() - began), clock=time.monotonic)
        processes = []

        def factory(argv, **options):
            child = subprocess.Popen(argv, **options, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes.append(child)
            return child

        try:
            with driver.linked():
                receipt = base.run_owned_worker([sys.executable, "-B", "-c", "pass"],
                    dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONDONTWRITEBYTECODE="1"),
                    MemoryFile(), guard, factory=factory, tools=tools)
            self.assertEqual(receipt["status"], "COMPLETE")
            self.assertEqual(receipt["returncode"], 0)
            self.assertFalse(receipt["unsafe_process_state"])
            self.assertEqual(processes[0].poll(), 0)
            self.assertEqual(tools._OWNED_GROUPS, {})
        finally:
            for child in processes:
                if child.poll() is None:
                    tools.stop_process_group(child, time.monotonic() + 3., time.monotonic)
                child.wait(timeout=3.)

    def test_original_supervisor_launches_companion_and_preserves_cleanup_failure(self):
        for unsafe in (False, True):
            owner = driver.original()
            report = observed_report()
            report["sources"] = {"source_sha256": "A" * 64}
            files = {name: MemoryFile() for name in ("worker.log", "terminal.jsonl")}
            files["report.json"] = MemoryFile(json.dumps(report).encode())
            files["report.json"].read_text = lambda encoding=None: files["report.json"].value.decode()
            target = mock.MagicMock()
            target.__truediv__.side_effect = lambda name: files.get(name, Path("/unused") / name)
            captured = []

            def run(command, env, logfile, guard, **options):
                captured.append((command, env))
                options["state"].update(status="TOOL_ERROR" if unsafe else "COMPLETE", returncode=0,
                    process_started=True, unsafe_process_state=unsafe,
                    error="모의 정리 오류" if unsafe else None)

            with driver.linked(owner) as base, contextlib.ExitStack() as stack:
                stack.enter_context(mock.patch.object(base, "source_receipt", return_value=report["sources"]))
                stack.enter_context(mock.patch.object(base, "target_path", return_value=target))
                stack.enter_context(mock.patch.object(base, "write_new"))
                stack.enter_context(mock.patch.object(base, "run_owned_worker", side_effect=run))
                stack.enter_context(mock.patch.object(base.os, "fsync"))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                code = base.supervise(arguments(), Clock().guard())
            self.assertEqual(code, 9 if unsafe else 0)
            command, env = captured[0]
            self.assertEqual(command[4], str(PATH))
            self.assertIn("--_worker", command)
            self.assertEqual(command[command.index("--warmup") + 1], "2")
            self.assertEqual(command[command.index("--measure") + 1], "5")
            self.assertEqual(env["TINYLM_V12_KERNEL_WORKER"], str(os.getpid()))
            terminal = [json.loads(line) for line in files["terminal.jsonl"].value.splitlines()]
            self.assertEqual(terminal[0]["actual_worker_exit"], 0)
            if unsafe:
                self.assertEqual(terminal[0]["error"]["exception_class"], "Incomplete")
                self.assertIn("모의 정리 오류", terminal[0]["error"]["exception"])


class TestCpuOriginalMath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        driver.source_receipt()
        import torch
        cls.t = torch
        torch.set_num_threads(2)
        archive = str(driver.original().module.ARCHIVE)
        previous_path = list(sys.path)
        try:
            sys.path.insert(0, archive)
            import v12_code_reuse as core
            import v12_swiglu as swiglu
        finally:
            sys.path[:] = previous_path
        cls.core, cls.swiglu = core, swiglu

    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        for name in ("synchronize", "get_device_capability", "get_device_name", "Event"):
            self.stack.enter_context(mock.patch.object(self.t.cuda, name,
                side_effect=AssertionError("CPU 합성 시험에서 CUDA 호출 금지")))

    def mods(self):
        t, core = self.t, self.core

        def pack(value, compute, group, terms, weight, binary):
            p = core.pack_cpu(value, compute, group, terms, weight, binary)
            return p.rows.codes, p.rows.scale, p.high, p.low, p.sh, p.sl, t.zeros((), dtype=t.int32)

        def gradients(g, sx, sw):
            return core.quantize_rows(g.float() * sw[None, :]), core.quantize_rows((g.float() * sx[:, None]).T), t.zeros((), dtype=t.int32)

        kernels = types.SimpleNamespace(pack=pack, gradient_gemm=core.gradient_cpu,
            forward_gemm=lambda h, lo, sh, sl, w, sw, terms, group, dtype:
                core.group_forward(h, lo, sh, sl, w, sw, terms, group, "cpu_int8", dtype))
        swiglu = types.SimpleNamespace(launch=lambda g, u, group: self.swiglu.producer_op(g, u, "cpu_int8", group),
            _SwiGLU=types.SimpleNamespace(apply=lambda g, u, backend, group:
                self.swiglu._SwiGLU.apply(g, u, "cpu_int8", group)))
        return {"v12_kernels": kernels, "v11_reuse_kernels": types.SimpleNamespace(pack_weighted_gradients=gradients),
                "v12_code_reuse": core, "v12_swiglu": swiglu}

    def tensors(self):
        t = self.t
        generator = t.Generator().manual_seed(1337)
        x = t.randn((4, 128), generator=generator).bfloat16()
        w = (t.randint(-1, 2, (16, 128), generator=generator) * .03125).bfloat16()
        dy = t.randn((4, 16), generator=generator).bfloat16()
        return x, w, dy

    def test_hybrid_forward_exact_native_and_gradients_exact_original_cpu(self):
        t, mods = self.t, self.mods()
        x, w, dy = self.tensors()
        native = driver.pipeline(t, mods, x, w, dy, "native")
        integers = driver.pipeline(t, mods, x, w, dy, "int_full")
        hybrid = driver.pipeline(t, mods, x, w, dy, "hybrid")
        expected = driver.cpu_reference(t, mods, x, w, dy)
        self.assertTrue(t.equal(hybrid[0], native[0]))
        self.assertTrue(all(t.equal(a, b) for a, b in zip(hybrid[1:3], integers[1:3])))
        self.assertTrue(all(t.equal(a, b) for a, b in zip(integers[:3], expected)))
        self.assertFalse(all(t.equal(a, b) for a, b in zip(native[1:3], integers[1:3])))

    def test_gradient_operands_are_strided_views_without_explicit_copy(self):
        t, mods = self.t, self.mods()
        x, w, dy = self.tensors()
        seen = []
        gradient = mods["v12_kernels"].gradient_gemm

        def observe(rows, right, compute, dtype):
            seen.append((right._base is not None, right.is_contiguous()))
            return gradient(rows, right, compute, dtype)

        mods["v12_kernels"].gradient_gemm = observe
        driver.pipeline(t, mods, x, w, dy, "hybrid")
        self.assertEqual(seen, [(True, False), (True, False)])

    def test_hybrid_uses_original_terms0_pack_and_weight_reuse(self):
        t, mods = self.t, self.mods()
        x, w, dy = self.tensors()
        pack = mods["v12_kernels"].pack
        seen = []

        def observe(value, compute, group, terms, weight, binary):
            seen.append((id(value), terms, weight, binary))
            return pack(value, compute, group, terms, weight, binary)

        mods["v12_kernels"].pack = observe
        cached = driver.pack_operand(t, mods, w, "hybrid", True)
        seen.clear()
        reused = driver.pipeline(t, mods, x, w, dy, "hybrid", cached)
        self.assertEqual(seen, [(id(x), 0, False, False)])
        cold = driver.pipeline(t, mods, x, w, dy, "hybrid")
        self.assertTrue(all(t.equal(a, b) for a, b in zip(reused[:3], cold[:3])))

    def test_pipeline_does_not_read_scalar_bad_inside_timed_call(self):
        t, mods = self.t, self.mods()
        x, w, dy = self.tensors()
        raw = mods["v11_reuse_kernels"].pack_weighted_gradients

        class Flag:
            def __bool__(self):
                raise AssertionError("계측 안의 scalar 동기화")

        def gradients(*args):
            a, b, _ = raw(*args)
            return a, b, Flag()

        mods["v11_reuse_kernels"].pack_weighted_gradients = gradients
        output = driver.pipeline(t, mods, x, w, dy, "hybrid")
        with self.assertRaisesRegex(AssertionError, "scalar"):
            driver.check_outputs(t, driver.original().module, output)

    def test_approximation_is_separate_and_cannot_become_five_percent_pass(self):
        t, base = self.t, driver.original().module
        observation = base.approximation(t, t.tensor([2.]), t.tensor([1.]))
        self.assertGreater(observation["relative_l2"], .05)
        self.assertIsNone(observation["acceptance_threshold"])
        self.assertFalse(observation["quality_claim"])
        with self.assertRaises(base.NumericMismatch):
            base.exact(t, t.tensor([2.]), t.tensor([1.]), "별도 원식 차이")

    def test_finite_flags_and_wrong_dtype_cannot_be_observed_as_exact(self):
        t, base = self.t, driver.original().module
        with self.assertRaises(FloatingPointError):
            driver.check_outputs(t, base, (t.tensor([float("inf")]), t.ones(1), t.ones(1), ()))
        with self.assertRaises(FloatingPointError):
            driver.check_outputs(t, base, (t.ones(1), t.ones(1), t.ones(1), (t.tensor(1),)))
        with self.assertRaises(base.NumericMismatch):
            base.exact(t, t.ones(1).bfloat16(), t.ones(1), "dtype 경계")

    def test_original_low_boundary_and_zero_ternary_pack(self):
        t, mods = self.t, self.mods()
        x = t.zeros((1, 128), dtype=t.bfloat16)
        x[0, 0], x[0, 1], x[0, 2] = 127., .5, -.5
        packed = driver.pack_operand(t, mods, x, "int_full")
        self.assertEqual((int(packed[3][0, 1]), int(packed[3][0, 2])), (-128, -128))
        zero = driver.pack_operand(t, mods, t.zeros_like(x), "int_full", True)
        self.assertEqual(int(zero[0].abs().sum()), 0)

    def test_original_bf16_ulp_zero_one_two_and_signed_zero(self):
        t, base = self.t, driver.original().module
        reference = t.ones(1, dtype=t.bfloat16)
        bits = reference.view(t.int16)
        self.assertEqual(driver.producer_ulp(t, base, reference, reference), 0)
        self.assertEqual(driver.producer_ulp(t, base, (bits + 1).view(t.bfloat16), reference), 1)
        with self.assertRaises(base.NumericMismatch):
            driver.producer_ulp(t, base, (bits + 2).view(t.bfloat16), reference)
        self.assertEqual(driver.producer_ulp(t, base, t.tensor([-0.]).bfloat16(), t.tensor([0.]).bfloat16()), 0)
        with self.assertRaises(FloatingPointError):
            driver.producer_ulp(t, base, t.tensor([float("nan")]).bfloat16(), reference)

    def test_matched_producers_return_all_outputs_without_autograd_graph(self):
        t, mods = self.t, self.mods()
        generator = t.Generator().manual_seed(1337)
        g = t.randn((2, 128), generator=generator).bfloat16().requires_grad_()
        u = t.randn((2, 128), generator=generator).bfloat16().requires_grad_()
        left = driver.producer_forward(t, mods, g, u, False)
        right = driver.producer_forward(t, mods, g, u, True)
        self.assertEqual((len(left), len(right)), (8, 8))
        self.assertFalse(left[0].requires_grad)
        self.assertFalse(right[0].requires_grad)
        self.assertTrue(all(t.equal(a, b) for a, b in zip(left, right)))

    def test_original_vjp_is_exact_and_native_arm_includes_pack(self):
        t, mods = self.t, self.mods()
        generator = t.Generator().manual_seed(1337)
        g = t.randn((2, 128), generator=generator).bfloat16().requires_grad_()
        u = t.randn((2, 128), generator=generator).bfloat16().requires_grad_()
        dy = t.randn((2, 128), generator=generator).bfloat16()
        with mock.patch.object(mods["v12_kernels"], "pack", wraps=mods["v12_kernels"].pack) as packed:
            left = driver.producer_vjp(t, mods, g, u, dy, False)
        packed.assert_called_once()
        right = driver.producer_vjp(t, mods, g, u, dy, True)
        self.assertTrue(all(t.equal(a, b) for a, b in zip(left[0], right[0])))


if __name__ == "__main__":
    unittest.main()
