#!/usr/bin/env python3
"""Regression checks for the shared handoff linter helpers."""
from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().with_name("check_handoff.py")
SPEC = importlib.util.spec_from_file_location("check_handoff_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_completed_transfer_is_not_live_queue() -> None:
    lines = """## 7. next
| batch |
|---|
| `run_live.bat` |
### 7.1 previous completion
| previous batch |
|---|
| `run_done.bat` |
## 8. commit
""".splitlines()
    segment = MODULE.current_queue_segment(lines)
    assert "run_live.bat" in segment
    assert "run_done.bat" not in segment


def test_section_7_without_history_is_preserved() -> None:
    lines = """## 7. next
| batch |
|---|
| `run_only.bat` |
## 8. commit
""".splitlines()
    segment = MODULE.current_queue_segment(lines)
    assert "run_only.bat" in segment


def test_operational_launcher_is_not_counted_as_experiment_batch() -> None:
    segment = """## 7. next
| batch |
|---|
| `run_live.bat` |
Use `run_queue.bat` to select it.
"""
    names = MODULE.current_queue_batch_names(segment, {"run_live.bat"})
    assert names == {"run_live.bat"}


def main() -> int:
    tests = [
        test_completed_transfer_is_not_live_queue,
        test_section_7_without_history_is_preserved,
        test_operational_launcher_is_not_counted_as_experiment_batch,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"SUMMARY {len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
