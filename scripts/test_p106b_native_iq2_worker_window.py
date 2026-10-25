"""날짜 파생과 별도 세션 고아 worker 회수의 모델 없는 CPU 회귀."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts import p106b_native_iq2_worker_window as run


class BuildContracts(unittest.TestCase):
    def test_exact_two_literals_and_backend_guard_order(self):
        source = (run.ROOT / "scripts/p106b_native_llama_worker.cpp").read_bytes()
        derived = run.derive_source(source)
        self.assertEqual(derived.replace(str(run.NEW_EPOCH).encode(), str(run.OLD_EPOCH).encode())
            .replace(run.NEW_TEXT.encode(), run.OLD_TEXT.encode()), source)
        self.assertNotEqual(derived, source)
        self.assertLess(derived.index(b"if(argv[2]!=allowed)"), derived.index(b"Runtime runtime(argv[2],architecture)"))
        for bad in (source.replace(str(run.OLD_EPOCH).encode(), b"0"), source + str(run.OLD_EPOCH).encode(),
                source.replace(b"if(argv[2]!=allowed)", b"if(false)")):
            with self.assertRaises((ValueError, IndexError)):
                run.derive_source(bad)

    def test_cpu_probe_commands_never_name_registered_model(self):
        calls = []
        def runner(argv, **kwargs):
            calls.append(argv)
            if argv[-1] == "--self-test":
                return subprocess.CompletedProcess(argv, 0, "CPU_ONLY; backend_init=0; model_loads=0", "")
            marker = run.OLD_TEXT if argv[0] == "/old" else run.NEW_TEXT if int(argv[-1]) > run.NEW_EPOCH else "unregistered model path; no backend initialized"
            return subprocess.CompletedProcess(argv, 9, "", marker)
        result = run.cpu_probes(Path("/old"), Path("/new"), runner=runner)
        self.assertEqual(len(result), 5)
        self.assertTrue(all("/__tinylm_unregistered_iq2_window_probe__" in argv for argv in calls if "--execute" in argv))

    def test_bad_cpu_probe_is_not_accepted(self):
        with self.assertRaises(ValueError):
            run.cpu_probes(Path("/old"), Path("/new"), runner=lambda argv, **kw: subprocess.CompletedProcess(argv, 0, "", ""))

    def test_write_once_and_twenty_mb_and_append_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            run.write_once(path, {"정상": True})
            with self.assertRaises(FileExistsError):
                run.write_once(path, {"덮기": True})
            with patch.object(run, "MAX_BYTES", 10), self.assertRaises(ValueError):
                run.write_once(Path(tmp) / "big.json", {"길이": "가" * 10})
            first = run.append_veto(tmp, {"원인": "첫 실패"})
            second = run.append_veto(tmp, {"원인": "둘째 실패"})
            self.assertNotEqual(first, second)
            self.assertEqual(run.read_json(first)["원인"], "첫 실패")

    def test_pure_cli_not_ready_does_not_prepare_or_load(self):
        with patch.object(run, "build_identity", return_value=dict(status="NOT_READY", models=0, backend_initializations=0)), \
                patch.object(run, "prepare") as prepare, redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run.main(["--check-only"]), 8)
            self.assertEqual(json.loads(output.getvalue())["status"], "NOT_READY")
            prepare.assert_not_called()

    def test_missing_build_is_explicit_not_ready_without_subprocess(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp, patch.object(run, "original_identity",
                return_value=(SimpleNamespace(HEADERS=Path(tmp)), {"sha256": "고정"})), \
                patch.object(run.subprocess, "run") as process:
            self.assertEqual(run.build_identity()["status"], "NOT_READY")
            process.assert_not_called()

    def test_ready_receipt_requires_exact_derived_bytes_worker_hash_and_cpu_proof(self):
        from types import SimpleNamespace
        source = (run.ROOT/"scripts/p106b_native_llama_worker.cpp").read_bytes()
        for change in ("none", "source", "binary", "proof", "origin"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); headers = root/"headers"; directory = headers/run.FOLDER
                directory.mkdir(parents=True); (root/"scripts").mkdir()
                (root/"scripts/p106b_native_llama_worker.cpp").write_bytes(source)
                cpp = directory/"worker_window.cpp"; cpp.write_bytes(run.derive_source(source))
                binary = headers/run.WORKER; binary.write_bytes(b"synthetic CPU binary, never executed")
                frozen = dict(sha256="고정", build=dict(worker="원worker"))
                receipt = dict(schema=run.SCHEMA, deadline_epoch=run.NEW_EPOCH, original_native_sha256="고정",
                    original_build=frozen["build"], worker=run.WORKER, cpp_sha256=run.digest(cpp),
                    worker_sha256=run.digest(binary), cpu_probe_passed=True, models=0, backend_initializations=0)
                if change == "source": cpp.write_bytes(cpp.read_bytes()+b" ")
                if change == "binary": binary.write_bytes(b"changed")
                if change == "proof": receipt["cpu_probe_passed"] = False
                if change == "origin": receipt["original_native_sha256"] = "변경"
                run.write_once(directory/"build_receipt.json", receipt)
                with patch.object(run, "ROOT", root), patch.object(run, "original_identity",
                        return_value=(SimpleNamespace(HEADERS=headers), frozen)):
                    if change == "none": self.assertEqual(run.build_identity()["status"], "READY")
                    else:
                        with self.assertRaises(ValueError): run.build_identity()


@unittest.skipUnless(sys.platform == "linux" and hasattr(os, "waitpid"), "Linux CPU 프로세스 회귀")
class SupervisionContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name); self.binary = self.base / "synthetic_worker"
        shutil.copyfile("/bin/sleep", self.binary); self.binary.chmod(0o700)

    def supervise(self, script, *, cap=3., reserve=1., verify=None):
        return run.supervise_process([sys.executable, "-B", "-c", script], worker_binary=self.binary,
            directory=self.base / "supervisor", deadline_epoch=time.time()+10, cap=cap, reserve=reserve,
            verify_success=verify)

    def spawn_script(self, action):
        return ("import os,subprocess,signal,time; "
            + "p=subprocess.Popen([" + repr(str(self.binary)) + ", '30'], start_new_session=True); " + action)

    def test_actual_controller_sigkill_reaps_orphan_new_session_worker(self):
        result = self.supervise(self.spawn_script("time.sleep(.15); os.kill(os.getpid(),signal.SIGKILL)"))
        self.assertEqual(result["returncode"], 9)
        self.assertEqual(result["controller_returncode"], -signal.SIGKILL)
        self.assertEqual(result["original_error"]["type"], "ChildProcessError")
        self.assertTrue(result["worker_reaping"])
        self.assertTrue(all(row.get("reaped") for row in result["worker_reaping"]))
        self.assertEqual(list(run.find_owned_workers(self.binary, "unmatched", result["controller_identity"])), [])
        self.assertTrue(list((self.base / "supervisor").glob("supervisor_veto_*.json")))

    def test_parent_dies_immediately_after_spawning_worker(self):
        result = self.supervise(self.spawn_script("os._exit(7)"))
        self.assertEqual(result["controller_returncode"], 7)
        self.assertTrue(result["worker_reaping"])
        self.assertEqual(result["cleanup_errors"], [])

    def test_success_has_actual_exit_and_no_worker(self):
        result = self.supervise("print('CPU')", verify=lambda: {"모의": True})
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["controller_returncode"], 0)
        self.assertTrue(result["actual_controller_exit_observed"])

    def test_worker_left_after_success_is_vetoed_and_reaped(self):
        result = self.supervise(self.spawn_script("os._exit(0)"))
        self.assertEqual(result["returncode"], 9)
        self.assertTrue(result["worker_reaping"])
        self.assertEqual(result["cleanup_errors"], [])

    def test_actual_work_timeout_closes_controller_and_worker(self):
        result = self.supervise(self.spawn_script("time.sleep(30)"), cap=2., reserve=1.)
        self.assertEqual(result["returncode"], 9)
        self.assertEqual(result["original_error"]["type"], "TimeoutError")
        self.assertIsNotNone(result["controller_returncode"])
        self.assertTrue(result["worker_reaping"])

    def test_unrelated_same_binary_environment_token_is_never_owned(self):
        process = subprocess.Popen([str(self.binary), "30"], start_new_session=True)
        try:
            result = self.supervise("pass")
            self.assertEqual(result["returncode"], 0)
            self.assertIsNone(process.poll())
        finally:
            os.killpg(process.pid, signal.SIGKILL); process.wait()

    def test_cleanup_failure_preserves_actual_primary_and_append_only_veto(self):
        with patch.object(run, "cleanup_workers", side_effect=RuntimeError("모의 청소 실패")):
            result = self.supervise("raise ValueError('모의 첫 실패')")
        self.assertEqual(result["returncode"], 9)
        self.assertEqual(result["original_error"]["type"], "ChildProcessError")
        self.assertEqual(result["cleanup_errors"][0]["message"], "모의 청소 실패")

    def test_storage_delay_cannot_promote_saved_candidate(self):
        original = run.write_once
        def delayed(path, value):
            original(path, value)
            if Path(path).name == "supervisor_receipt.json":
                time.sleep(.2)
        with patch.object(run, "write_once", side_effect=delayed):
            result = self.supervise("pass", cap=.15, reserve=.05)
        self.assertEqual(result["returncode"], 9)
        self.assertTrue(list((self.base / "supervisor").glob("supervisor_veto_*.json")))

    def test_terminal_verification_error_keeps_real_exit_zero_but_vetoes(self):
        def fail():
            raise ValueError("모의 종결 해시 불일치")
        result = self.supervise("pass", verify=fail)
        self.assertEqual(result["controller_returncode"], 0)
        self.assertEqual(result["returncode"], 9)
        self.assertIn("종결", result["original_error"]["message"])

    def test_existing_partial_namespace_never_launches(self):
        (self.base / "supervisor").mkdir()
        with patch.object(run.subprocess, "Popen") as popen, self.assertRaises(ValueError):
            self.supervise("pass")
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
