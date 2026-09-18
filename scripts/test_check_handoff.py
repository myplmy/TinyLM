#!/usr/bin/env python3
"""Regression checks for the shared handoff linter helpers."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().with_name("check_handoff.py")
SPEC = importlib.util.spec_from_file_location("check_handoff_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

QUEUE_MODULE_PATH = Path(__file__).resolve().with_name("handoff_queue.py")
QUEUE_SPEC = importlib.util.spec_from_file_location("handoff_queue_under_test", QUEUE_MODULE_PATH)
assert QUEUE_SPEC and QUEUE_SPEC.loader
QUEUE_MODULE = importlib.util.module_from_spec(QUEUE_SPEC)
sys.modules[QUEUE_SPEC.name] = QUEUE_MODULE
QUEUE_SPEC.loader.exec_module(QUEUE_MODULE)


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


def test_completed_transfer_lines_are_historical_references() -> None:
    lines = """## 7. next
| batch |
|---|
| `run_live.bat` |
### 7.1 이전 큐 제외·완료 이관
| previous batch |
|---|
| `run_deleted_after_completion.bat` |
## 8. commit
""".splitlines()
    historical = MODULE.historical_queue_line_numbers(lines)
    assert 4 not in historical
    assert 8 in historical


def test_empty_recommendation_table_is_structurally_valid() -> None:
    lines = """## 7. next
| 순 | id | 실험 | 배치 파일 | ⚙ | 누적 | 인벤토리 | 실행상태 | 선결 | 근거 |
|---:|---:|---|---|---:|---:|---|---|---|---|

현재 실행 가능한 실험은 없다.
""".splitlines()
    assert MODULE.queue_table_header_index(lines) == 1


def test_inherited_reason_boilerplate_is_idempotent() -> None:
    core = "RMS 상단을 닫는다"
    once = QUEUE_MODULE.inherited_reason(core)
    twice = QUEUE_MODULE.inherited_reason(once)
    already_duplicated = QUEUE_MODULE.inherited_reason(
        "직전 핸드오프 계승; 직전 핸드오프 계승; RMS 상단을 닫는다; "
        "현재 과학적 순서 재검증 필요; 현재 과학적 순서 재검증 필요"
    )
    expected = "직전 핸드오프 계승; RMS 상단을 닫는다; 현재 과학적 순서 재검증 필요"
    assert once == expected
    assert twice == expected
    assert already_duplicated == expected


def main() -> int:
    tests = [
        test_completed_transfer_is_not_live_queue,
        test_section_7_without_history_is_preserved,
        test_operational_launcher_is_not_counted_as_experiment_batch,
        test_completed_transfer_lines_are_historical_references,
        test_empty_recommendation_table_is_structurally_valid,
        test_inherited_reason_boilerplate_is_idempotent,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"SUMMARY {len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
