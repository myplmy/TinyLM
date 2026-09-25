#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import runlog
import summarize_smoke

ROOT = Path(__file__).resolve().parent.parent


class SmokeEntrypointExitTests(unittest.TestCase):
    def test_smoke_start_note_forces_a_fresh_log(self) -> None:
        self.assertTrue(
            runlog._is_smoke_session_start(
                "smoke", [runlog.SMOKE_SESSION_START]
            )
        )
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            first = runlog._stamped_path(
                out, "smoke", "abcdef0", None, 30, force_new=True
            )
            first.write_text("old\n", encoding="utf-8")
            second = runlog._stamped_path(
                out, "smoke", "abcdef0", None, 30, force_new=True
            )
        self.assertNotEqual(first, second)

    def test_commit_banner_distinguishes_clean_and_dirty(self) -> None:
        import contextlib
        import io

        cases = (
            ((0, 0), "INFO 작업트리 clean", False),
            ((2, 0), "INFO 비코드 변경만", False),
            ((2, 1), "⚠️ 실행 코드 미커밋", True),
            ((None, None), "⚠️ 작업트리 상태 확인 불가", True),
        )
        for state, phrase, expect_warning in cases:
            with self.subTest(state=state), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "smoke.txt"
                with contextlib.redirect_stdout(io.StringIO()):
                    runlog._header(path, "abcdef0", state)
                body = path.read_text(encoding="utf-8")
                self.assertIn(phrase, body)
                self.assertEqual("⚠️" in body, expect_warning)

    def test_root_shell_dirty_counts_as_code(self) -> None:
        from types import SimpleNamespace
        from unittest.mock import patch

        replies = (
            SimpleNamespace(returncode=0, stdout="abcdef0" + chr(10)),
            SimpleNamespace(
                returncode=0,
                stdout="?? run_P100_Stage0bW_saved_answer_triage.sh"
                + chr(10) + "?? test_result/example.txt" + chr(10),
            ),
        )
        with patch("subprocess.run", side_effect=replies):
            sha, counts = runlog._git_state()
        self.assertEqual(sha, "abcdef0")
        self.assertEqual(counts, (2, 1))
    def test_summary_isolates_last_accidentally_appended_session(self) -> None:
        text = (
            f"{summarize_smoke.SESSION_MARK}\nold-arm\n"
            f"{summarize_smoke.SESSION_MARK}\nnew-arm\n"
        )
        latest, count = summarize_smoke.latest_session(text)
        self.assertEqual(count, 2)
        self.assertNotIn("old-arm", latest)
        self.assertIn("new-arm", latest)

    def test_windows_wrapper_returns_summary_failure(self) -> None:
        text = (ROOT / "run_smoke_check.bat").read_text(encoding="ascii")
        summary = (
            "python scripts\\runlog.py --name smoke -- "
            "python scripts\\summarize_smoke.py\n"
            "set TL_SUMMARY_RC=!errorlevel!"
        )
        self.assertIn(summary, text)
        self.assertIn(
            'if not "!TL_SUMMARY_RC!"=="0" exit /b !TL_SUMMARY_RC!',
            text,
        )
        self.assertNotIn("set TL_OUTDIR=\nif not defined TL_NOPAUSE pause\nexit /b 0", text)

    def test_posix_wrapper_returns_summary_failure(self) -> None:
        text = (ROOT / "run_smoke_check.sh").read_text(encoding="utf-8")
        self.assertIn("summary_rc=$?", text)
        self.assertIn('exit "$summary_rc"', text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
