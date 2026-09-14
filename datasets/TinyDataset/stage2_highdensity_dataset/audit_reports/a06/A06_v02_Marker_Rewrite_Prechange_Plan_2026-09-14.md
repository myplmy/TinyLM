# A06 v02 표식 제거 재서술 — 10 locator 변경 계획

## 1. 범위와 사전 상태

- 작성 시각: 2026-09-14 KST
- 승인 근거: 사용자의 A06 재개 지시와 A04 팀의 2026-09-14 locator 동기화 절차.
- 대상 source: `sources/train/stage2_(16)relational_composition_high_density_train_v02.source.psv`의 물리 행 2~11(헤더는 행 1).
- 대상 registry: `sources/term_registry/stage2_(16)relational_composition_train_registry_v01_v52.jsonl`의 같은 `source_file + source_line` 10 locator.
- 수정 전 v02 source SHA-256: `7E732D7306149E0EA3E82493E15E5DA474C604F77B8C190DCBA66D4CEBBFB647`.
- 수정 전 A06 source-set SHA-256: `87BEB2DBE900E522212E713D0798C0E12E28FC3135618D9B2F9E16A4FD150663`.
- 수정 전 registry SHA-256: `15A9429AB0F5A6C383E487A443705F834EC68C1C384C8834B31556D55ED98C29`.
- 기준 수량: source 52 files·7,800 records, registry 7,800 JSONL rows.

`concept`는 legacy PSV의 실제 primary field이고, registry의 `primary`는 그것의 대조용 복사값이다. locator는 `source_file + source_line`이며 행 삽입·삭제·순서 변경을 하지 않는다.

## 2. 착수 전 영향도 분석

| 파일·경로 | 예정 동작 | 권한 근거 | NOT_RUN·제외 |
|---|---|---|---|
| `stage2_(16)...train_v02.source.psv` | 10행의 `concept`·`text`만 직접 재서술 | A06 source v02~v52와 자연성 재서술 승인 | v01·v03~v52는 이번 묶음 제외 |
| `stage2_(16)...registry_v01_v52.jsonl` | 같은 10 locator의 `primary`만 변경 | A04 동기화 절차 3항 | locator·definition·provenance·review_status 및 비대상 7,790행 보존 |
| `tools/a06/...updater.js` | A06 전용 line-preserving updater 신설·fixture 검증 | A04 권장안 B | 공용 감사기·다른 영역 도구 수정 금지 |
| `audit_reports/.../a06` | 계획·fixture·검증 결과 기록 | A06 전용 감사 산출물 허용 | 중앙 원장·manifest·package·train/val·checkpoint 제외 |

| 축 | 영향 | 내용 |
|---|---|---|
| 코드 | 있음 | A06 전용 updater 1개만 신설한다. 공용 builder·auditor의 호출부는 추가하지 않는다. |
| 데이터 | 있음 | source 10행의 concept/text와 registry 10행의 primary만 달라진다. relations·other_type·행 수·행 순서는 보존한다. |
| 테스트 | 있음 | 비정본 fixture에서 target 10행만 달라지고 비대상 행 바이트가 동일한지 확인한 뒤 canonical precondition·정합성 검사를 실행한다. |
| 정본 문서 | 없음 | `.agents/project.json`의 공용 docImpactTargets, 설계서, 중앙 원장은 이번 source-only 수정 대상이 아니다. |
| 기술부채·우선순위 | 있음 | 전역 직렬화·전역 치환을 금지하고 expected-old-primary를 요구해 잘못된 행 갱신을 차단한다. |
| 데이터셋·동시 작업 소유권 | 있음 | A06 source/registry/audit artifact만 변경한다. 다른 영역·공용 산출물은 해시 확인만 한다. |
| 증거 수준 | 있음 | fixture 검증은 `STATIC_ONLY`이며, source-only 수정은 package·checkpoint·학습 품질 검증을 뜻하지 않는다. |

## 3. registry 갱신 방식 비교와 선택

| 안 | 내용 | 장점 | 단점 | 영향도 | 수행비용 |
|---|---|---|---|---|---|
| A | `apply_patch`로 registry JSONL 10행 직접 수정 | 가장 좁은 diff | 현 4MB 파일에서 바이트 경계 오류가 재현돼 성공 경로가 없음 | 낮음 | 낮음이나 불확실 |
| B | A06 전용 line-preserving updater를 fixture에서 검증한 뒤 10 locator만 갱신 | expected-old 값·JSON·비대상 바이트를 기계 검증 | 전용 도구와 fixture가 필요 | 중간, A06 한정 | 중간 |
| C | source 재서술을 보류하고 HOLD 유지 | 정본 변경 위험 0 | 표식 문제와 자연성 HOLD가 그대로 남음 | 없음 | 낮음 |

