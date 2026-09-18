#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import smoke_module


class SmokeModuleParserTests(unittest.TestCase):
    def fixture(self, text: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "tool_smoke.bat"
        path.write_text(text, encoding="ascii")
        return path

    def test_known_grammar_rewrites_outer_and_child_python(self) -> None:
        path = self.fixture(
            "@echo off\n"
            "REM\n"
            "python scripts\\runlog.py --name !TL_LOGNAME! --note \"hello world\"\n"
            "python scripts\\runlog.py --name !TL_LOGNAME! -- python scripts\\probe.py\n"
            "timeout /t 15 /nobreak\n"
            "if errorlevel 1 echo [WARN] continue\n"
            "goto DONE\n"
            ":DONE\n"
            "if not defined TL_NOPAUSE pause\n"
            "exit /b 0\n"
        )
        actions = smoke_module.parse_smoke_module(path, log_name="fixture")
        self.assertEqual([action.kind for action in actions], ["run", "run", "sleep"])
        self.assertEqual(actions[0].argv[0], sys.executable)
        self.assertIn("fixture", actions[0].argv)
        separator = actions[1].argv.index("--")
        self.assertEqual(actions[1].argv[separator + 1], sys.executable)
        self.assertEqual(actions[2].seconds, 15)

    def test_unknown_executable_statement_is_rejected(self) -> None:
        path = self.fixture(
            "@echo off\n"
            "python scripts\\runlog.py --name !TL_LOGNAME! --note \"ok\"\n"
            "curl https://example.invalid\n"
        )
        with self.assertRaisesRegex(ValueError, "unsupported BAT statement"):
            smoke_module.parse_smoke_module(path)

    def test_canonical_module_is_parseable_without_execution(self) -> None:
        actions = smoke_module.parse_smoke_module()
        self.assertEqual(sum(action.kind == "run" for action in actions), 95)
        self.assertEqual(sum(action.kind == "sleep" for action in actions), 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
