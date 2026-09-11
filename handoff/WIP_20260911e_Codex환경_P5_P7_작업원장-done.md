# WIP 작업원장 — 2026-09-11 Codex 환경 P5·P7 (완료)

- **세션 시작**: 2026-09-11
- **직전 유효 핸드오프**: `handoff/202609110159_HANDOFF.md` (이름·mtime 후보 대조)
- **승인 제안서**: `proposal/done/20260911_Codex-작업환경-완전분리-구축-approved.md`
- **변경 허용범위**: P5 `.codex/hooks.json`·`.codex/hooks/**`, P7 검증에 직접 필요한 Codex 환경 파일·검증 보고·상태 문서, 이 WIP, 최종 핸드오프
- **명시적 제외**: P8 실제 새 세션 E2E, `datasets/TinyDataset/**`, 루트 09 수정·복제, 제품·모델·실험 코드 변경, GPU·학습·모델 로딩·동적 스모크, 삭제·staging·commit·push·PR

## 사용자 지시 원문

> Codex 분리 계약 ai\_dev\_tool/Codex/README.md 에 따라 P5, P7 착수. proposal/done/20260911\_Codex-작업환경-완전분리-구축-approved.md 제안서, ai\_dev\_tool/Codex/temp\_AGENTS.MD\_항목별\_00\_08\_이식목록.md 문서 참고할 것. P8 새 세션 E2E는 테스트방법 사용자에게 안내바람
>
> 세션 핸드오프 메모 작성 및 이번 작업내용에 대해 한국어 커밋메시지 제목과 내용 제안바람.

## 진행 상황판

| # | 사용자 지시 | 상태 | 산출물 | 이어받을 지점 |
|---|---|---|---|---|
| **1** | `Codex 분리 계약 ai_dev_tool/Codex/README.md 에 따라 P5, P7 착수.` | ✅완료 | `.codex/hooks.json`, `.codex/hooks/**`, `.codex/check_environment.py`, `ai_dev_tool/Codex/P7_정적종합검증_보고.md` | P5 14/14, P7 20/20 PASS. P8 전 `STATIC_ONLY / E2E_NOT_RUN` |
| **2** | `proposal/done/20260911_Codex-작업환경-완전분리-구축-approved.md 제안서, ai_dev_tool/Codex/temp_AGENTS.MD_항목별_00_08_이식목록.md 문서 참고할 것.` | ✅완료 | 본 원장과 영향도 | 두 문서의 P5·P7 통과 조건을 작업 체크리스트로 반영 |
| **3** | `P8 새 세션 E2E는 테스트방법 사용자에게 안내바람` | ✅완료 | P7 보고 §6, 핸드오프·최종 보고의 사용자 절차 | 안전한 무쓰기 차단 probe와 통과 기준 확정. 실제 P8은 `NOT_RUN` |
| **4** | `세션 핸드오프 메모 작성 및 이번 작업내용에 대해 한국어 커밋메시지 제목과 내용 제안바람.` | ✅완료 | `handoff/202609111517_HANDOFF.md`, 한국어 제목·본문 | Codex 전용 구조 검사 PASS, 시각 감사 81/81 정합, commit은 제안만 하고 미수행 |

범례: ⏳대기 · 🔄진행 · ✅완료 · 🚫막힘(사유 기재)

## 착수 전 영향도

| 축 | 영향 | 내용 |
|---|---|---|
| 코드 | 있음 | `.codex/hooks/**`의 명령 입력 파서와 차단 응답을 Codex 공식 PreToolUse 계약으로 교체 |
| 데이터 | 없음 | 보호 데이터·체크포인트·로그에 접근하지 않음 |
| 테스트 | 있음 | P5 합성 정상·차단·경계·오류 입력, P7 구문·링크·경로·참조·불변성 종합검증 필요. P8은 별도 |
| 정본 문서 | 있음 | Codex README·06·07·제안서·이식표 상태와 별도 P7 검증 보고 동기화 |
| 기술부채·우선순위 | 있음 | 훅은 일부 도구 경로가 opt-out할 수 있고 신뢰 전에는 건너뛰므로 P8 전 `ACTIVE_VERIFIED` 금지 |
| GPU·학습·모델 로딩 분리 | 영향 없음 | 모두 `NOT_RUN` 유지 |
| 데이터·동시 작업 소유권 | 영향 없음 | `datasets/TinyDataset/**` 열람·열거·검색·해시·검사·수정·staging 0건 유지 |
| 비교 유효성 | 영향 없음 | 모델·실험 수치 비교를 수행하지 않음 |
| 증거 수준 | 있음 | P5 모의 검증과 P7 정적 통과까지만 `STATIC_ONLY / E2E_NOT_RUN`으로 판정 |
| 문서 연쇄 | 있음 | 환경 구축 상태 문서와 새 핸드오프만 갱신; 연구 결과 정본은 비영향 |

