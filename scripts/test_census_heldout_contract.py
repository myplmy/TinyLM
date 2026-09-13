#!/usr/bin/env python3
"""GPU-free regression tests for the held-out census persistence contract."""
from __future__ import annotations

import datetime as dt
import io
import importlib.util
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().with_name("census_heldout_discrimination.py")
SPEC = importlib.util.spec_from_file_location("census_contract_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_pairs_keep_discordance_and_family_ci() -> None:
    per_ok = {"a": [True, False, True], "b": [False, False, True]}

    def fake_ci(ok_a, ok_b, relations):
        assert ok_a == [True, False, True]
        assert ok_b == [False, False, True]
        assert relations == ["r1", "r1", "r2"]
        return 0.05, 0.25, 2

    rows = MODULE.pair_records(per_ok, ["a", "b"], ["r1", "r1", "r2"], 3,
                               ci_fn=fake_ci)
    assert rows == [{
        "a": "a", "b": "b", "a_only": 1, "b_only": 0, "discordant": 1,
        "family_count": 2, "family_ci95": [0.05, 0.25],
        "family_verdict": "a_better",
    }]


def test_family_ci_withheld_is_explicit() -> None:
    rows = MODULE.pair_records(
        {"a": [True], "b": [False]}, ["a", "b"], ["only"], 1,
        ci_fn=lambda *_: (None, None, 1),
    )
    assert rows[0]["family_ci95"] is None
    assert rows[0]["family_verdict"] == "withheld"


def test_automatic_log_path_follows_output_and_never_overwrites() -> None:
    started = dt.datetime(2026, 9, 14, 4, 30, 12, tzinfo=dt.timezone.utc)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "heldout.v3.0.json"
        first = MODULE.automatic_log_path(["--out", str(out)], started)
        assert first.parent == out.parent
        assert first.name == "20260914043012_heldout.v3.0.log"
        first.write_text("old evidence", encoding="utf-8")
        second = MODULE.automatic_log_path([f"--out={out}"], started)
        assert second.name == "20260914043012_heldout.v3.0_2.log"
        assert first.read_text(encoding="utf-8") == "old evidence"


def test_logged_main_mirrors_console_and_records_exit() -> None:
    original_main = MODULE.main
    console_out, console_err = io.StringIO(), io.StringIO()
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "normal.log"

        def fake_main():
            print("normal stdout")
            print("normal stderr", file=sys.stderr)
            return 0

        MODULE.main = fake_main
        try:
            with redirect_stdout(console_out), redirect_stderr(console_err):
                code = MODULE.logged_main([], log_path=log)
        finally:
            MODULE.main = original_main
        saved = log.read_text(encoding="utf-8")
    assert code == 0
    assert "normal stdout" in console_out.getvalue()
    assert "normal stderr" in console_err.getvalue()
    assert "normal stdout" in saved and "normal stderr" in saved
    assert "[census_heldout_discrimination] exit_code=0" in saved
    assert "[census_heldout_discrimination] ended=" in saved


def test_logged_main_records_traceback_and_failure_exit() -> None:
    original_main = MODULE.main
    console_err = io.StringIO()
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "failure.log"

        def failing_main():
            raise RuntimeError("census boom")

        MODULE.main = failing_main
        try:
            with redirect_stderr(console_err):
                code = MODULE.logged_main([], log_path=log)
        finally:
            MODULE.main = original_main
        saved = log.read_text(encoding="utf-8")
    assert code == 1
    assert "RuntimeError: census boom" in console_err.getvalue()
    assert "RuntimeError: census boom" in saved
    assert "[census_heldout_discrimination] exit_code=1" in saved


def main() -> int:
    tests = [
        test_pairs_keep_discordance_and_family_ci,
        test_family_ci_withheld_is_explicit,
        test_automatic_log_path_follows_output_and_never_overwrites,
        test_logged_main_mirrors_console_and_records_exit,
        test_logged_main_records_traceback_and_failure_exit,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"SUMMARY {len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
