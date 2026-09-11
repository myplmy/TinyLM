#!/usr/bin/env python3
"""Mock tests for the TinyLM Codex backslash PreToolUse guard."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

GUARD_PATH = Path(__file__).resolve().with_name("guard_backslash.py")
WINDOWS_WRAPPER_PATH = GUARD_PATH.with_name("guard_backslash_windows.ps1")
HOOKS_PATH = GUARD_PATH.parents[1] / "hooks.json"
SPEC = importlib.util.spec_from_file_location("codex_guard_backslash", GUARD_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {GUARD_PATH}")
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


def event(
    command: str,
    *,
    hook_event_name: str = "PreToolUse",
    tool_name: str = "Bash",
) -> dict[str, object]:
    return {
        "hook_event_name": hook_event_name,
        "cwd": str(GUARD_PATH.parents[2]),
        "tool_name": tool_name,
        "tool_input": {"command": command},
    }


def decision(response: dict[str, object] | None) -> str | None:
    if not isinstance(response, dict):
        return None
    specific = response.get("hookSpecificOutput")
    if not isinstance(specific, dict):
        return None
    value = specific.get("permissionDecision")
    return value if isinstance(value, str) else None


def windows_handler() -> str:
    hooks = json.loads(HOOKS_PATH.read_text(encoding="utf-8"))
    return hooks["hooks"]["PreToolUse"][0]["hooks"][0]["commandWindows"]


class GuardEvaluationTests(unittest.TestCase):
    def test_non_event_input_continues(self) -> None:
        self.assertIsNone(GUARD.evaluate_event(None))
        self.assertIsNone(GUARD.evaluate_event({"tool_input": {}}))

    def test_wrong_event_and_tool_continue(self) -> None:
        self.assertIsNone(
            GUARD.evaluate_event(event("Set-Content x 'a\\nb'", hook_event_name="PostToolUse"))
        )
        self.assertIsNone(
            GUARD.evaluate_event(event("Set-Content x 'a\\nb'", tool_name="apply_patch"))
        )

    def test_read_only_backslash_command_continues(self) -> None:
        self.assertIsNone(GUARD.evaluate_event(event(r"rg '\d+' .agents")))

    def test_plain_write_continues(self) -> None:
        self.assertIsNone(
            GUARD.evaluate_event(
                event("Set-Content -LiteralPath '.codex/probe.txt' -Value 'plain'")
            )
        )

    def test_null_redirect_continues(self) -> None:
        self.assertIsNone(
            GUARD.evaluate_event(event(r"Write-Output 'a\nb' > $null"))
        )

    def test_windows_paths_are_not_escape_payloads(self) -> None:
        command = (
            r"Set-Content -LiteralPath 'C:\temp\new.txt' "
            r"-Value 'scripts\check.py'"
        )
        self.assertIsNone(GUARD.evaluate_event(event(command)))

    def test_redirect_with_risky_escape_is_denied(self) -> None:
        response = GUARD.evaluate_event(event(r"Write-Output 'a\nb' > probe.txt"))
        self.assertEqual(decision(response), "deny")

    def test_set_content_with_risky_escape_is_denied(self) -> None:
        command = (
            r"if ($false) { Set-Content -LiteralPath '.codex/hook-probe.txt' "
            r"-Value 'a\nb' }"
        )
        response = GUARD.evaluate_event(event(command))
        self.assertEqual(decision(response), "deny")

    def test_python_write_with_risky_escape_is_denied(self) -> None:
        command = r'''python -c "from pathlib import Path; Path('x').write_text('a\nb')"'''
        response = GUARD.evaluate_event(event(command))
        self.assertEqual(decision(response), "deny")

    def test_actual_control_character_is_denied(self) -> None:
        command = "Set-Content -LiteralPath 'x' -Value 'a\x08b'"
        response = GUARD.evaluate_event(event(command))
        self.assertEqual(decision(response), "deny")

    def test_explicit_allow_token_continues_with_warning(self) -> None:
        command = r"Write-Output 'a\nb' > probe.txt # ALLOW_BACKSLASH_WRITE"
        response = GUARD.evaluate_event(event(command))
        self.assertIsInstance(response, dict)
        self.assertIsNone(decision(response))
        self.assertIn("systemMessage", response)

    def test_missing_allowlist_is_fail_open_with_warning(self) -> None:
        missing = GUARD_PATH.with_name("definitely_missing_allowlist.tsv")
        response = GUARD.evaluate_event(
            event(r"Write-Output 'a\nb' > probe.txt"),
            allowlist_path=missing,
        )
        self.assertIsInstance(response, dict)
        self.assertIsNone(decision(response))
        self.assertIn("systemMessage", response)


class GuardProcessTests(unittest.TestCase):
    def run_guard(self, stdin_text: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-I", "-B", str(GUARD_PATH)],
            input=stdin_text,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

    def test_malformed_json_is_fail_open_and_silent(self) -> None:
        completed = self.run_guard("{malformed")
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "")

    def test_denial_uses_official_structured_shape(self) -> None:
        completed = self.run_guard(
            json.dumps(event(r"Write-Output 'a\nb' > probe.txt"))
        )
        self.assertEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        specific = payload["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "PreToolUse")
        self.assertEqual(specific["permissionDecision"], "deny")

    def test_windows_handler_uses_quote_free_git_root_wrapper(self) -> None:
        handler = windows_handler()
        self.assertNotIn('"', handler)
        self.assertTrue(handler.startswith("cmd.exe /d /q /c powershell.exe "))
        self.assertIn(
            "-Command . (Join-Path (git rev-parse --show-toplevel) ",
            handler,
        )
        self.assertTrue(
            handler.endswith("'.codex/hooks/guard_backslash_windows.ps1')")
        )
        self.assertTrue(WINDOWS_WRAPPER_PATH.is_file())

    @unittest.skipUnless(sys.platform == "win32", "Windows hook launcher contract")
    def test_windows_handler_survives_codex_outer_quotes(self) -> None:
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        command_line = f'{comspec} /d /s /c "{windows_handler()}"'
        for cwd in (GUARD_PATH.parents[2], GUARD_PATH.parents[2] / "scripts"):
            with self.subTest(cwd=cwd):
                completed = subprocess.run(
                    command_line,
                    cwd=cwd,
                    input=json.dumps(event(r"Write-Output '한글 a\nb' > probe.txt")),
                    text=True,
                    encoding="utf-8",
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                payload = json.loads(completed.stdout)
                self.assertEqual(decision(payload), "deny")


if __name__ == "__main__":
    unittest.main(verbosity=2)
