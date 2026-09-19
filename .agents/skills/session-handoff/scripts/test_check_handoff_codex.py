#!/usr/bin/env python3
"""Isolated regression fixtures for the TinyLM Codex handoff contract."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

CHECKER_PATH = Path(__file__).resolve().with_name("check_handoff_codex.py")
SPEC = importlib.util.spec_from_file_location("tinylm_handoff_checker", CHECKER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {CHECKER_PATH}")
CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKER
SPEC.loader.exec_module(CHECKER)


def previous_text(batch: str = "run_P999_Stage1_fixture.bat") -> str:
    return f"""# prior

## 7. 다음 권장 실험 순서

| 순 | id | 실험 | 배치 파일 | ⚙ | 누적 | 선결 | 근거 |
|---:|---:|---|---|---:|---:|---|---|
| 1 | 4 | P999 Stage1 | `{batch}` | 1.0 | 1.0 | 없음 | fixture |
"""


def current_text(previous: str, *, queue_row: str, smoke: str = "NOT_REQUIRED(문서 전용 변경)") -> str:
    return f"""# HANDOFF 2099-01-01 00:01 — fixture

- **이전**: [`{previous}`]({previous})
- STATIC_ONLY / E2E_NOT_RUN / NOT_RUN

## 0. 사용자 지시 1건 — 원문과 처리

| # | 사용자가 지시한 것 | AI 가 판단한 목적 | 그래서 필요했던 작업 | 실제로 한 것 | 결과 |
|---|---|---|---|---|---|
| 1 | fixture | validate | check | checked | 완료 |

## 1. 가장 중요한 것 셋

fixture

## 2. 무엇을 했나

fixture

## 3. 무엇이 바뀌었나 — 코드·도구

| 산출물 | 필요 여부 | 실제 diff | 미갱신 사유 |
|---|---|---|---|
| 결과 | 불필요 | 없음 | fixture only |

## 4. 조심할 것

| 항목 | 상태 | 근거 | 사용자 요청 반영 |
|---|---|---|---|
| `run_smoke_check.bat` | `{smoke}` | fixture | 요청 없음 |

### 4.2 미해결 검사·판정

| 검사 | 정확한 대상 | 증거와 상태 | 운영 영향 | 권장 조치 | 대안 | 승인 주체 |
|---|---|---|---|---|---|---|

## 5. 확보한 수치

없음

## 6. 열린 질문

없음

## 7. 다음 권장 실험 순서

| 순 | id | 실험 | 배치 파일 | ⚙ | 누적 | 인벤토리 | 실행상태 | 선결 | 근거 |
|---:|---:|---|---|---:|---:|---|---|---|---|
{queue_row}

> ★**시간 미달 사유**: fixture queue는 계약 검사 한 건뿐이며 중복 실험으로 48시간을 채우지 않는다.

### 7.1 이전 큐 제외·완료 이관

| 이전 배치 | 처리 | 근거 |
|---|---|---|

## 6b. 사용자에게 부탁하는 것

| 대상 | 정확한 위치 | 근거 | 사용자가 할 행동 | 완료 신호 | AI 후속 처리 |
|---|---|---|---|---|---|
| `-done` 삭제 | 저장소 루트 | 삭제 후보 없음 | 삭제하지 않음 | 변경 없음 | 재감사 |

## 8. 커밋 메시지

### 제목
```
fixture title
```

### 본문
```
fixture body
```

## 9. compact 프롬프트

수동 보조

## 10. 세션 시작 프롬프트

- **열린 WIP 상태**: `없음`
- **정확한 WIP / 첫 미완료**: —
- **첫 행동과 선결**: 새 요청 시작
- **승인 전 금지**: 없음

## 11. 참조 치트시트

