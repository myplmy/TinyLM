"""Synthetic Git-scope regression; no repository inventory, model or GPU."""
from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runlog


class GitScopeTests(unittest.TestCase):
    def test_default_command_is_unchanged(self):
        self.assertEqual(runlog._git_status_command({}),
                         ["git", "status", "--porcelain"])

    def test_safe_scope_excludes_protected_sources_before_git_runs(self):
        command = runlog._git_status_command({"TL_RUNLOG_GIT_SCOPE": "codex-safe"})
        self.assertEqual(command[:5], ["git", "status", "--porcelain", "--", "."])
        for item in ("datasets/TinyDataset", ".claude", "CLAUDE.md",
                     "ai_dev_tool/[0-8]*", ".aws", ".env*"):
            self.assertIn(":(exclude)" + item, command)

    def test_invalid_scope_fails_before_any_subprocess(self):
        with patch.dict(os.environ, {"TL_RUNLOG_GIT_SCOPE": "typo"}), \
                patch("subprocess.run") as call:
            with self.assertRaises(ValueError):
                runlog._git_state()
            call.assert_not_called()

    def test_scoped_state_counts_only_returned_records(self):
        outputs = [SimpleNamespace(returncode=0, stdout="abc1234\n"),
                   SimpleNamespace(returncode=0, stdout=" M scripts/a.py\n?? docs/b.md\n")]
        with patch.dict(os.environ, {"TL_RUNLOG_GIT_SCOPE": "codex-safe"}), \
                patch("subprocess.run", side_effect=outputs) as call:
            self.assertEqual(runlog._git_state(), ("abc1234", (2, 1)))
            self.assertIn(":(exclude)datasets/TinyDataset", call.call_args_list[1].args[0])

    def test_scoped_banner_cannot_claim_whole_tree_clean(self):
        with tempfile.TemporaryDirectory(prefix="tinylm-runlog-scope-") as tmp, \
                patch.dict(os.environ, {"TL_RUNLOG_GIT_SCOPE": "codex-safe"}), \
                contextlib.redirect_stdout(io.StringIO()):
            destination = Path(tmp) / "log.txt"
            runlog._header(destination, "abc1234", (0, 0))
            text = destination.read_text(encoding="utf-8")
            self.assertIn("허용 경로만 조회", text)
            self.assertNotIn("작업트리 clean —", text)
            self.assertIn("전체 작업트리 상태는 미확인", text)

    def test_scoped_noncode_changes_do_not_claim_code_commit_identity(self):
        with tempfile.TemporaryDirectory(prefix="tinylm-runlog-scope-") as tmp, \
                patch.dict(os.environ, {"TL_RUNLOG_GIT_SCOPE": "codex-safe"}), \
                contextlib.redirect_stdout(io.StringIO()):
            destination = Path(tmp) / "log.txt"
            runlog._header(destination, "abc1234", (3, 0))
            text = destination.read_text(encoding="utf-8")
            self.assertNotIn("코드는 이 커밋 그대로", text)
            self.assertIn("scoped-dirty 3개", text)


if __name__ == "__main__":
    unittest.main()
