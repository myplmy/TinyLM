#!/usr/bin/env python3
"""Mock-only regression tests for .codex/check_environment.py."""
from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
import unittest
from unittest import mock
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


class PlatformDiscoveryTests(unittest.TestCase):
    def test_posix_bash_uses_path_lookup(self) -> None:
        with mock.patch.object(ENV.os, "name", "posix"), mock.patch.object(
            ENV.shutil, "which", return_value="/usr/bin/bash"
        ):
            self.assertEqual(ENV.find_git_bash(), Path("/usr/bin/bash"))

    def test_missing_powershell_is_not_run(self) -> None:
        state, detail = ENV.powershell_syntax_result(
            [ENV.CODEX_ROOT / "hooks" / "compact_state_windows.ps1"],
            executable=None,
        )
        self.assertEqual(state, "NOT_RUN")
        self.assertIn("unavailable", detail)

    def test_available_powershell_parses_source(self) -> None:
        calls: list[list[str]] = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return completed(0)

        state, detail = ENV.powershell_syntax_result(
            [ENV.CODEX_ROOT / "hooks" / "compact_state_windows.ps1"],
            executable="pwsh",
            runner=runner,
        )
        self.assertEqual(state, "PASS")
        self.assertEqual(calls[0][0], "pwsh")
        self.assertIn("parsed", detail)

    def test_posix_working_rule_mtime_is_informational(self) -> None:
        with mock.patch.object(ENV.os, "name", "posix"):
            passed, detail = ENV.check_working_rule_parity()
        self.assertTrue(passed, detail)
        self.assertIn("mtime=informational", detail)


class TomlCompatibilityTests(unittest.TestCase):
    def test_current_config_parses_without_tomllib(self) -> None:
        text = ENV.read_utf8(ENV.CODEX_ROOT / "config.toml")
        parsed = ENV.parse_codex_config(text, parser=None)
        self.assertEqual(parsed["project_doc_max_bytes"], 32768)
        self.assertEqual(parsed["project_doc_fallback_filenames"], [])
        self.assertEqual(parsed["project_root_markers"], [".git"])

    def test_fallback_rejects_toml_tables_instead_of_misreading_them(self) -> None:
        with self.assertRaisesRegex(ValueError, "tables require Python 3.11"):
            ENV.parse_codex_config("[hooks]\nenabled = true\n", parser=None)

    def test_module_import_survives_when_tomllib_is_unavailable(self) -> None:
        module_name = "tinylm_codex_environment_without_tomllib"
        spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        real_import = __import__

        def blocked_import(name, *args, **kwargs):
            if name == "tomllib":
                raise ModuleNotFoundError("No module named 'tomllib'", name="tomllib")
            return real_import(name, *args, **kwargs)

        sys.modules[module_name] = module
        try:
            with mock.patch("builtins.__import__", side_effect=blocked_import):
                spec.loader.exec_module(module)
            self.assertIsNone(module._tomllib)
            parsed = module.parse_codex_config(
                module.read_utf8(module.CODEX_ROOT / "config.toml")
            )
            self.assertEqual(parsed["project_root_markers"], [".git"])
        finally:
            sys.modules.pop(module_name, None)


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