## 기준선 SHA-256

| 대상 | 바이트 | SHA-256 |
|---|---:|---|
| `AGENTS.md` | 14,057 | `573FF5D03CE782F59EF2910BF341946C144F2D9C3DEA631FF28326B652DAC5F1` |
| `.agents/project.json` | 3,103 | `FD910DF385500C547941A0CC12B7641D70B3612A6823395A4A27A791CCD33042` |
| `.codex/config.toml` | 782 | `6C14401D103AC5A28AD1B34EC463D54C38540017EBE7E149278D163CCABE2C6B` |
| `.codex/hooks.json` | 265 | `FF58951A377546B99487952CB859B5B3EF4A185A99D3A79C657897601DBA0F11` |
| `.codex/hooks/guard_backslash.py` | 7,591 | `38AF0E6430C53F3C0C68D9E274ED79B2877A7CBD99D867603CE459F9DBBC17FF` |
| `.codex/hooks/backslash_whitelist.tsv` | 2,101 | `6D6E70FE38330E90692C8FDA8899D33386C1C9B6AC9A99C1C1F6A13B32D3CD2C` |
| 루트 `ai_dev_tool/09_구현검증_필요목록.md` | 30,219 | `7FA13A5AD04B521056806A751DE1E289EB6EA9B648F68F8CF53D75E1AEA248D4` |

## 작업 로그 (append-only)

- `2026-09-11` 열린 WIP 0건, 최신 유효 공유 핸드오프 후보 `handoff/202609110159_HANDOFF.md`, 대상 Codex 환경 경로 Git 상태 clean을 확인하고 착수.
- `2026-09-11` 공식 OpenAI Docs에서 프로젝트 훅은 신뢰된 `<repo>/.codex/hooks.json`에서 발견되고, `PreToolUse`의 셸·통합 exec 표준 matcher가 `Bash`, 입력 명령이 `tool_input.command`, 차단은 `hookSpecificOutput.permissionDecision=deny` 또는 exit 2임을 확인.
- `2026-09-11` 공식 문서는 저장소 루트 기준 훅 경로 해석, 같은 계층의 `hooks.json`·인라인 `[hooks]` 중복 금지, 변경된 비관리 훅의 hash 재신뢰 필요, 일부 도구의 훅 opt-out 가능성을 명시하므로 이를 P5·P8 경계로 채택.
- `2026-09-11` `.codex/hooks.json`을 표준 `Bash` matcher와 저장소 루트 동적 해석으로 교체하고, `guard_backslash.py`를 Codex 공식 JSON 입출력 계약의 독립 구현으로 이식. 광범위한 도구·임시경로 우회는 제거하고 명시 예외 토큰만 유지.
- `2026-09-11` `python -I -B .codex/hooks/test_guard_backslash.py`: 정상·차단·Windows 경로 경계·실제 제어문자·명시 예외·손상 JSON·allowlist 실패를 포함한 14개 모의 테스트 PASS. 셸 쓰기나 실제 훅 활성화는 수행하지 않음.
- `2026-09-11` `.codex/check_environment.py`를 보호 데이터 비접근 허용목록 방식으로 작성. 첫 실행의 실제 끊긴 링크 1건(Codex 02의 비링크 표기)과 검사기 오탐을 교정.
- `2026-09-11` 최종 P7: `checks=20 passed=20 failed=0`. JSON/TOML/Python/PowerShell/셸 구문, 17개 스킬 계약, 링크 55개 문서, 금지 런타임 의존성 0건, 링크·junction·hardlink 0건, 루트 09 기준선 해시 일치를 확인.
- `2026-09-11` P8은 실행하지 않고, 프로젝트 신뢰·`/hooks` hash 검토·시작 라우팅·스킬 발견·정상 probe·`$false` 안전 차단 probe·하위 디렉터리 probe로 구성한 사용자 절차를 P7 보고 §6에 기록.
- `2026-09-11` 핸드오프 검사 직전 공유 `scripts/check_handoff.py`가 다른 에이전트 환경 진입 파일을 직접 읽는 숨은 의존성을 발견해 실행하지 않음. `.agents/skills/session-handoff/scripts/check_handoff_codex.py`를 독립 이식하고 스킬·Codex 02 라우팅을 교정.
- `2026-09-11` 독립 검사기 이식 뒤 P7 환경 검사 최종 `20/20 PASS` 재확인.
- `2026-09-11` 생성기 작성 `handoff/202609111517_HANDOFF.md`를 Codex 전용 검사기로 구조·로컬 링크 PASS, `scripts/handoff_time.py`로 전체 81건 시각 모순 0·정합 81 확인.
- `2026-09-11` 네 사용자 지시를 모두 완료. P8 실제 새 세션 E2E만 사용자 수행 항목으로 남기고, 커밋 메시지는 제안만 하며 staging·commit·push는 수행하지 않음.
