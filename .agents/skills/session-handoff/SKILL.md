---
name: session-handoff
description: TinyLM 세션 종료·중단·이전 요청에서 Codex 02 규약과 scripts/new_handoff.py를 사용해 공유 handoff 문서를 만든다. 범용 7절 템플릿이나 다른 환경 메모리를 사용하지 않으며, WIP 및 루트 09와 역할을 분리한다.
---

# session-handoff

> **TinyLM Codex 이식본(전용 어댑터).** 형식 정본은 [Codex 02](../../../ai_dev_tool/Codex/02_핸드오프_규약.md),
> 경로 메타데이터는 [`.agents/project.json`](../../project.json)이다. 다른 에이전트 환경의
> 지침·스킬·메모리·템플릿은 읽거나 호출하지 않는다.

## 목적과 트리거

사용자가 세션 종료, 다음 세션 이전, 핸드오프, 임시 기억, 중단 대비 정리를 요청하거나
그 의도를 명확히 나타낼 때 사용한다. 일반 진행 보고나 영구 규범 갱신에는 사용하지 않는다.

- 진행 중 작업의 실시간 복구 기록: `wip-ledger`
- 세션 종료·이전 스냅샷: 이 스킬과 공유 `handoff/`
- 영구 작업규범·프로젝트 기억: `AGENTS.md`, `ai_dev_tool/Codex/00~08`
- 구현검증 작업원장: 루트 `ai_dev_tool/09_구현검증_필요목록.md`

WIP나 루트 09를 핸드오프로 복사·이관하지 않는다. 필요한 항목은 원래 정본을 링크한다.

## 사전 읽기

1. 현재 사용자 지시와 승인 범위
2. `AGENTS.md`
3. `ai_dev_tool/Codex/02_핸드오프_규약.md` 전체
4. `.agents/project.json`의 `handoffDir`과 09 예외
5. 완료되지 않은 `handoff/WIP_*.md` 및 최신 유효 `*_HANDOFF.md`

최신 핸드오프는 특정 파일명을 하드코딩하지 않는다. 이름·이전 체인·존재 증거를 사용해
동적으로 고르고, 공유 핸드오프의 레거시 환경 포인터는 현재 Codex 지침으로 따르지 않는다.

## 작성 절차

### 1. 파일 생성

사용자의 핸드오프 작성 요청이 쓰기 권한이다. 파일명 시각을 추측하지 말고 다음 도구가 정하게 한다.

```powershell
python scripts/new_handoff.py --title "<이 세션이 남긴 것 한 줄>"
```

같은 분 파일이 이미 있으면 덮어쓰지 않는다. 도구가 만든 기존 파일을 이어 쓸지 사용자 범위를 확인한다.

### 2. Codex 02 고정 구조 채우기

도구 골격과 Codex 02의 현재 규약을 대조해 다음 내용을 빠짐없이 채운다.

- `§0`: 사용자 지시 원문, 판단한 목적, 필요 작업, 실제 작업, 결과를 분리한 표
- `§1`: 가장 중요한 사실 세 가지
- `§2 사용자용 판독`: 내부 파일명을 몰라도 이해하도록 `관측/의미/사용자 영향/다음 행동`을
  한 행에 설명한다. AI 복구용 경로·hash·상태 코드만 나열해 사용자 설명을 대신하지 않는다.
- `§2~K`: 지시별 상세 근거·수치·판정과 `NOT_RUN` 상태
- `정본 동기화·미갱신 사유`: `산출물/필요 여부/실제 diff/미갱신 사유`를 모두 채움
- 정적검사 전문은 handoff에 복사하지 않고 동일 세션의 `handoff/audit/*_STATIC_AUDIT.json`을
  머리말에서 링크한다. handoff·WIP·audit 세 문서가 한 세션 묶음이며 각 역할을 중복하지 않는다.
- `스모크·동적 검증 계승`: `REQUIRED_USER_RUN`, `NOT_REQUIRED(정확한 근거)`,
  `NOT_RUN_PENDING` 중 하나를 기록하고 대기 상태는 사용자 부탁과 연결
- `사용자에게 부탁하는 것`: `대상/정확한 위치/근거/사용자가 할 행동/완료 신호/AI 후속 처리`
  여섯 요소를 한 행에 두며, 비어도 쓰고 `-done` 배치 삭제 판정을 항상 포함
- `다음 권장 실험 순서`: `순/id/실험/배치 파일/⚙/누적/인벤토리/실행상태/선결/근거` 열과
  `이전 큐 제외·완료 이관` 표. 상태는 인벤토리와 즉시 실행 가능성을 섞지 않음
- `커밋 메시지`: 한국어 제목과 본문을 별도 라벨·별도 코드블록으로
- `열린 질문`, 상태 분기한 `새 세션 시작 프롬프트`, `compact 프롬프트`, `참조 치트시트`

GPU·학습·모델 로딩·스모크·삭제·commit·push를 실제로 하지 않았다면 반드시 `NOT_RUN` 또는
`0건`으로 적는다. 계획, 정적 확인, 실제 실행, 사용자 E2E를 서로 승격하지 않는다.

### 3. 정본 동기화

- 핸드오프 §0의 지시 수는 열린 WIP의 지시 수와 같아야 한다.
- 사용자 부탁 절이 채팅 최종 보고의 부탁 목록 정본이다. 보고에서 항목을 더하거나 빼지 않는다.
- 영구 규범을 전문 복사하지 말고 `AGENTS.md` 또는 Codex 00~08의 해당 절을 링크한다.
- 이번 세션의 변동 사실과 재시작 지점은 구체 경로·상태·근거와 함께 적는다.
- 결과 연쇄의 각 대상은 `필요/불필요/보류`와 실제 diff 또는 정확한 미갱신 사유를 기록한다.
- 열린 WIP가 있으면 시작 프롬프트에 정확한 파일명과 첫 미완료 번호를 쓴다. 없으면
  “중단 작업”을 쓰지 않고 새 요청 시작이라고 명시한다. 승인 대기 항목은 승인 전 금지를 함께 쓴다.

