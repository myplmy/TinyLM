#!/usr/bin/env python3
"""GPU/data-free regressions for fetch logging and held-out version discovery."""
from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().with_name("fetch_bench_data.py")
SPEC = importlib.util.spec_from_file_location("fetch_bench_logging_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_log_argument_forms() -> None:
    assert MODULE.requested_log_path(["--log", "a.txt"]) == "a.txt"
    assert MODULE.requested_log_path(["--log=b.txt"]) == "b.txt"
    assert MODULE.requested_log_path(["--list"]) is None


def test_utf8_log_mirrors_console_text() -> None:
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "fetch.log"
        with MODULE.execution_log(path):
            print("한글 오류 원문")
        text = path.read_text(encoding="utf-8")
        assert "[fetch_bench_data] started=" in text
        assert "한글 오류 원문" in text
        assert "[fetch_bench_data] ended=" in text


def test_heldout_dirs_ignore_non_numeric_archive_names() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        for name in ("held-out_v2.9", "held-out_v2.10", "held-out_v3.0",
                     "held-out_v1_archive"):
            (root / name).mkdir()
        (root / "held-out_vnotes").write_text("history", encoding="utf-8")

        found = MODULE.heldout_dirs(root)

        assert list(found) == ["2.9", "2.10", "3.0"]
        assert found["3.0"] == root / "held-out_v3.0"


def main() -> int:
    tests = [
        test_log_argument_forms,
        test_utf8_log_mirrors_console_text,
        test_heldout_dirs_ignore_non_numeric_archive_names,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"SUMMARY {len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
