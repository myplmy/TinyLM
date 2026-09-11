# WIP 작업원장 — 2026-09-12 Codex P8 실패 원인분석·수정

- **세션 시작**: 2026-09-12
- **직전 핸드오프**: `handoff/202609111517_HANDOFF.md`
- **사용자 지시**: 1건 (아래 표가 정본)

## 진행 상황판

| # | 지시 | 상태 | 산출물 | 이어받을 지점 |
|---:|---|---|---|---|
| **1** | `(chatgpt 종료 후 재시작, 기존 tinyLM 프로젝트에 새 세션 생성)새 세션에서 수행결과 아래와 같은 응답을 받았음. 확인 후 원인분석, 수정 진행바람.` 및 첨부된 P8 `FAIL/PARTIAL` 관찰·문서 불일치 2건 | ✅완료 | Windows handler 교정, 회귀검증, P8 교정 보고, Codex 상태 문서 정합화 | 변경 hash 재신뢰 뒤 깨끗한 새 세션에서 P8 재검증 |

범례: ⏳대기 · 🔄진행 · ✅완료 · 🚫막힘(사유 기재)

## 작업 분해

- [x] P8 관찰과 현재 훅 설정·guard·테스트 사이의 불일치 재현 및 원인 확정
- [x] 영향도 분석 후 최소 범위 수정
- [x] 훅 단위·정적 환경 회귀검증
- [x] Codex 00 서두와 Codex 06 §8의 단계 상태 정합화
- [x] 변경 diff와 수행·미수행 경계 보고

## 확보한 수치

| 항목 | 값 | 의미 |
|---|---:|---|
| P8 정상 probe | 1/1 통과 | 셸 도구 자체는 실행됨 |
| P8 차단 probe | 0/2 차단 | 루트·`scripts` 모두 exit 0, `PreToolUse deny` 미관찰 |
| probe 파일 생성 | 0건 | `$false` 안전장치가 실제 쓰기를 막음 |
| 저장소 스킬 발견 | 17개 | P4 스킬 자동 발견은 새 세션에서 확인됨 |
| 현재 Codex Desktop | `26.903.9818.0` | 로컬 설치 버전 관측 |
| 현재 Codex CLI | `0.153.4` | 로컬 번들/CLI 관측 |
| Python guard 직접 호출 | deny 출력·exit 0 | 판정 로직과 구조화 출력은 정상 |
| 기존 `commandWindows` 직접 실행 | deny 출력·exit 0 | 외부 outer-quote가 없을 때 정상 |
| 기존 `commandWindows` Codex식 outer-quote 재현 | exit 1·guard 미도달 | 내부 `-Command "..."`가 Windows `cmd /C` outer-quote와 충돌 |
| 교정 handler outer-quote 회귀 | 루트·`scripts` 2/2 deny | Git 루트 해석과 구조화 출력 확인 |
| 훅 테스트 | 16/16 PASS | 기존 guard 14개 + Windows handler 계약·실제 프로세스 2개 |
| Codex 환경 전용 P7 | 20/20 PASS | 보호 데이터 비접근 환경 정적검사 |

## 작업 로그 (append-only)

- `2026-09-12` 사용자 제공 P8 결과를 기준으로 착수. 현재 판정은 `STATIC_ONLY / E2E_NOT_RUN` 유지.
- `2026-09-12` 공식 OpenAI Hooks 문서에서 프로젝트 신뢰, `PreToolUse`, `Bash` matcher, `tool_input.command`, Windows `commandWindows`, 구조화된 deny 계약을 재확인.
- `2026-09-12` 실제 `.codex/hooks.json`의 Windows handler를 합성 이벤트로 대조. handler 자체는 deny를 출력하지만 Codex Windows 실행 형태처럼 전체 명령을 outer-quote하면 exit 1로 guard에 도달하지 못함을 재현.
- `2026-09-12` OpenAI Codex 공개 이슈 #38168의 "embedded quotes never execute but may report Completed" 현상과 현재 handler의 `powershell ... -Command "..."` 형태가 일치함을 확인. Code Mode `PreToolUse` dispatch 문제(#23411)는 저장소 측 수정 후 새 세션에서 분리 판정할 잔여 위험으로 기록.
- `2026-09-12` Windows handler를 embedded double quote 없는 중첩 `cmd`와 Git 루트 해석형 PowerShell wrapper로 교정. Codex식 outer-quote를 적용한 실제 프로세스 회귀를 루트와 `scripts` cwd에서 각각 deny로 확인.
- `2026-09-12` 훅 테스트 16/16 PASS. 환경 전용 P7은 샌드박스 내부 Git Bash 신호 파이프 제한(Win32 error 5)으로 19/20이었으나, 동일 검사를 승인된 샌드박스 밖에서 재실행해 20/20 PASS.
- `2026-09-12` Codex 00의 P7 `NOT_RUN`, Codex 06 §8의 P0~P4·P6 한정 문구와 관련 상태 색인을 현재 증거로 정합화. P8은 새 세션 재검증 전까지 `STATIC_ONLY / E2E_NOT_RUN` 유지.
- `2026-09-12` 보호 데이터·GPU·학습·모델·프로젝트 스모크·삭제·staging·commit·push·PR은 수행하지 않았고, 루트 09는 기준선 해시 일치만 확인했으며 수정·복제하지 않음.
