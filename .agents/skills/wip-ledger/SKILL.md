---
name: wip-ledger
description: 세션 착수 시 WIP 작업원장을 만들고 작업 중 갱신한다. 사용량 초과로 중단돼도 원장만으로 이어받을 수 있게 한다. 지시가 3건 이상이거나 작업이 1시간을 넘을 것 같으면 무조건 쓴다.
---

# WIP 작업원장 v2

> **TinyLM Codex 전용.** 의미 정본은 [Codex 02 §10](../../../ai_dev_tool/Codex/02_핸드오프_규약.md),
> 유일한 정상 쓰기 API는 [`scripts/wip.py`](../../../scripts/wip.py)다. WIP와 루트
> [09 구현검증 원장](../../../ai_dev_tool/09_구현검증_필요목록.md)은 서로 다르며, 사용자가
> 09 갱신을 지시하지 않으면 복사·이관·미러링하지 않는다.

## 언제 반드시 쓰나

- 사용자 지시가 3건 이상
- 로그 판독·결과문서 반영이 하나라도 포함
- 코드 수정이 2파일 이상

위 조건이면 작업 착수 전에 만든다. 핸드오프는 세션 종료 스냅샷이고 WIP는 진행 중 복구
정본이므로 서로 대체하지 않는다.

## v2 고정 계약

```text
# | 사용자 지시 | 상태 | 작업 내용 | 산출물 | 이어받을 지점
```

- `사용자 지시`: 원문 의미를 생략하지 않는다.
- `작업 내용`: 최신 한 줄 요약. 새 상태 기록으로 교체하며 누적하지 않는다.
- `산출물`: 최종 파일·검사 증거. 없으면 `—`.
- `이어받을 지점`: 대기·진행·막힘이면 다음 한 행동, 완료면 `—`.
- 셀에 `<br>`이나 실제 개행을 넣지 않는다. 전체 이력은 `## 3. 작업 로그 (append-only)`가 소유한다.
- `## 4. 오버라이드 수정 이력 (append-only)`와 `## 5. Compact 상태 캡슐 (v1)`을 보존한다.

레거시 5열 원장은 조회만 가능하다. 완료 원장은 소급 변환하지 않는다. 열린 레거시 원장의
변환은 사용자 승인 참조를 명시한 `--migrate-v2`로만 한다.

## 정상 명령

항상 선택한 원장을 `--file`로 명시하고 UTF-8 모드로 실행한다.

```powershell
# 새 원장: 열린 원장이 없을 때
python -X utf8 scripts/wip.py --new `
  --previous handoff/이전_HANDOFF.md `
  --allow "허용된 파일·작업" --not-run "금지·미실행 경계" `
  --user-owned "사용자 소유 실행" --retired-claims "폐기·정정 주장" `
  --item "1=사용자 지시 원문" --item "2A=사용자 지시 원문"

# 동시 작업 예외: 사용자가 별도로 승인한 경우에만
python -X utf8 scripts/wip.py --new --allow-concurrent `
  --concurrent-reason "사용자 승인 YYYY-MM-DD와 승인 범위" `
  --session-id $env:CODEX_SESSION_ID `
  --previous handoff/이전_HANDOFF.md `
  --allow "이번 작업의 독립 허용범위" --not-run "금지·미실행 경계" `
  --user-owned "사용자 소유 실행" --retired-claims "폐기·정정 주장" `
  --item "1=사용자 지시 원문"

# 상태 전이
python -X utf8 scripts/wip.py --start 1 --file handoff/WIP_YYYYMMDD_작업원장.md `
  --note "현재 한 줄" --resume "다음 한 행동"
python -X utf8 scripts/wip.py --done 1 --file handoff/WIP_YYYYMMDD_작업원장.md `
  --note "완료 판정과 검증" --artifact "산출물 경로"
python -X utf8 scripts/wip.py --wait 2A --file handoff/WIP_YYYYMMDD_작업원장.md `
  --note "왜 대기인가" --resume "대기 해제 뒤 첫 행동"
python -X utf8 scripts/wip.py --block 2A --file handoff/WIP_YYYYMMDD_작업원장.md `
  --note "막힘 근거" --resume "해제 조건"

# 사용자 지시 추가와 완료 닫기
python -X utf8 scripts/wip.py --add 3 --file handoff/WIP_YYYYMMDD_작업원장.md `
  --directive "추가 사용자 지시 원문" --resume "첫 행동"
