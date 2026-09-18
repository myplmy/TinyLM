#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class SmokeEntrypointExitTests(unittest.TestCase):
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
