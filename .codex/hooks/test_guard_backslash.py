#!/usr/bin/env python3
"""Mock tests for the TinyLM Codex backslash PreToolUse guard."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

GUARD_PATH = Path(__file__).resolve().with_name("guard_backslash.py")
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