**선택: B.** A04 권장안이며, source와 registry의 같은 locator를 하나의 변경 묶음으로 검증할 수 있다. canonical 적용 전 fixture가 실패하거나 precondition이 달라지면 변경하지 않고 HOLD로 돌아간다.

## 4. locator별 변경 계획

공통 조건: relations는 원문 그대로 보존한다. registry에서는 `primary`만 새 concept로 바꾸며 `definition`, `term_kind`, `provenance_kind`, `provenance_ref`, `review_status`는 변경하지 않는다. 각 새 concept는 A06 전체에서 기존 exact concept 중복 0, 새 text의 concept literal 포함 `true`, ` — ` 표식 포함 `false`를 사전 확인했다.

| locator | 기존 concept → 새 concept | registry primary | relations 보존 | 의미 검토 근거 |
|---|---|---|---|---|
| `v02:2` | `양액 탱크와 환기창의 저부하 운전 충돌 조정 — 경로 보존` → `양액 탱크와 환기창의 저부하 운전 충돌 조정` | 같은 변경 | `state, contrast, comparison` | 저부하 운전의 충돌·통상/제한 처리 대비는 보존하고 검수 표식만 제거한다. |
| `v02:3` | `배수관 우선 압력 조절기 예외의 부분 회복 경로 — 결과 검증` → `배수관 우선 압력 조절기의 부분 복구 기준` | 같은 변경 | `classification, boundary, function` | 예외 조건에서 일부 조치를 보류하는 적용 기준을 더 자연스러운 명사구로 명시한다. |
| `v02:4` | `원격 관찰에서 함수율 센서와 환경 제어기를 가르는 환기창 기준 — 영향 검토` → `원격 관찰에서 함수율 센서와 환경 제어기를 구분하는 환기창 기준` | 같은 변경 | `process, state, contrast` | 두 기록·지시를 구별하는 기준이라는 원래 관계를 유지한다. |
| `v02:5` | `재배 베드 기록과 관수 밸브 지시의 대체 자원 우선순위 — 예외 점검` → `재배 베드 기록과 관수 밸브 지시 사이의 대체 자원 우선순위` | 같은 변경 | `boundary, role, attribute` | 충돌 상황의 대체 자원 우선순위와 재판정 과정을 유지한다. |
| `v02:6` | `순환팬과 기상 예보가 만날 때 양액 탱크를 보류하는 판단 — 독립 확인` → `순환팬 운전과 기상 예보가 충돌할 때 양액 탱크 보충을 보류하는 판단` | 같은 변경 | `boundary, comparison, state` | 모호한 ‘만날 때’를 실제 충돌·보충 보류 판단으로 구체화한다. |
| `v02:7` | `차광 모터와 환기창의 복구 직후 충돌 조정 — 분기 기록` → `차광 모터와 환기창의 복구 직후 충돌 조정` | 같은 변경 | `process, boundary, role` | 복구 직후 규칙·예외 충돌의 조정이라는 원 뜻을 보존한다. |
| `v02:8` | `기상 예보 우선 순환팬 예외의 재검 표본 경로 — 중간 판정` → `기상 예보를 우선하는 순환팬 운전의 재검토 경로` | 같은 변경 | `state, contrast, comparison` | 정책 기록과 현장 신호의 충돌을 재검토하는 경로로 자연화한다. |
| `v02:9` | `초기 입력에서 관수 밸브와 재배 베드를 가르는 압력 조절기 기준 — 신호 전달` → `초기 입력에서 관수 밸브와 재배 베드를 구분하는 압력 조절기 기준` | 같은 변경 | `classification, boundary, function` | 두 대상의 입력·기준 구분과 최신성 검토를 보존한다. |
| `v02:10` | `환경 제어기 기록과 함수율 센서 지시의 전원 대기 우선순위 — 대상 추적` → `전원 대기 상태에서 환경 제어기 기록과 함수율 센서 지시의 우선순위` | 같은 변경 | `process, state, contrast` | 전원 대기 상태의 기록·지시 우선순위 및 예외 승인을 보존한다. |
| `v02:11` | `압력 조절기와 배수관이 만날 때 작업 기록을 보류하는 판단 — 순서 기록` → `압력 조절기와 배수관의 지시가 충돌할 때 작업 기록을 보류하는 판단` | 같은 변경 | `boundary, role, attribute` | 모호한 ‘만날 때’를 지시 충돌·예외 승인에 따른 기록 보류로 구체화한다. |

## 5. 계획된 새 source 행

