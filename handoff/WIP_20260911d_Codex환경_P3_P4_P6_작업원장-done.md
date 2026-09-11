# WIP 작업원장 — 2026-09-11 Codex 환경 P3·P4·P6 — 완료

- **세션 시작**: 2026-09-11
- **직전 핸드오프**: `handoff/202609110159_HANDOFF.md`
- **승인 제안서**: `proposal/done/20260911_Codex-작업환경-완전분리-구축-approved.md`
- **사용자 지시 원문**: 아래 인용이 정본이며, 진행 상황판은 이를 단계별로 분해한 것이다.
- **변경 허용범위**: P3 `.agents/project.json`·`.codex/config.toml`, P4 `.agents/skills/**`, P6 `AGENTS.md`, 직접 연관된 Codex 상태 문서와 이 원장
- **명시적 제외**: P5 `.codex/hooks.json`·`.codex/hooks/**`, P7 종합검증, P8 새 세션 E2E, 루트 09, 데이터셋·제품 코드, 학습·GPU·모델 로딩·스모크, 삭제·commit·push·PR

> Codex 분리 계약 ai_dev_tool/Codex/README.md 에 따라 P3, P4, P6 착수. proposal/done/20260911_Codex-작업환경-완전분리-구축-approved.md 제안서, ai_dev_tool/Codex/temp_AGENTS.MD_항목별_00_08_이식목록.md 문서 참고할 것. P5 훅은 및 P7, P8은 이번작업 끝나고 별도로 수행예정.

## 진행 상황판

| # | 작업 단위 | 상태 | 산출물 | 이어받을 지점 |
|---|---|---|---|---|
| **1** | P3 Codex 네이티브 설정과 스킬 프로젝트 메타데이터를 분리 작성 | ✅완료 | `.codex/config.toml`, `.agents/project.json` | JSON/TOML 구문·선언 경로·사용자 절대경로 0건 제한 확인 통과. 훅 선언 없음 |
| **2** | P4 17개 스킬과 부속 파일을 Codex·Windows 환경에 맞춰 독립 이식 | ✅완료 | `.agents/skills/**` | 17/17 이름·진입 파일·Codex 표지 확인. 레거시 런타임 참조·루트 00~08 참조·reparse point 0건. P7은 `NOT_RUN` |
| **3** | P6 `AGENTS.md`를 16 KiB 이하의 Codex 진입 규범으로 축약·전환 | ✅완료 | `AGENTS.md` | 890행·100,960바이트 → 219행·14,057바이트. 안전 앵커 보존·동적 상태 하드코딩 제한 확인 |
| **4** | P3·P4·P6 상태 문서 동기화와 범위 확인 | ✅완료 | Codex README·06·07, 승인 제안서, 이식표, 이 원장 | P5·P7·P8 `NOT_RUN`, 루트 09·P5 훅 기준선 해시 불변 기록 |

범례: ⏳대기 · 🔄진행 · ✅완료 · 🚫막힘(사유 기재)

## 착수 전 영향도

| 축 | 영향 | 내용 |
|---|---|---|
| 코드 | 없음 | `tinylm/**`, 실행 배치, 프로젝트 스크립트는 수정하지 않음 |
| 데이터 | 없음 | 데이터셋 팀 경로를 열람·열거·검색·해시·검사·수정·staging하지 않음 |
| 테스트 | 있음 | P4 파일 자체 구조 확인까지만 수행. P7 종합검증과 P8 E2E는 별도 작업으로 남김 |
| 정본 문서 | 있음 | README·Codex 06/07·승인 제안서의 단계 상태를 P3/P4/P6에 맞춰 동기화 |
| 기술부채·우선순위 | 있음 | P5 훅이 미이식이므로 환경 전체 완료를 선언하지 않고 `MIGRATED_UNVERIFIED / E2E_NOT_RUN` 유지 |
| 안전·권한 | 있음 | PR·핸드오프 스킬은 외부 상태를 실제 변경하지 않고 계약만 이식. 삭제·commit·push 금지 유지 |
| 환경 분리 | 있음 | 활성 Codex 파일에서 `.claude/**`, `CLAUDE.md`, 잘못된 `.Codex/**` 런타임 의존 제거 |

## 기준선(SHA-256)

