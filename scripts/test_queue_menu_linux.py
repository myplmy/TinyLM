#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path, PureWindowsPath
from unittest import mock

import check_shell_entrypoints as shell_check
import queue_menu_linux as linux_queue
import queue_menu as shared_queue


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
        "negative_rc": "",
        "negative_rcs": set(),
    }


class LinuxQueueTests(unittest.TestCase):
    def test_shared_ids_delegate_to_linux_menu_on_posix(self) -> None:
        rows = [row("run_fixture_Stage0.sh")]
        with mock.patch.object(shared_queue.os, "name", "posix"), mock.patch.object(
            linux_queue, "with_shell_state", return_value=[{"linux": True}]
        ) as state, mock.patch.object(linux_queue, "cmd_ids", return_value=0) as ids:
            rc = shared_queue.cmd_platform_ids(rows, ["run_fixture_Stage0.sh"])
            self.assertEqual(rc, 0)
            state.assert_called_once_with(rows)
            ids.assert_called_once_with([{"linux": True}], ["run_fixture_Stage0.sh"])

    def test_experiment_shell_requires_runlog_contract(self) -> None:
        path = Path("run_P099_fixture.sh")
        missing = b"#!/usr/bin/env bash\nexec python scripts/diag_fixture.py\n"
        self.assertIn(
            "does not invoke scripts/runlog.py",
            shell_check.experiment_log_contract_errors(path, missing),
        )
        wrapped = (
            b"#!/usr/bin/env bash\n"
            b"exec python scripts/runlog.py --name P099_fixture -- "
            b"python scripts/diag_fixture.py\n"
        )
        self.assertEqual(
            shell_check.experiment_log_contract_errors(path, wrapped), []
        )

    def test_same_stem_mapping(self) -> None:
        self.assertEqual(
            linux_queue.shell_name("run_smoke_check.bat"),
            "run_smoke_check.sh",
        )
        self.assertEqual(
            linux_queue.shell_name("run_fixture_Stage0.sh"),
            "run_fixture_Stage0.sh",
        )
        with self.assertRaises(ValueError):
            linux_queue.shell_name("run_smoke_check.ps1")

    def test_only_existing_shell_companion_is_runnable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "run_smoke_check.sh").write_text("#!/bin/sh\n", encoding="ascii")
            rows = linux_queue.with_shell_state(
                [row("run_smoke_check.bat"), row("run_fixture_Stage0.bat")],
                root=root,
            )
            self.assertEqual(
                [item["shell_batch"] for item in linux_queue.available(rows)],
                ["run_smoke_check.sh"],
            )

    def test_done_canonical_batch_is_not_runnable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "run_fixture_Stage0.sh").write_text("#!/bin/sh\n", encoding="ascii")
            finished = row("run_fixture_Stage0.bat")
            finished["exists"] = False
            finished["done"] = True
            rows = linux_queue.with_shell_state([finished], root=root)
            self.assertEqual(linux_queue.available(rows), [])
            output = StringIO()
            with redirect_stdout(output):
                linux_queue._display_rows(rows, [])
            self.assertIn("Completed (-done)", output.getvalue())
            self.assertNotIn("Unavailable Linux/WSL", output.getvalue())

    def test_cancelled_shell_is_not_a_live_queue_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "run_P092_Stage3W-cancel.sh").write_text(
                "#!/usr/bin/env bash" + chr(10), encoding="ascii"
            )
            with mock.patch.object(linux_queue, "ROOT", root), mock.patch.object(
                linux_queue, "REQUIRED_COMMON", set()
            ):
                self.assertEqual(linux_queue.cmd_audit([], []), 0)

    def test_native_shell_row_is_runnable_without_bat(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "run_fixture_Stage0.sh").write_text("#!/bin/sh\n", encoding="ascii")
            rows = linux_queue.with_shell_state([row("run_fixture_Stage0.sh")], root=root)
            self.assertEqual(
                [item["shell_batch"] for item in linux_queue.available(rows)],
                ["run_fixture_Stage0.sh"],
            )

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
                **row("run_fixture_Stage0.bat"),
                "shell_batch": "run_fixture_Stage0.sh",
                "shell_exists": True,
            },
        ]
        plan = linux_queue.render_plan(chosen)
        self.assertIn("./run_smoke_check.sh", plan)
        self.assertIn("smoke check failed", plan)
        self.assertIn("./run_fixture_Stage0.sh", plan)
        self.assertIn("continuing to collect remaining results", plan)
        self.assertIn("tl_failures=$((tl_failures + 1))", plan)
        self.assertIn("exit 4", plan)
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

    def test_generated_plan_runs_all_gates_and_returns_aggregate_failure(self) -> None:
        chosen = [
            {
                **row("run_gate_one.sh"),
                "shell_batch": "run_gate_one.sh",
                "shell_exists": True,
            },
            {
                **row("run_gate_two.sh"),
                "shell_batch": "run_gate_two.sh",
                "shell_exists": True,
            },
        ]
        bash = shell_check.find_bash()
        if bash is None:
            self.skipTest("bash is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runs = root / "runs"
            runs.mkdir()
            first = root / "run_gate_one.sh"
            second = root / "run_gate_two.sh"
            first.write_text(
                "#!/usr/bin/env bash\nprintf '%s\\n' gate-one-ran\nexit 7\n",
                encoding="ascii",
            )
            second.write_text(
                "#!/usr/bin/env bash\nprintf '%s\\n' gate-two-ran\nexit 0\n",
                encoding="ascii",
            )
            first.chmod(0o755)
            second.chmod(0o755)
            plan_path = runs / "_queue_plan.sh"
            plan_text = linux_queue.render_plan(chosen).replace("sleep 15", "sleep 0")
            plan_path.write_text(
                plan_text, encoding="utf-8", newline="\n"
            )
            completed = subprocess.run(
                [bash, str(plan_path)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 4, completed.stderr)
        self.assertIn("gate-one-ran", completed.stdout)
        self.assertIn("gate-two-ran", completed.stdout)
        self.assertIn("selected entry failures: 1", completed.stderr)
        self.assertIn("run_gate_one.sh", completed.stderr)

    def test_selection_contains_smoke_accepts_id_and_name(self) -> None:
        rows = [
            {
                **row("run_smoke_check.sh"),
                "shell_batch": "run_smoke_check.sh",
                "shell_exists": True,
            },
            {
                **row("run_gate_one.sh"),
                "shell_batch": "run_gate_one.sh",
                "shell_exists": True,
            },
        ]
        self.assertTrue(linux_queue.selection_contains_smoke(rows, "0 1"))
        self.assertTrue(linux_queue.selection_contains_smoke(rows, "smoke_check"))
        self.assertFalse(linux_queue.selection_contains_smoke(rows, "1"))

    def test_declared_negative_is_not_execution_failure(self) -> None:
        chosen = [
            {
                **row("run_gate_negative.sh"),
                "shell_batch": "run_gate_negative.sh",
                "shell_exists": True,
                "negative_rc": "8",
                "negative_rcs": {8},
            },
            {
                **row("run_gate_pass.sh"),
                "shell_batch": "run_gate_pass.sh",
                "shell_exists": True,
            },
        ]
        bash = shell_check.find_bash()
        if bash is None:
            self.skipTest("bash is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runs = root / "runs"
            runs.mkdir()
            negative = root / "run_gate_negative.sh"
            passed = root / "run_gate_pass.sh"
            negative.write_text("#!/usr/bin/env bash\nexit 8\n", encoding="ascii")
            passed.write_text(
                "#!/usr/bin/env bash\nprintf '%s\\n' pass-ran\nexit 0\n",
                encoding="ascii",
            )
            negative.chmod(0o755)
            passed.chmod(0o755)
            plan_path = runs / "_queue_plan.sh"
            plan_path.write_text(
                linux_queue.render_plan(chosen).replace("sleep 15", "sleep 0"),
                encoding="utf-8",
                newline="\n",
            )
            completed = subprocess.run(
                [bash, str(plan_path)], cwd=root, capture_output=True,
                text=True, check=False,
            )
        self.assertEqual(completed.returncode, 8, completed.stderr)
        self.assertIn("pass-ran", completed.stdout)
        self.assertIn("GATE NEGATIVE", completed.stderr)
        self.assertIn("not an execution failure", completed.stderr)
        self.assertNotIn("selected entry failures", completed.stderr)

    def test_execution_failure_takes_precedence_over_declared_negative(self) -> None:
        chosen = [
            {
                **row("run_gate_negative.sh"),
                "shell_batch": "run_gate_negative.sh",
                "shell_exists": True,
                "negative_rc": "8",
                "negative_rcs": {8},
            },
            {
                **row("run_gate_broken.sh"),
                "shell_batch": "run_gate_broken.sh",
                "shell_exists": True,
            },
        ]
        bash = shell_check.find_bash()
        if bash is None:
            self.skipTest("bash is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runs = root / "runs"
            runs.mkdir()
            negative = root / "run_gate_negative.sh"
            broken = root / "run_gate_broken.sh"
            negative.write_text("#!/usr/bin/env bash\nexit 8\n", encoding="ascii")
            broken.write_text("#!/usr/bin/env bash\nexit 7\n", encoding="ascii")
            negative.chmod(0o755)
            broken.chmod(0o755)
            plan_path = runs / "_queue_plan.sh"
            plan_path.write_text(
                linux_queue.render_plan(chosen).replace("sleep 15", "sleep 0"),
                encoding="utf-8",
                newline="\n",
            )
            completed = subprocess.run(
                [bash, str(plan_path)], cwd=root, capture_output=True,
                text=True, check=False,
            )
        self.assertEqual(completed.returncode, 4, completed.stderr)
        self.assertIn("selected entry failures: 1", completed.stderr)
        self.assertIn("valid gate-negative results: run_gate_negative.sh", completed.stderr)
        self.assertIn("run_gate_broken.sh", completed.stderr)

    def test_smoke_collect_and_warn_policies_are_explicit(self) -> None:
        chosen = [
            {
                **row("run_smoke_check.sh"),
                "shell_batch": "run_smoke_check.sh",
                "shell_exists": True,
            }
        ]
        collect = linux_queue.render_plan(chosen, smoke_policy="collect")
        warn = linux_queue.render_plan(chosen, smoke_policy="warn")
        self.assertNotIn("[STOP] smoke check failed", collect)
        self.assertIn("tl_failures=$((tl_failures + 1))", collect)
        self.assertIn("user-selected warn policy", warn)
        self.assertIn("tl_warnings=$((tl_warnings + 1))", warn)
        self.assertNotIn("tl_failures=$((tl_failures + 1))", warn)

    def test_smoke_policy_controls_failure_and_continuation(self) -> None:
        chosen = [
            {
                **row("run_smoke_check.sh"),
                "shell_batch": "run_smoke_check.sh",
                "shell_exists": True,
            },
            {
                **row("run_gate_one.sh"),
                "shell_batch": "run_gate_one.sh",
                "shell_exists": True,
            },
        ]
        bash = shell_check.find_bash()
        if bash is None:
            self.skipTest("bash is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runs = root / "runs"
            runs.mkdir()
            smoke = root / "run_smoke_check.sh"
            gate = root / "run_gate_one.sh"
            smoke.write_text("#!/usr/bin/env bash\nexit 9\n", encoding="ascii")
            gate.write_text(
                "#!/usr/bin/env bash\nprintf '%s\\n' gate-ran\nexit 0\n",
                encoding="ascii",
            )
            smoke.chmod(0o755)
            gate.chmod(0o755)
            completed = {}
            for policy in linux_queue.SMOKE_POLICIES:
                plan_path = runs / f"_queue_plan_{policy}.sh"
                plan_text = linux_queue.render_plan(
                    chosen, smoke_policy=policy
                ).replace("sleep 15", "sleep 0")
                plan_path.write_text(plan_text, encoding="utf-8", newline="\n")
                completed[policy] = subprocess.run(
                    [bash, str(plan_path)],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
        self.assertEqual(completed["stop"].returncode, 3)
        self.assertNotIn("gate-ran", completed["stop"].stdout)
        self.assertEqual(completed["collect"].returncode, 4)
        self.assertIn("gate-ran", completed["collect"].stdout)
        self.assertEqual(completed["warn"].returncode, 0)
        self.assertIn("gate-ran", completed["warn"].stdout)
        self.assertIn("user-accepted warning", completed["warn"].stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