```text
양액 탱크와 환기창의 저부하 운전 충돌 조정|state,contrast,comparison||양액 탱크와 환기창의 저부하 운전 충돌 조정에서는 예외 목록을 검토해 통상 처리와 제한 처리를 구분하고, 한 번의 예외를 영구 규칙으로 삼지 않는다.
배수관 우선 압력 조절기의 부분 복구 기준|classification,boundary,function||배수관 우선 압력 조절기의 부분 복구 기준은 기본 경로가 열려 있어도 예외 조건이 충족되면 일부 조치를 보류하고, 보류 범위와 적용 시점을 함께 정한다.
원격 관찰에서 함수율 센서와 환경 제어기를 구분하는 환기창 기준|process,state,contrast||원격 관찰에서 함수율 센서와 환경 제어기를 구분하는 환기창 기준은 두 기록을 대조해 기본 지시와 예외 지시의 우선순위를 정하고, 서로 다른 출처를 하나의 사실로 합치지 않는다.
재배 베드 기록과 관수 밸브 지시 사이의 대체 자원 우선순위|boundary,role,attribute||경보가 겹치면 재배 베드 기록과 관수 밸브 지시 사이의 대체 자원 우선순위에 따라 먼저 확인할 조건을 정하고 나머지 항목은 대기시킨다. 조건이 해소되면 대기 항목을 다시 판정한다.
순환팬 운전과 기상 예보가 충돌할 때 양액 탱크 보충을 보류하는 판단|boundary,comparison,state||순환팬 운전과 기상 예보가 충돌할 때 양액 탱크 보충을 보류하는 판단은 교대 기록의 우선순위와 적용 범위를 다시 확인해 충돌을 숨기지 않는다. 같은 대상에 두 지시를 동시에 부여하지 않는다.
차광 모터와 환기창의 복구 직후 충돌 조정|process,boundary,role||차광 모터와 환기창의 복구 직후 충돌 조정에서는 운영표의 규칙과 예외를 구분하고, 충돌한 근거의 출처를 남긴다.
기상 예보를 우선하는 순환팬 운전의 재검토 경로|state,contrast,comparison||기상 예보를 우선하는 순환팬 운전의 재검토 경로는 정책 기록과 현장 신호가 맞지 않을 때 충돌한 두 관계를 병렬로 보존하고, 한쪽을 지워 단일 경로로 만들지 않는다.
초기 입력에서 관수 밸브와 재배 베드를 구분하는 압력 조절기 기준|classification,boundary,function||초기 입력에서 관수 밸브와 재배 베드를 구분하는 압력 조절기 기준은 두 담당자의 표가 다를 때 어느 표가 최신인지 확인하고, 최신성 판단과 내용의 타당성을 별도로 남긴다.
전원 대기 상태에서 환경 제어기 기록과 함수율 센서 지시의 우선순위|process,state,contrast||전원 대기 상태에서 환경 제어기 기록과 함수율 센서 지시의 우선순위는 일치하는 기록과 어긋난 기록을 나누고, 예외가 승인됐는지 확인한다. 승인되지 않은 예외는 실행 근거가 아니다.
압력 조절기와 배수관의 지시가 충돌할 때 작업 기록을 보류하는 판단|boundary,role,attribute||압력 조절기와 배수관의 지시가 충돌할 때 작업 기록을 보류하는 판단에서는 기본 순서가 예외 승인으로 바뀐 지점을 표시하고, 변경되지 않은 단계는 원래 순서를 유지한다.
```

## 6. 원복용 원문

각 locator의 registry JSON은 `primary`만 source의 기존 concept와 같은 값이다. 아래 행은 source 원문 및 registry 원문이며, fixture 또는 canonical precondition이 실패하면 이 값으로 복원하지 않고 source·registry를 모두 변경 전 상태로 유지한다.

