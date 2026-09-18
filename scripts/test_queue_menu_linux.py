#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path, PureWindowsPath

import check_shell_entrypoints as shell_check
import queue_menu_linux as linux_queue


def row(batch: str):
    return {
        "prio": "0",
        "prio_n": 0,
        "plan": "-",
        "batch": batch,
        "gpu": "N",
        "hours": "0.1",
        "hours_n": 0.1,
        "alone": "N",
        "watch": "N",
        "note": "fixture",
        "line": 1,
        "exists": True,
        "done": False,
    }


class LinuxQueueTests(unittest.TestCase):
    def test_same_stem_mapping(self) -> None:
        self.assertEqual(
            linux_queue.shell_name("run_smoke_check.bat"),
            "run_smoke_check.sh",
        )
        with self.assertRaises(ValueError):
            linux_queue.shell_name("run_smoke_check.sh")

    def test_only_existing_shell_companion_is_runnable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "run_smoke_check.sh").write_text("#!/bin/sh\n", encoding="ascii")
            rows = linux_queue.with_shell_state(
                [row("run_smoke_check.bat"), row("run_P999_Stage0.bat")],
                root=root,
            )
            self.assertEqual(
                [item["shell_batch"] for item in linux_queue.available(rows)],
                ["run_smoke_check.sh"],
            )

    def test_done_canonical_batch_is_not_runnable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "run_P999_Stage0.sh").write_text("#!/bin/sh\n", encoding="ascii")
            finished = row("run_P999_Stage0.bat")
            finished["exists"] = False
            finished["done"] = True
            rows = linux_queue.with_shell_state([finished], root=root)
            self.assertEqual(linux_queue.available(rows), [])

    def test_windows_path_is_converted_for_git_bash(self) -> None:
        converted = shell_check.to_bash_path(
            PureWindowsPath(r"C:\\repo\\run_queue.sh"), windows=True
        )
        self.assertEqual(converted, "/c/repo/run_queue.sh")

    def test_generated_plan_uses_shell_and_stops_on_smoke(self) -> None:
        chosen = [
            {
                **row("run_smoke_check.bat"),
                "shell_batch": "run_smoke_check.sh",
                "shell_exists": True,
            },
            {
                **row("run_P999_Stage0.bat"),
                "shell_batch": "run_P999_Stage0.sh",
                "shell_exists": True,
            },
        ]
        plan = linux_queue.render_plan(chosen)
        self.assertIn("./run_smoke_check.sh", plan)
        self.assertIn("smoke check failed", plan)
        self.assertIn("./run_P999_Stage0.sh", plan)
        self.assertIn("returned an error - continuing", plan)
        self.assertNotIn(".bat", plan)
        self.assertIn("printf '%s\\n' '[STOP]", plan)
        bash = shell_check.find_bash()
        if bash is None:
            self.skipTest("bash is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "plan.sh"
            path.write_text(plan, encoding="utf-8", newline="\n")
            completed = subprocess.run(
                [bash, "-n", shell_check.to_bash_path(path)], capture_output=True, text=True, check=False
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