| 대상 | 상태/크기 | SHA-256 |
|---|---:|---|
| `AGENTS.md` | 100,960 bytes | `382205FECFF91B808C95044FF337E9713B1E37953F36EE291BADDBC7BA14E79E` |
| `ai_dev_tool/09_구현검증_필요목록.md` | 30,219 bytes | `7FA13A5AD04B521056806A751DE1E289EB6EA9B648F68F8CF53D75E1AEA248D4` |
| `ai_dev_tool/Codex/temp_AGENTS.MD_항목별_00_08_이식목록.md` | 25,761 bytes | `1C7D57EE7821AE291160EA023BCD0F0FD735089898ED29A548878895DCC830AC` |
| `.codex/hooks.json` | 265 bytes | `FF58951A377546B99487952CB859B5B3EF4A185A99D3A79C657897601DBA0F11` |
| `.codex/hooks/guard_backslash.py` | 7,591 bytes | `38AF0E6430C53F3C0C68D9E274ED79B2877A7CBD99D867603CE459F9DBBC17FF` |
| `.codex/hooks/backslash_whitelist.tsv` | 2,101 bytes | `6D6E70FE38330E90692C8FDA8899D33386C1C9B6AC9A99C1C1F6A13B32D3CD2C` |
| `.agents/project.json` | 없음 | P3 신설 대상 |
| `.codex/config.toml` | 없음 | P3 신설 대상 |

착수 시 활성 미완료 WIP는 없었다. `.agents/skills`에는 17개 디렉터리가 있으며 P4 전에는 부분 기계 사본으로 취급한다.

## 작업 로그 (append-only)

- `2026-09-11` 사용자 승인 범위를 P3·P4·P6으로 고정. P5·P7·P8은 별도 작업으로 제외.
- `2026-09-11` 공식 OpenAI 문서에서 저장소 지침은 루트 `AGENTS.md`, 프로젝트 스킬은 `.agents/skills`, 신뢰된 프로젝트 설정은 `.codex/config.toml`임을 재확인. 프로젝트 설정에서 훅은 중복 선언하지 않기로 고정.
- `2026-09-11` P5 소유 파일 3개의 해시를 기준선으로 기록하고 수정 금지 경계 설정.
- `2026-09-11` P3: `.agents/project.json`에 TinyLM 경로·정본·영향축·제외경로·증거상태를, `.codex/config.toml`에 공식 Codex 프로젝트 문서 설정만 분리 작성. local main과 origin HEAD master의 충돌 때문에 `baseBranch`는 `null`로 두고 PR 시 사용자 확인 계약을 기록.
- `2026-09-11` P3 파일 단위 확인: PowerShell JSON 파싱, Python 표준 `tomllib` 파싱, 선언 경로 존재, 사용자 종속 절대경로 0건을 확인. 저장소 검사기나 프로젝트 스크립트는 실행하지 않음.
- `2026-09-11` P4: 17개 `SKILL.md`와 필요한 참고자료·템플릿·보조 스크립트를 Codex 질문·별도 승인·PowerShell 우선·TinyLM 정본 경로로 이식. `check-and-verify` Codex 절차와 PR workflow PowerShell 보조 스크립트를 독립 파일로 신설.
- `2026-09-11` P4 제한 확인: 17/17 디렉터리·선언 이름·Codex 이식 표지 일치, `.claude`·`CLAUDE.md`·`AskUserQuestion`·잘못된 `.Codex/project.json` 런타임 참조 0건, 루트 00~08 참조 0건, reparse point 0건. 스킬·보조 스크립트 실제 실행과 P7 종합검증은 하지 않음.
- `2026-09-11` P6: `AGENTS.md`를 영구 안전경계와 동적 라우팅만 남긴 219행·14,057바이트 Codex 진입 규범으로 전환. 특정 최신 핸드오프 파일명·고정 게이트 수·표준모델·분해능 하드코딩을 제거.
- `2026-09-11` Codex README·06·07, 승인 제안서, 임시 항목별 이식표를 P3·P4·P6 완료 및 `MIGRATED_UNVERIFIED / E2E_NOT_RUN` 상태로 동기화.
- `2026-09-11` 종료 보호 확인: 루트 09와 `.codex/hooks.json`, `guard_backslash.py`, `backslash_whitelist.tsv`의 SHA-256이 착수 전과 동일하고 Codex 09 사본은 0개.
- `2026-09-11` P5 훅 이식·실행, P7 정적 종합검증, P8 새 세션 E2E, 데이터셋 접근, GPU·학습·모델 로딩·스모크, 삭제·commit·push·PR은 모두 `NOT_RUN` 또는 0건.

## 완료 판정

- 승인된 P3·P4·P6 산출물 작성: **완료**
- 환경 전체 증거 수준: **`MIGRATED_UNVERIFIED / E2E_NOT_RUN`**
- 남은 별도 단계: **P5·P7·P8**
- 최종 `AGENTS.md`: `573FF5D03CE782F59EF2910BF341946C144F2D9C3DEA631FF28326B652DAC5F1`
- 최종 `.agents/project.json`: `FD910DF385500C547941A0CC12B7641D70B3612A6823395A4A27A791CCD33042`
- 최종 `.codex/config.toml`: `6C14401D103AC5A28AD1B34EC463D54C38540017EBE7E149278D163CCABE2C6B`