```text
[source v02:2] 양액 탱크와 환기창의 저부하 운전 충돌 조정 — 경로 보존|state,contrast,comparison||예외 목록을 검토하면서 양액 탱크와 환기창의 저부하 운전 충돌 조정 — 경로 보존은 통상 처리와 제한 처리를 갈라 적는다. 한 번의 예외를 영구 규칙으로 만들지 않는다.
[source v02:3] 배수관 우선 압력 조절기 예외의 부분 회복 경로 — 결과 검증|classification,boundary,function||기본 경로가 열려 있어도 배수관 우선 압력 조절기 예외의 부분 회복 경로 — 결과 검증은 예외 조건이 충족되면 일부 조치를 보류한다. 보류 범위와 적용 시점을 함께 기록한다.
[source v02:4] 원격 관찰에서 함수율 센서와 환경 제어기를 가르는 환기창 기준 — 영향 검토|process,state,contrast||두 기록을 대조하면 원격 관찰에서 함수율 센서와 환경 제어기를 가르는 환기창 기준 — 영향 검토는 기본 지시와 예외 지시를 분리해 우선순위를 정한다. 서로 다른 출처를 하나의 사실로 합치지 않는다.
[source v02:5] 재배 베드 기록과 관수 밸브 지시의 대체 자원 우선순위 — 예외 점검|boundary,role,attribute||경보가 겹친 상황에서는 재배 베드 기록과 관수 밸브 지시의 대체 자원 우선순위 — 예외 점검은 먼저 확인할 조건을 정하고 나머지는 대기시킨다. 조건이 풀리면 대기 항목을 다시 판정한다.
[source v02:6] 순환팬과 기상 예보가 만날 때 양액 탱크를 보류하는 판단 — 독립 확인|boundary,comparison,state||교대 기록에서 순환팬과 기상 예보가 만날 때 양액 탱크를 보류하는 판단 — 독립 확인은 우선순위와 적용 범위를 다시 확인해 충돌을 숨기지 않는다. 같은 대상에 두 지시를 동시에 부여하지 않는다.
[source v02:7] 차광 모터와 환기창의 복구 직후 충돌 조정 — 분기 기록|process,boundary,role||운영표에는 차광 모터와 환기창의 복구 직후 충돌 조정 — 분기 기록은 먼저 적용할 규칙과 나중에 살필 예외가 함께 적힌다. 충돌한 근거의 출처를 남긴다.
[source v02:8] 기상 예보 우선 순환팬 예외의 재검 표본 경로 — 중간 판정|state,contrast,comparison||정책 기록과 현장 신호가 맞지 않으면 기상 예보 우선 순환팬 예외의 재검 표본 경로 — 중간 판정은 충돌한 두 관계를 병렬로 보존한다. 한쪽을 지우고 단일 경로로 만들지 않는다.
[source v02:9] 초기 입력에서 관수 밸브와 재배 베드를 가르는 압력 조절기 기준 — 신호 전달|classification,boundary,function||두 담당자의 표가 다를 때 초기 입력에서 관수 밸브와 재배 베드를 가르는 압력 조절기 기준 — 신호 전달은 어느 표가 최신인지 확인한다. 최신이라는 판단과 내용의 타당성은 별도로 남긴다.
[source v02:10] 환경 제어기 기록과 함수율 센서 지시의 전원 대기 우선순위 — 대상 추적|process,state,contrast||판정 담당은 환경 제어기 기록과 함수율 센서 지시의 전원 대기 우선순위 — 대상 추적은 일치하는 기록과 어긋난 기록을 나누고 예외가 승인됐는지 확인한다. 승인되지 않은 예외는 실행 근거가 아니다.
[source v02:11] 압력 조절기와 배수관이 만날 때 작업 기록을 보류하는 판단 — 순서 기록|boundary,role,attribute||관리자는 압력 조절기와 배수관이 만날 때 작업 기록을 보류하는 판단 — 순서 기록은 기본 순서가 예외 승인으로 바뀐 지점을 표시한다. 변경되지 않은 단계는 원래 순서를 유지한다.
```

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":2,"primary":"양액 탱크와 환기창의 저부하 운전 충돌 조정 — 경로 보존","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":3,"primary":"배수관 우선 압력 조절기 예외의 부분 회복 경로 — 결과 검증","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":4,"primary":"원격 관찰에서 함수율 센서와 환경 제어기를 가르는 환기창 기준 — 영향 검토","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":5,"primary":"재배 베드 기록과 관수 밸브 지시의 대체 자원 우선순위 — 예외 점검","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":6,"primary":"순환팬과 기상 예보가 만날 때 양액 탱크를 보류하는 판단 — 독립 확인","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":7,"primary":"차광 모터와 환기창의 복구 직후 충돌 조정 — 분기 기록","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":8,"primary":"기상 예보 우선 순환팬 예외의 재검 표본 경로 — 중간 판정","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":9,"primary":"초기 입력에서 관수 밸브와 재배 베드를 가르는 압력 조절기 기준 — 신호 전달","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":10,"primary":"환경 제어기 기록과 함수율 센서 지시의 전원 대기 우선순위 — 대상 추적","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":11,"primary":"압력 조절기와 배수관이 만날 때 작업 기록을 보류하는 판단 — 순서 기록","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

## 7. canonical 적용 전후의 강제 확인

1. source와 registry의 SHA-256·행 수를 다시 읽고 위 precondition과 일치시킨다.
2. fixture에서 10 target line만 `primary`가 바뀌고 비대상 line bytes가 모두 동일한지 검증한다.
3. source·registry를 같은 변경 묶음으로 반영하되 source 실패 또는 registry 실패 시 둘 다 원문으로 유지한다.
4. JSON parse, 7,800 locator 수, source-only locator 0, registry-only locator 0, duplicate locator 0, source `concept`↔registry `primary` mismatch 0을 확인한다.
5. v01, v03~v52, 비대상 registry 7,790행, 다른 영역, package/train/val, manifest, 중앙 원장, 공용 감사기는 변경하지 않는다.
6. A06 전체 자연성·TF-IDF·Jaccard 감사는 v02~v52 표식 재서술 완료 뒤에만 실행한다.