### 3.1 직전 큐 무손실 계승 — B 다음 D

`scripts/new_handoff.py`는 먼저 B 계약에 따라 직전 §7의 미완료 배치를 전수 가져오고,
`scripts/handoff_queue.py`가 D 보조 입력으로 `queue_menu.py`의 현재 id·TSV 시간을 대조한다.
자동 이관 행은 항상 `REVALIDATE`다. AI가 현재 로그·계획·선결을 감사해 `READY/GATED/HOLD`로
바꾸기 전에는 실행을 권하지 않는다.

- 인벤토리: `PRESENT`, `DONE`, `MISSING`, `REPLACED`, `UNVERIFIED`(진행 중 큐 잠금)
- 실행상태: `READY`, `GATED`, `HOLD`, `DONE`, `REVALIDATE`
- 직전 미완료 배치를 현재 §7에서 빼려면 `이전 큐 제외·완료 이관` 표에 파일명·처리·근거를 쓴다.
- 재감사하지 않았다는 사실은 삭제 근거가 아니며 `REVALIDATE` 근거다.
- 현재 큐의 배치 수·시간 합계는 §7 본표만 집계한다. §7.1 이하의 완료·제외 이관 이력은
  계승 증거일 뿐 현재 큐에 다시 합산하지 않는다. `run_queue.bat` 같은 운영 실행기는
  `experiments.tsv` 실험 배치가 아니므로 배치 수·시간에서 제외한다.

### 3.2 진행 중 큐 잠금 예외

사용자가 진행 중 큐의 실험 로그·런처를 읽지 말라고 지정하면
`scripts/new_handoff.py --title "..." --queue-locked`를 사용한다.
생성기는 직전 핸드오프 §7만 읽고, `experiments.tsv`와 런처 경로의
존재·내용을 조회하지 않는다. 자동 행의 인벤토리는
`UNVERIFIED`, 실행상태는 `REVALIDATE`, id는 미확인으로 둔다.
예상 시간은 **직전 문서의 역사값**이며 현 큐 제안이 아니다.
§7에 `시간 미달 사유`와 잠금 해제 뒤 재감사 선결을 명시한다.
`handoff_queue.py --audit`는 문서 상속만 확인하므로 사용할 수 있지만
`queue_menu.py --audit`나 live inventory를 열면 안 된다.

### 4. 한정 검증

핸드오프 작성 작업 자체에서 허용된 경우에만 다음 Codex 전용 문서 검사기를 실행한다.

```powershell
$env:PYTHONIOENCODING = 'utf-8'
python -I -B .agents/skills/session-handoff/scripts/check_handoff_codex.py
python scripts/handoff_time.py
python -X utf8 scripts/handoff_queue.py --audit handoff/<현재> --previous handoff/<직전>
```

공유 `scripts/check_handoff.py`는 다른 에이전트 환경 진입 파일을 직접 읽으므로 Codex
런타임에서 호출하지 않는다. 위 독립 검사기는 고정 구조·정본 동기화·행동 6요소·시작 상태
분기·스모크 disposition·직전 큐 계승·커밋 구분·`-done` 삭제 판정·로컬 링크를 검사하고,
시각 증거는 공유 `scripts/handoff_time.py`가 별도로 본다.
이는 핸드오프 문서 정적 검사일 뿐 프로젝트 스모크나 새 세션 E2E가 아니다. 실패하면 내용을
고치되 과거 핸드오프를 소급 재작성하지 않는다.

## 최종 보고

- 생성한 절대 경로
- 핵심 상태와 미해결
- 미해결 검사 행은 `검사 / 정확한 대상 / 증거와 상태 / 운영 영향 / 권장 조치 / 대안 / 승인 주체`
  7요소를 모두 적는다. 번호 전체를 면제하지 않고 원문 오류와 진단 기록을 분리한다.
- 사용자 부탁 절의 정확한 요약
- 커밋 메시지 제목과 본문(요청 범위에 포함된 경우)
- compact 프롬프트(규약상 파일에 기록한 것). M4·M5 PASS 전에는 수동 보조라고 표시

사용자가 compact를 실행할지 결정한다. 스킬은 compact나 새 세션을 임의 실행하지 않는다.

## 금지

- 범용 7절 세션 템플릿 사용
- 파일명·시각 수동 추정
- 특정 최신 핸드오프 이름을 영구 문서에 하드코딩
- PR·branch·GitHub를 기본 전제로 삽입
- WIP 또는 루트 09의 사본·미러 생성
- 사용자 요청 없는 삭제·Git 외부 변경·실험 실행
- 다른 에이전트 환경 경로로 fallback

## 번들 리소스

- `assets/templates/session_handoff.md`: 중복 양식을 금지하고 정본 생성기를 안내하는 표지
- `references/what_to_include.md`: TinyLM 항목별 포함 기준
- `references/examples.md`: Codex 02 형식의 최소 예시
- 실제 골격 정본: 저장소 `scripts/new_handoff.py`
- Codex 정적 검사기: `.agents/skills/session-handoff/scripts/check_handoff_codex.py`
- 큐 이관·감사 보조: 저장소 `scripts/handoff_queue.py`