python -X utf8 scripts/wip.py --capsule-check --file handoff/WIP_YYYYMMDD_작업원장.md
python -X utf8 scripts/wip.py --close --file handoff/WIP_YYYYMMDD_작업원장.md
```

허용 상태 전이는 `대기→진행`, `진행→완료`, `대기·진행→막힘`, `막힘→대기·진행`이다.
완료 항목은 다시 열지 않는다. 열린 항목이 하나라도 있거나 캡슐 해시가 낡았으면 닫지 않는다.

기본 계약은 열린 원장 하나다. 병렬 세션 때문에 둘째 원장이 꼭 필요할 때만 사용자의 별도 승인을
근거로 `--allow-concurrent`와 `--concurrent-reason`을 함께 쓴다. 이때 세션 ID를 원장에 결합하고,
모든 조회·상태 전이·닫기에 `--file`을 명시한다. 인자 없는 `--list`는 열린 원장을 모두 보여준다.
compact 훅은 공식 hook 입력의 `session_id`와 정확히 일치하는 원장 하나만 주입한다. 일치
원장이 없거나 `session_id`가 없으면 다른 원장을 대체 선택하지 않고 경고·무주입 상태로 compact는
계속한다. 같은 세션에 복수 원장이 일치하거나 정확히 일치한 원장의 캡슐이 손상·구식이면
상태 모호성으로 중단한다. 기존 다른 원장은 수정·종료하지 않는다. 새 파일명은 열린 파일과 동일 stem의 `-done` 파일을 모두 사용 중인
슬롯으로 보아야 한다. 과거 완료 파일 때문에 닫기 대상이 충돌한 열린 원장은 직접 개명하지 않고
`--repair-name-collision --reason ... --approval-ref ...`로 감사 이력을 남겨 다음 빈 슬롯으로 옮긴다.

기능 도입 전에 만들어져 `Codex 세션 ID`가 없는 기존 원장은 자동 추정하지 않는다. 그 원장의
소유 세션과 사용자가 확인된 경우에만 다음처럼 정확한 파일·세션·사유·승인을 함께 기록한다.

```powershell
python -X utf8 scripts/wip.py --bind-session `
  --file handoff/WIP_YYYYMMDD_작업원장.md `
  --session-id $env:CODEX_SESSION_ID `
  --reason "이 원장이 현재 세션 소유임을 확인한 근거" `
  --approval-ref "사용자 승인 YYYY-MM-DD"
```

완료 원장 재결합과 이미 결합된 원장의 다른 세션 재결합은 거부한다.

## 예외 교정

정상 상태 명령으로 표현할 수 없는 단일 셀 교정만 compare-and-set 오버라이드로 처리한다.
대상, 정확한 수정 전·후, 근거, 사용자 승인 참조가 모두 필요하며 시각과 SHA-256은 도구가 쓴다.

```powershell
python -X utf8 scripts/wip.py --override --file handoff/WIP_YYYYMMDD_작업원장.md `
  --item 2A --field "작업 내용" --expect-before "현재 정확한 값" `
  --set-after "교정값" --reason "정상 전이로 표현할 수 없는 이유" `
  --approval-ref "사용자 지시 YYYY-MM-DD"
```

`상태`는 오버라이드할 수 없다. `사용자 지시` 교정은 구체 승인과
`--allow-directive-correction`이 함께 있어야 한다. 직접 `apply_patch`, 리다이렉션,
`Set-Content` 등으로 WIP를 고치지 않는다. PreToolUse 가드는 보조선일 뿐이며 fail-open 경고나
정적 mock PASS를 실제 Code Mode 차단 E2E PASS로 승격하지 않는다.

## 재개·검증

1. `python -X utf8 scripts/wip.py --list --file <열린 원장>`으로 스키마와 항목을 확인한다.
2. `## 5. Compact 상태 캡슐`의 해시를 `--capsule-check`로 검사한다.
3. 진행·대기·막힘 행의 `이어받을 지점`부터 이어간다. 원장에 확보 수치가 있으면 먼저 재사용하되,
   최신성이 바뀔 수 있는 외부 상태만 다시 확인한다.
4. 변경 뒤 `python -X utf8 scripts/test_wip.py`를 실행한다.

## 금지

- 작업이 끝난 뒤 원장을 몰아 쓰기
- 완료 원장 삭제·소급 변환
- 여러 열린 원장 중 하나를 추측해 수정
- WIP 표·핸드오프 §0의 항목 수 또는 의미를 서로 다르게 기록
- 수동 패치 성공을 감사 가능한 스크립트 상태 전이로 오보고
