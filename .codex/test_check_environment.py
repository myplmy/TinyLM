#!/usr/bin/env python3
"""Mock-only regression tests for .codex/check_environment.py."""
from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().with_name("check_environment.py")
SPEC = importlib.util.spec_from_file_location("tinylm_codex_environment", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
ENV = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ENV
SPEC.loader.exec_module(ENV)


def completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["bash"], returncode, stdout, stderr)


class BashProbeTests(unittest.TestCase):
    def test_ready(self) -> None:
        state, _ = ENV.classify_bash_probe(Path("bash.exe"), runner=lambda *a, **k: completed(0))
        self.assertEqual(state, "READY")

    def test_missing(self) -> None:
        state, _ = ENV.classify_bash_probe(None)
        self.assertEqual(state, "MISSING")

    def test_known_windows_sandbox_signature_is_not_run(self) -> None:
        failure = completed(
            -1073741502,
            stderr="fatal error - couldn't create signal pipe, Win32 error 5",
        )
        state, detail = ENV.classify_bash_probe(Path("bash.exe"), runner=lambda *a, **k: failure)
        self.assertEqual(state, "SANDBOX_UNAVAILABLE")
        self.assertIn("0xC0000142", detail)

    def test_code_or_message_alone_does_not_hide_unknown_failure(self) -> None:
        code_only = completed(-1073741502, stderr="unrelated startup failure")
        message_only = completed(9, stderr="couldn't create signal pipe, Win32 error 5")
        for result in (code_only, message_only):
            with self.subTest(result=result):
                state, _ = ENV.classify_bash_probe(
                    Path("bash.exe"), runner=lambda *a, _result=result, **k: _result
                )
                self.assertEqual(state, "BROKEN")


class ShellSyntaxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.shell_file = ENV.REPO_ROOT / ".agents" / "skills" / "pr-workflow" / "scripts" / "create_pr.sh"

    def test_missing_bash_is_one_not_run(self) -> None:
        state, detail = ENV.shell_syntax_result([self.shell_file], bash=None)
        self.assertEqual(state, "NOT_RUN")
        self.assertIn("not found", detail)

    def test_known_sandbox_failure_is_one_not_run_before_file_parse(self) -> None:
        calls: list[list[str]] = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return completed(
                -1073741502,
                stderr="fatal error - couldn't create signal pipe, Win32 error 5",
            )

        state, _ = ENV.shell_syntax_result(
            [self.shell_file, self.shell_file], bash=Path("bash.exe"), runner=runner
        )
        self.assertEqual(state, "NOT_RUN")
        self.assertEqual(len(calls), 1)

    def test_ready_bash_reports_source_failure_only_after_probe(self) -> None:
        calls = 0

        def runner(argv, **kwargs):
            nonlocal calls
            calls += 1
            return completed(0) if "-c" in argv else completed(2, stderr="syntax error")

        state, detail = ENV.shell_syntax_result(
            [self.shell_file], bash=Path("bash.exe"), runner=runner
        )
        self.assertEqual(calls, 2)
        self.assertEqual(state, "FAIL")
        self.assertIn("source syntax errors", detail)

    def test_ready_bash_and_valid_file_pass(self) -> None:
        state, _ = ENV.shell_syntax_result(
            [self.shell_file], bash=Path("bash.exe"), runner=lambda *a, **k: completed(0)
        )
        self.assertEqual(state, "PASS")


class LedgerTests(unittest.TestCase):
    def emit(self, ledger, *, strict=False) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = ledger.emit(require_shell_syntax=strict)
        return code, output.getvalue()

    def test_not_run_is_visible_and_has_distinct_exit(self) -> None:
        ledger = ENV.Ledger()
        ledger.record("other", True, "ok")
        ledger.record_status("POSIX shell syntax", "NOT_RUN", "sandbox")
        code, output = self.emit(ledger)
        self.assertEqual(code, 2)
        self.assertIn("PASS=1 FAIL=0 NOT_RUN=1", output)
        strict_code, _ = self.emit(ledger, strict=True)
        self.assertEqual(strict_code, 1)

    def test_real_failure_takes_precedence(self) -> None:
        ledger = ENV.Ledger()
        ledger.record("Python syntax", False, "bad")
        ledger.record_status("POSIX shell syntax", "NOT_RUN", "sandbox")
        code, output = self.emit(ledger)
        self.assertEqual(code, 1)
        self.assertIn("PASS=0 FAIL=1 NOT_RUN=1", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