fixture
"""


class HandoffContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.handoff = Path(self.temp.name)
        self.old_root = CHECKER.REPO_ROOT, CHECKER.HANDOFF_ROOT
        CHECKER.REPO_ROOT = self.handoff.parent
        CHECKER.HANDOFF_ROOT = self.handoff
        self.previous = self.handoff / "209901010000_HANDOFF.md"
        self.previous.write_text(previous_text(), encoding="utf-8")
        self.current = self.handoff / "209901010001_HANDOFF.md"

    def tearDown(self) -> None:
        CHECKER.REPO_ROOT, CHECKER.HANDOFF_ROOT = self.old_root
        self.temp.cleanup()

    def write(self, text: str) -> list[str]:
        self.current.write_text(text, encoding="utf-8")
        return CHECKER.validate(self.current).errors

    @property
    def carried_row(self) -> str:
        return (
            "| 1 | 4 | P999 Stage1 | `run_P999_Stage1_fixture.bat` | 1.0 | 1.0 | "
            "PRESENT | REVALIDATE | 재검증 | 계승 |"
        )

    def test_valid_current_handoff_passes(self) -> None:
        errors = self.write(current_text(self.previous.name, queue_row=self.carried_row))
        self.assertEqual(errors, [])

    def test_short_queue_without_reason_fails(self) -> None:
        text = current_text(self.previous.name, queue_row=self.carried_row).replace(
            "> ★**시간 미달 사유**: fixture queue는 계약 검사 한 건뿐이며 중복 실험으로 48시간을 채우지 않는다.\n",
            "",
        )
        errors = self.write(text)
        self.assertTrue(any("below 48h" in error and "시간 미달 사유" in error for error in errors))

    def test_previous_queue_omission_fails(self) -> None:
        errors = self.write(current_text(self.previous.name, queue_row=""))
        self.assertTrue(any("no current row or transfer reason" in error for error in errors))

    def test_transfer_table_can_account_for_completed_batch(self) -> None:
        text = current_text(self.previous.name, queue_row="")
        text = text.replace(
            "| 이전 배치 | 처리 | 근거 |\n|---|---|---|",
            "| 이전 배치 | 처리 | 근거 |\n|---|---|---|\n"
            "| `run_P999_Stage1_fixture.bat` | 완료 | 결과문서에 재현 명령 보존 |",
        )
        errors = self.write(text)
        self.assertFalse(any("no current row or transfer reason" in error for error in errors))

    def test_pending_smoke_must_be_in_user_request(self) -> None:
        errors = self.write(
            current_text(self.previous.name, queue_row=self.carried_row, smoke="REQUIRED_USER_RUN")
        )
        self.assertTrue(any("not mirrored" in error for error in errors))

    def test_wsl_smoke_entrypoint_is_accepted_and_mirrored(self) -> None:
        text = current_text(
            self.previous.name, queue_row=self.carried_row, smoke="REQUIRED_USER_RUN"
        ).replace("run_smoke_check.bat", "run_smoke_check.sh")
        text = text.replace(
            "| `-done` 삭제 | 저장소 루트 | 삭제 후보 없음 | 삭제하지 않음 | 변경 없음 | 재감사 |",
            "| smoke | `run_smoke_check.sh` | WSL fixture | 실행 | PASS | 판독 |\n"
            "| `-done` 삭제 | 저장소 루트 | 삭제 후보 없음 | 삭제하지 않음 | 변경 없음 | 재감사 |",
        )
        errors = self.write(text)
        self.assertFalse(any("smoke" in error for error in errors))

    def test_no_open_wip_cannot_claim_interrupted_work(self) -> None:
        text = current_text(self.previous.name, queue_row=self.carried_row).replace(
            "새 요청 시작", "중단 작업을 이어서 시작"
        )
        errors = self.write(text)
        self.assertTrue(any("although open-WIP state is 없음" in error for error in errors))

    def test_missing_sync_table_fails(self) -> None:
        text = current_text(self.previous.name, queue_row=self.carried_row).replace(
            "| 산출물 | 필요 여부 | 실제 diff | 미갱신 사유 |",
            "| 파일 | 상태 |",
        ).replace("|---|---|---|---|\n| 결과 | 불필요 | 없음 | fixture only |", "|---|---|")
        errors = self.write(text)
        self.assertTrue(any("synchronization table" in error for error in errors))

    def test_unresolved_failure_requires_all_decision_fields(self) -> None:
        text = current_text(self.previous.name, queue_row=self.carried_row).replace(
            "|---|---|---|---|---|---|---|\n\n## 5. 확보한 수치",
            "|---|---|---|---|---|---|---|\n"
            "| plan numbers | P091 draft | FAIL | — | remove reservation | rename token | 사용자 |\n\n"
            "## 5. 확보한 수치",
        )
        errors = self.write(text)
        self.assertTrue(any("unresolved-check row" in error and "운영 영향" in error for error in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)
