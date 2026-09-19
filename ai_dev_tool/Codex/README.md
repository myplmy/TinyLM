# TinyLM Codex 작업환경 — 소유권·분리 계약

> **최신 갱신일자**: 2026-09-18 · **문서 유형**: live

> 제정: 2026-09-11, 승인된 제안서 P1  
> 상태: **Windows P0~P8 역사 증거 보존; WSL agent·관찰한 hook 범위 `ACTIVE_VERIFIED`, M3 사용자 범위 예외 종결(manual compact `NOT_RUN`·검증 제외), 현재 변경 뒤 smoke `E2E_NOT_RUN`**
> 제안서: `proposal/done/20260911_Codex-작업환경-완전분리-구축-approved.md`  
> 항목별 설계표: [`temp_AGENTS.MD_항목별_00_08_이식목록.md`](temp_AGENTS.MD_항목별_00_08_이식목록.md)
> 정적 검증 보고: [`P7_정적종합검증_보고.md`](P7_정적종합검증_보고.md)
> P8 1차 실패·교정: [`P8_새세션_E2E_1차실패_원인분석_및_교정.md`](P8_새세션_E2E_1차실패_원인분석_및_교정.md)
> P8 최종 E2E: 이 문서 [§1.1](#11-p8-최종-e2e-관찰-기록--2026-09-12)의 사용자 제공 실제 관찰 기록

이 폴더는 TinyLM의 **Codex 전용 장기기억**이다. 파일명만 바꾼 Claude 사본이 아니라, Codex의 도구·권한·경로에 맞춘 독립 정본을 둔다.

## 1. 현재 전환 상태

| 단계 | 상태 | 의미 |
|---|---|---|
| P0 기준선·소유권 | 완료 | 대상 문서의 해시와 동시 작업 보호선을 `handoff/WIP_20260911c_작업원장-done.md`에 기록 |
| P1 분리 계약 | **이 문서로 확정** | 활성·공유·금지 경로와 우선순위를 고정 |
| P2 Codex 00~08 | **완료·P7 정적검증 통과** | 10개 초벌 사본을 의미 단위로 이식하고 상호링크·역사 표지를 종합검증 |
| P3 설정 | **완료·P7 정적검증 통과** | `.agents/project.json`과 `.codex/config.toml`의 구문·경로·역할 분리 확인 |
| P4 스킬 | **완료·P7 정적검증 통과** | 17개 스킬과 부속 파일의 구문·참조·정적 계약·독립성 확인 |
| P5 훅 | **위험쓰기·이전 auto compact 관찰 범위 `ACTIVE_VERIFIED`; 현재 compact 변경 `STATIC_ONLY`** | guard 실제 관찰은 보존한다. exact-WIP auto 주입도 과거 hash에서 관찰했지만, 2026-09-19 진행 항목 capsule·반환 계약을 바꿨으므로 새 hash 재신뢰와 auto E2E 전에는 현재 변경을 승격하지 않는다 |
| P6 `AGENTS.md` 축약·전환 | **완료** | 890행·100,960바이트에서 219행·14,057바이트로 축약하고 Codex 전용 진입 규범으로 전환 |
| P7 정적 종합검증 | **PASS** | 환경 전용 검사 20/20 통과, 루트 09 기준선 SHA-256 일치. P7 당시 프로젝트·모델 스모크는 `NOT_RUN`; 2026-09-12 별도 사용자 실행은 §1.2 `PASS` |
| P8 새 세션 E2E | **`PASS / ACTIVE_VERIFIED`** | 2026-09-12 새 Code Mode 세션에서 `AGENTS.md` 자동 적용, 저장소 스킬 17개 발견, 정상 probe 허용, 루트·`scripts/` 차단 probe 2/2 deny, fail-open 경고 0건과 probe 파일 0개를 실제 관찰했다. 범위는 §1.1로 한정한다 |

P0~P7의 파일 이식과 정적 종합검증 뒤, P8 1차 실패 원인을 Windows handler의
embedded-quote 처리로 좁혀 교정했다. 2026-09-12 최종 E2E에서 교정된 경로의 실제 차단을
새 세션으로 관찰했으므로 **P8은 PASS이고 해당 관찰 범위는 `ACTIVE_VERIFIED`**다.
이는 모든 Codex 기능·Desktop 버전·모델 실행까지 검증됐다는 뜻이 아니다.

### 1.1 P8 최종 E2E 관찰 기록 — 2026-09-12

이 표는 사용자가 제공한 최종 E2E 실행 기록을 보존한다. `실제 관찰`은 Code Mode 세션에서
관찰한 사실이고, `/hooks` UI 상태는 사용자가 사전 검토·신뢰를 완료했다고 명시한 **전제**다.

| 검사 | 실제 도구·workdir | 기대 | 실제 관찰 | 판정 |
|---|---|---|---|---|
| `AGENTS.md` 자동 적용 | 세션 자동 주입·도구 호출 전 | 자동 적용 | `Z:\TinyLM\AGENTS.md` 본문이 세션 시작 시 제공됨 | PASS |
| 저장소 스킬 자동 발견 | 세션 자동 주입·도구 호출 전 | 17개, `session-handoff`·`wip-ledger` 포함 | 정확히 17개이며 두 스킬 모두 포함 | PASS |
| `/hooks` enabled·trusted·새 hash 신뢰 | 사용자 사전 조치 | 사전 검토·신뢰 완료 | 사용자가 완료했다고 명시함. 이 세션에서 UI를 별도 조회하지 않음 | **전제 PASS** |
| 정상 probe | `functions.exec` → `exec_command`, `Z:\TinyLM` | 허용·exit 0·파일 생성 없음 | 리터럴 `a\nb` 출력, `exit_code: 0` | PASS |
| 루트 차단 probe | 같은 도구, `Z:\TinyLM` | 셸 실행 전 deny | `Command blocked by PreToolUse hook`; 셸 `exit_code` 생성 전 차단 | PASS |
| `scripts/` 차단 probe | 같은 도구, `Z:\TinyLM\scripts` | 셸 실행 전 deny·Git-root wrapper 해석 | 같은 실제 `PreToolUse` deny; 셸 `exit_code` 없음 | PASS |
| fail-open 경고 | 위 probe 3건 | 0건 | 훅 fail-open·`systemMessage` 경고 0건 | PASS |
| probe 파일 부재 | `Test-Path`, `Z:\TinyLM` | 모두 없음 | 루트와 `scripts/`의 `.codex\hook-probe.txt`가 모두 `False` | PASS |
| 외부 상태 보존 | 전체 수행 범위 | 변경·접근·실행 0건 | 파일 생성·수정·삭제 0건, 보호 데이터 접근 0건, GPU·모델 실행 0건, staging·commit·push·PR 0건 | PASS |

관찰된 셸은
`C:\Users\Uranus\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe`
7.6.5였고, Codex CLI는 `C:\Users\Uranus\AppData\Roaming\npm\codex.ps1` 0.153.4였다.
Desktop 버전은 이 세션에서 확인하지 못했다.

CLI 버전 조회 중 임시 경로 권한 경고 2건이 있었지만 버전 조회는 exit 0이었고, 위 probe의
훅 fail-open 경고는 아니었다. 이 최종 E2E 기록에서는 guard·wrapper·훅 단위 테스트·환경 검사기를
직접 실행하지 않았다. 그 항목의 P7 정적·로컬 검사 증거와 이번 새 세션 실제 관찰을 서로 대신하지 않는다.

### 1.2 프로젝트·모델 스모크 사용자 실행 기록 — 2026-09-12

사용자가 P088 Stage10 종료 뒤 [`202609121745_smoke_254f4ff.txt`](../../smoketest_logs/202609121745_smoke_254f4ff.txt)를
제공했다. 최종 SUMMARY는 **41팔, 실패 0, exit 0 오류표지 0, 계측 필드 계약 오류 0**이므로
이 실행은 프로젝트·모델 스모크 범위에서 **PASS**다. 실행 기준은 commit `254f4ff`에 당시 dirty
20개(코드 1개)가 더해진 작업트리였으므로, 순수 커밋 `254f4ff`만의 재현 증거로 읽지 않는다.
합성 30스텝 손실값은 품질 근거가 아니며 계측값의 물리적 정확성까지 증명하지 않는다.

⚠️이 로그 뒤 프로젝트 코드와 Codex 훅·작업 도구를 수정했다. 따라서 §1.2는 **실행 당시 트리의 PASS 기록**이고,
후속 수정분을 포함한 현재 트리의 프로젝트 스모크는 **E2E_NOT_RUN**이다. 장기 실험 큐 전에 사용자가
`run_smoke_check.bat`를 다시 실행해야 한다.

2026-09-14 사용자 로그 [`202609140112_smoke_cffa297.txt`](../../smoketest_logs/202609140112_smoke_cffa297.txt)는
42팔 중 실패 1, exit-0 오류표지 0, 계측 계약 오류 0이었다. 유일한 실패는 완료·제외 이력인 §7.1의
삭제된 과거 배치 4개를 `check_handoff.py`가 현재 실행 큐로 오인한 정적 검사 오탐이다. 실제 Markdown
상대링크 검사는 깨진 링크 0건이었다. 검사 범위를 현재 큐와 과거 이력으로 분리하고 회귀를 통과했지만,
수정 뒤 사용자 스모크는 아직 `E2E_NOT_RUN`이다.

### 1.3 2026-09-13 승인 개선안의 단계적 도입 상태

| 변경 | 정적 증거 | 현재 동적 상태 |
|---|---|---|
| WIP v2·감사형 override | 6열 계약·원자교체·lock·CP949 출력 회귀 fixture | `STATIC_ONLY`; 실제 다중 세션 경합 E2E는 `NOT_RUN` |
| WIP 직접수정 보조 차단 | Bash·`apply_patch` mock deny와 정상 `wip.py` 허용 | `STATIC_ONLY`; 새 hash 신뢰·실제 deny는 `E2E_NOT_RUN` |
| compact 상태 캡슐 | 8필드 sentinel, 진행 항목·길이상한, 수동/자동 `PreCompact`, `SessionStart(source=compact)` mock | WIP 12·compact 14 tests와 현재 session direct simulation PASS. 과거 exact-match auto 경로는 실제 PASS였으나 현재 hash는 `STATIC_ONLY`; manual은 사용자 검증 제외·`NOT_RUN` |
| 핸드오프 계승 | 6열 지시·동기화표·10열 큐·스모크 disposition fixture | 신규 실제 핸드오프에서 최종 검증 예정 |
| Git Bash 구문 검사 | 알려진 Windows startup 실패와 실제 `bash -n` 오류를 분리한 fixture | 현재 호스트의 POSIX 셸 구문 검사는 실행 결과에 따라 `PASS/FAIL/NOT_RUN` |
| 환경 검사 Python 호환 | `tomllib` 없는 모듈 import·flat TOML fallback 3회귀 포함 환경 단위검사 13/13 | 사용자 기본 Python의 E2E 1단계 재실행은 `NOT_RUN` |

환경 검사기는 이제 `PASS / FAIL / NOT_RUN`을 분리한다. 알려진 Windows signal-pipe·Win32 error 5·
`0xC0000142` Bash 시작 실패 또는 Bash 부재는 소스 오류가 아니므로 `NOT_RUN`이다. 실제 `bash -n`
구문 오류와 알 수 없는 startup 오류만 `FAIL`이며, 배포 게이트에서 반드시 Bash 증거가 필요하면
`--require-shell-syntax`로 `NOT_RUN`을 실패로 승격한다. 따라서 `NOT_RUN`을 PASS로 읽어서는 안 된다.

환경 검사기는 Python 3.11 이상의 `tomllib`를 우선 쓰되, 사용자 프로젝트 Python 3.10처럼 해당
표준 모듈이 없으면 현재 `.codex/config.toml`이 소유하는 **평면·JSON 호환 값 subset**만 내부
fallback으로 읽는다. 표·중복 키·확장 TOML은 구버전에서 조용히 오독하지 않고 실패한다. Codex 셸의
Python 3.11 단위검사 통과는 사용자 Python의 실제 E2E PASS가 아니므로 사용자 재실행 전에는
`STATIC_ONLY`다.

### 1.4 WSL 정본 이관 착수 상태 — 2026-09-17

사용자가 작업트리를 `/home/uranus/tinyLM`으로 이관했으며 Windows `Z:\TinyLM`은 같은 위치를
가리키는 편의 링크다. 공통 `run_queue.sh`, `run_smoke_check.sh`,
`run_cleanup_checkpoints.sh`와 교차 플랫폼 정적 검사는 구현·회귀 PASS다. 개별 실험 SH는
작성하지 않았고 실제 큐·스모크·cleanup은 `NOT_RUN`이다.

읽기 전용 Desktop 설정 실사에서는 `integratedTerminalShell = "wsl"`이지만
`runCodexInWindowsSubsystemForLinux = false`이며 과거 `Z:` project hook 세 개도 모두
disabled였다. 따라서 2026-09-12 Windows P8 기록은 역사적 유효 증거로 보존하되 현재 WSL
agent·hook에는 승계하지 않는다. WSL canonical project를 다시 열고 새 작업에서 exact hash를
검토·신뢰한 뒤 probe를 통과할 때까지 상태는 `E2E_NOT_RUN`이다.

### 1.5 WSL 새 task 실제 상태 — 2026-09-18

§1.4 뒤 사용자가 Desktop WSL mode로 새 task를 열었고 `/home/uranus/tinyLM`, Linux WSL2,
`Ubuntu`, `/usr/bin/bash`를 실제 관찰했다. 현재 task에서 다음 범위가 확인됐다.

| 범위 | 증거 | 판정 |
|---|---|---|
| WSL agent | canonical cwd·kernel·distro·Bash | `ACTIVE_VERIFIED` |
| 일반/root/scripts PreToolUse | 정상 exit 0, 위험쓰기 두 건은 shell exit 전 deny, 부산물·fail-open 경고 0 | 관찰 범위 `ACTIVE_VERIFIED` |
| WIP direct-write guard | Bash·`apply_patch` direct write는 tool 전 deny, 정상 `wip.py` 허용, WIP hash 불변 | 관찰 범위 `ACTIVE_VERIFIED` |
| compact | 과거 hash에서 exact 열린 WIP의 8필드 capsule이 auto compact 뒤 재주입 | 과거 auto 경로 PASS. 2026-09-19 진행 항목 포함 개선 뒤 현재 hash는 재신뢰·새 auto 관찰 전 `STATIC_ONLY`; manual `NOT_RUN`·사용자 검증 제외 |
| model smoke | `202609181921_smoke_d8011d0.txt`, 42팔·실패 0·exit-0 오류표지 0·계측 오류 0 | 당시 트리 PASS |

그 smoke 뒤 optimizer 기본값·기능 gate·추론 도구 코드가 바뀌었으므로 **현재 트리 smoke는 다시
`E2E_NOT_RUN`**이다. manual compact는 Codex가 앱 lifecycle event를 대신 만들 수 없고 사용자가
2026-09-18 검증 제외를 결정했다. M3 작업은 이 예외로 운영 종결하지만 manual 경로는 계속
`NOT_RUN`이며 WSL 이관 전체나 M3 전체를 `ACTIVE_VERIFIED`로 부르지 않는다. M4 backend와
M5 Windows↔WSL 교량은 `NOT_RUN`이다.

## 2. 런타임 경계

### 2.1 Codex 활성 정본

Codex의 작업환경을 구성하는 활성 원천은 다음뿐이다.

- 저장소 영구 지침: `AGENTS.md`
- 저장소 스킬: `.agents/**`
- Codex 네이티브 프로젝트 설정·훅: `.codex/**`
- Codex 장기기억: `ai_dev_tool/Codex/00~08`과 이 README

P3~P7 산출물은 독립 이식과 정적 종합검증을 통과했다. P8 1차 실패 뒤 P5 훅의
Windows handler를 교정했고, §1.1의 신뢰된 새 Code Mode 세션에서 수정본이 실제 호출되어
위험 쓰기 probe를 2/2 차단했다. 활성 완료 주장은 그 관찰 범위에 한정한다.

### 2.2 공유 프로젝트 정본

다음은 특정 에이전트 환경이 아니라 프로젝트 자체의 산출물이므로 Codex가 직접 참조할 수 있다.

- `handoff/**`와 `handoff/COMPASS.md`
- `docs/**`, `test_plan/**`, `test_result/**`, `review_request/**`, `proposal/**`
- `scripts/**`, `tinylm/**`, 최상위 배치·레지스트리·로그 등 실제 프로젝트 파일

공유 문서의 과거 본문에 `CLAUDE.md`, `.claude/**`, Claude용 시작 프롬프트가 남아 있어도 **환경 지침으로 따라가지 않는다.** 그것은 작성 당시의 역사 또는 레거시 포인터다. Codex는 동일 역할의 Codex 00·02·06·07과 `AGENTS.md`를 사용한다.

### 2.3 루트 09의 특별 예외

`ai_dev_tool/09_구현검증_필요목록.md`는 **현 위치 공유 작업원장**이다.

- Codex판 09를 만들지 않는다.
- 전체·부분 사본, 요약 정본, 동기화 미러를 만들지 않는다.
- 이 폴더의 문서는 필요할 때 `../09_구현검증_필요목록.md`를 링크로만 참조한다.
- Codex 환경 이식 작업은 루트 09를 수정하거나 이관하지 않는다.

### 2.4 Claude 전용 경로

다음은 Codex 런타임의 지침·스킬·훅·fallback 원천으로 사용하지 않는다.

- `CLAUDE.md`
- `.claude/**`
- 루트 `ai_dev_tool/00~08`의 Claude/공통 원본

금지는 단순 링크뿐 아니라 다음을 포함한다.

- `.claude/skills/**` 또는 `.claude/hooks/**`의 직접 실행·import
- 심볼릭 링크·하드링크·junction으로 Claude 파일을 Codex 경로에 노출
- Codex 파일이 없을 때 Claude 파일을 읽는 fallback
- 래퍼가 내부에서 Claude 스크립트를 호출하는 간접 재사용
- 한쪽을 고치면 다른 쪽이 자동으로 덮어써지는 동기화

## 3. 이식 입력과 전환 뒤 운영

P2·P4·P5의 승인된 이식 중에는 Claude 전용 파일을 **비교 입력으로 읽는 것만** 허용한다. 목적은 규범·절차·실패 교훈을 잃지 않고 Codex 의미로 다시 쓰는 것이다.

이식이 끝난 뒤의 동기화는 자동 공유가 아니라 다음 수동 절차를 따른다.

1. 사용자가 비교·이식 범위를 승인한다.
2. Claude 변경분을 읽기 전용으로 분류한다.
3. Codex 도구·권한·경로에 맞게 의미를 다시 설계한다.
4. Codex 소유 파일에 독립 패치한다.
5. 정적 검증과 새 세션 E2E를 별도로 기록한다.

문자열 `Claude` 자체가 모두 금지되는 것은 아니다. 01·04·05·08처럼 과거 사고를 보존하는 원장에서는 **`역사 기록 — 활성 Codex 지침 아님`**이라는 범위 안에서 당시 환경명을 쓸 수 있다. 그러나 현재 명령·정본·링크·도구 호출에는 쓰지 않는다.

## 4. 정본 우선순위

충돌 시 다음 순서를 적용한다.

1. 사용자의 현재 대화 지시와 명시적 승인 범위
2. 데이터·삭제·GPU·Git 등 보호 경계
3. `AGENTS.md`의 Codex 영구 지침
4. 최신 유효 공유 핸드오프, `handoff/COMPASS.md`, `docs/EXPERIMENT_BASELINES.md`
5. 이 폴더의 Codex 00~08
6. 실제 코드·로그·결과 문서의 해당 정본

동일 수준끼리 충돌하면 최신이라는 이유만으로 임의 선택하지 않는다. 충돌 위치와 양쪽 근거를 보고하고, 사용자 결정 또는 더 직접적인 실물 증거를 기다린다.

환경 지침의 경우 공유 핸드오프 안의 레거시 Claude 포인터보다 이 README와 Codex 파일이 우선한다. 실험 수치의 경우 이 README나 06의 요약보다 결과 문서·기준표가 우선한다.

## 5. 파일별 역할

| 파일 | 역할 | 담지 않는 것 |
|---|---|---|
| [`00_WORKING_RULES.md`](00_WORKING_RULES.md) | Codex 작업용 규약 정본(영문) | 장문 사고사·프로젝트 최신 수치 |
| [`00_작업규약_한글판.md`](00_작업규약_한글판.md) | 사용자 검토용 동등 한글판 | 영문판과 다른 규칙 |
| [`01_계측함정_원장.md`](01_계측함정_원장.md) | 측정·문서·도구 함정과 예방 근거 | 현재 프로젝트 상태 요약 |
| [`02_핸드오프_규약.md`](02_핸드오프_규약.md) | TinyLM 핸드오프와 WIP 절차 | 범용 7절 핸드오프 템플릿 |
| [`03_실험착수_절차.md`](03_실험착수_절차.md) | 계획→배치→사용자 실행→결과 회수 절차 | 사용자 승인 없는 실행 |
| [`04_의사결정함정_원장.md`](04_의사결정함정_원장.md) | 판단·범위·우선순위 사고 이력 | 계측 문제의 중복 전문 |
| [`05_폐기된_규약_원장.md`](05_폐기된_규약_원장.md) | 폐기 규범과 대체 정본 | 단순 실패 실험의 전문 |
| [`06_Codex용_프로젝트지침과_메모리.md`](06_Codex용_프로젝트지침과_메모리.md) | 현재 프로젝트 맥락·시작 라우팅 | 날짜별 전체 연혁과 수치 사본 |
| [`07_Codex_작업지시_권장.md`](07_Codex_작업지시_권장.md) | Codex용 시작·작업지시 예시 | Claude 도구명·경로 |
| [`08_AI-미보고-내역-자백원장.md`](08_AI-미보고-내역-자백원장.md) | 누락·오보고·재발 방지 기록 | 구현검증 백로그(루트 09가 소유) |

## 6. 변경 소유권

- 00~08은 Codex 세션이 갱신하되, 사용자 범위와 각 파일의 갱신 조건을 따른다.
- 실험 수치가 바뀌면 먼저 결과 문서·기준표·COMPASS를 고치고, 06은 링크와 현재 요약만 맞춘다.
- 이 폴더 파일을 고쳤다는 이유로 루트 `ai_dev_tool/00~08`, `.claude/**`, `CLAUDE.md`를 함께 고치지 않는다.
- 반대 방향도 같다. Claude 환경 변경은 Codex 파일 자동 변경 권한이 아니다.
- 동시 작업 중인 경로는 사용자 또는 해당 팀의 소유다. P0~P7 수행 중 `datasets/TinyDataset/**`는 데이터셋 팀 전용으로 잠갔고 열람·열거·검색·해시·검사·수정하지 않았다.

## 7. 증거 수준

| 표기 | 의미 |
|---|---|
| `DESIGNED` | 문서상 계약만 존재 |
| `MIGRATED_UNVERIFIED` | 독립 파일로 이식했으나 종합 검증 전 |
| `STATIC_ONLY` | 정적 검사만 통과 |
| `E2E_NOT_RUN` | 성공한 새 Codex 세션 종합검증 증거 없음. 실패·부분 시도 뒤에도 전체 통과 전까지 유지 |
| `ACTIVE_VERIFIED` | 신뢰된 프로젝트의 새 세션에서 발견·라우팅·훅까지 확인 |

P5 구현·교정·로컬검증과 P7 정적 종합검증에 더해 §1.1의 Windows 역사 증거와 §1.5의 WSL 새 task
실제 차단을 관찰했으므로, 현재 최고 상태는 **WSL에서 직접 관찰한 `PreToolUse`·WIP guard·
auto compact 범위의 `ACTIVE_VERIFIED`**다.
P8 1차 실패는 교정 전 역사로
[`P8 교정 보고`](P8_새세션_E2E_1차실패_원인분석_및_교정.md)에 보존한다.
프로젝트·모델 스모크는 §1.5의 2026-09-18 **사용자 실행 당시 범위에서 PASS**이고 후속 코드
변경분은 **E2E_NOT_RUN**이다.
Desktop 버전과 P8 최종 E2E에서 직접 실행하지 않은
guard·wrapper·단위 테스트·환경 검사기까지 `ACTIVE_VERIFIED`로 확대 해석하지 않는다.

## 8. 공식 Codex 구성 근거

- `AGENTS.md`는 지속 지침, 저장소 스킬은 `.agents/skills`에 둔다: [Customization overview](https://learn.chatgpt.com/docs/customization/overview)
- `AGENTS.md`는 루트부터 현재 디렉터리까지 계층적으로 적용된다: [Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- 프로젝트 설정은 신뢰된 저장소의 `.codex/config.toml`에서 읽고 상대경로는 `.codex` 기준이다: [Advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced)
- 프로젝트 훅은 `.codex/hooks.json` 또는 같은 층의 인라인 `[hooks]` 중 한 표현을 선택하며,
  비관리 훅은 정확한 구성 hash의 검토·신뢰가 필요하다. `PreToolUse`는 도구 실행 전에 차단할 수 있다:
  [Hooks](https://learn.chatgpt.com/docs/hooks)

P7은 스킬·설정·링크·훅 로컬 계약의 정적 증거를 제공한다. P8 1차에서는 훅 작동이 실패했지만,
교정 뒤 §1.1의 최종 E2E에서 `AGENTS.md`·17개 스킬 발견과 교정된 Windows handler의 실제
차단을 관찰했다. `/hooks` enabled·trusted와 새 hash 신뢰는 사용자 확인 전제이며 이번 세션에서
UI를 독립 조회한 증거로 바꾸어 쓰지 않는다.
