# A06 v02 표식형 primary 재서술 — 사전 변경계획 (physical line 22~31)

## 범위와 사전조건

- 대상 source: `stage2_(16)relational_composition_high_density_train_v02.source.psv`의 physical line 22~31만.
- 대상 registry locator: 같은 source file의 `source_line` 22~31만. registry에서는 `primary`만 변경한다.
- 수정 전 SHA-256: source v02 `159CB88766D2C066F86E5D84349D7ACF6C6E804F88AD7469CE14CCE441C1C449`, registry `92CBBEDB146E5F55564823B3F309D3928B15EC99E2659639F5075A53B7A47DF1`.
- 수정 전 행 수: source v02 150 data rows, registry 7,800 JSONL rows.
- v01, 다른 A06 source 행, 다른 영역, manifest, 중앙 원장, 공용 train/val·감사기·checkpoint는 변경하지 않는다.
- 새 primary 10개는 A06 전체 existing exact primary와의 충돌 0, 묶음 내부 중복 0을 사전 확인했다.

## locator별 변경안

| locator | 기존 concept / registry primary | 새 concept / registry primary | relations 보존 | 의미 검토 근거 |
|---|---|---|---|---|
| v02:22 | 환경 제어기와 함수율 센서의 승인 전 충돌 조정 — 예외 점검 | 환경 제어기와 함수율 센서의 승인 전 충돌 조정 | `process,state,contrast` | `예외 점검`은 개념이 아닌 검수 표식이다. 승인 전 충돌을 통상·제한 처리의 대비와 연결해 절차·상태 의미를 유지한다. |
| v02:23 | 압력 조절기 우선 배수관 예외의 정기 종료 경로 — 독립 확인 | 압력 조절기를 우선하는 배수관 운전 예외의 종료 절차 | `boundary,role,attribute` | 어색한 명사 나열과 `독립 확인` 표식을, 우선 운전 예외의 종료·보류 범위를 정하는 절차로 풀어 쓴다. |
| v02:24 | 주기 판정에서 환기창과 양액 탱크를 가르는 기상 예보 기준 — 분기 기록 | 주기별 운전에서 환기창과 양액 탱크를 구분하는 기상 예보 기준 | `boundary,comparison,state` | `분기 기록`은 기록 표식이다. 기상 예보에 따라 두 운전 대상을 구분하는 기준으로 자연스럽게 재서술한다. |
| v02:25 | 작업 기록 기록과 순환팬 지시의 자동 복귀 우선순위 — 중간 판정 | 작업 기록과 순환팬 지시의 자동 복귀 순서 | `process,boundary,role` | 중복된 `기록`과 `중간 판정` 표식을 제거하고, 경보 후 복귀 순서를 정하는 관계 조합으로 명확화한다. |
| v02:26 | 양액 탱크와 환기창이 만날 때 환경 제어기를 보류하는 판단 — 신호 전달 | 양액 탱크와 환기창 충돌 시 환경 제어기 보류 판단 | `state,contrast,comparison` | `만날 때`와 `신호 전달` 표식을 실제 운영 충돌·보류 판단으로 바꿔 대상·조건·결정을 드러낸다. |
| v02:27 | 배수관과 압력 조절기의 야간 점검 충돌 조정 — 대상 추적 | 배수관과 압력 조절기의 야간 점검 충돌 조정 | `classification,boundary,function` | 이미 자연스러운 중심 명사구에서 `대상 추적` 표식만 제거한다. 규칙과 예외의 구분·적용 기능은 text에서 명시한다. |
| v02:28 | 함수율 센서 우선 환경 제어기 예외의 승인 전 경로 — 순서 기록 | 함수율 센서를 우선하는 환경 제어기 예외의 승인 절차 | `process,state,contrast` | 부자연스러운 조사 생략과 `순서 기록` 표식을, 센서 우선 예외를 승인하는 절차로 바꾼다. |
| v02:29 | 교대 인계에서 재배 베드와 관수 밸브를 가르는 차광 모터 기준 — 상태 묶음 | 교대 인계에서 재배 베드와 관수 밸브를 구분하는 차광 모터 기준 | `boundary,role,attribute` | `상태 묶음`은 표식이다. 교대 인계의 최신성 판단에서 두 대상을 구분하는 차광 모터 기준을 보존한다. |
| v02:30 | 순환팬 기록과 기상 예보 지시의 현장 인계 우선순위 — 우선 처리 | 순환팬 기록과 기상 예보 지시의 현장 인계 우선순위 | `boundary,comparison,state` | `우선 처리`는 표식이다. 두 출처가 충돌할 때 현장 인계에 적용할 우선순위로 직접 표현한다. |
| v02:31 | 차광 모터와 환기창이 만날 때 관수 밸브를 보류하는 판단 — 연결 확인 | 차광 모터와 환기창 충돌 시 관수 밸브 보류 판단 | `process,boundary,role` | `연결 확인`은 표식이다. 충돌 조건에서 밸브 조치를 보류하는 판단으로 의미를 분명히 한다. |

## 예정 text 재서술

각 행은 새 concept literal을 text에 정확히 한 번 포함하고, 기존 relations 및 빈 `other_type`을 보존한다.

1. `환경 제어기와 함수율 센서의 승인 전 충돌 조정은 예외 목록을 살펴 통상 처리와 제한 처리를 구분하고, 한 번 승인된 예외를 영구 규칙으로 취급하지 않도록 하는 절차다.`
2. `압력 조절기를 우선하는 배수관 운전 예외의 종료 절차는 기본 경로가 열려 있어도 예외 조건이 남아 있으면 일부 조치를 보류하고, 보류 범위와 종료 시점을 함께 정하는 절차다.`
3. `주기별 운전에서 환기창과 양액 탱크를 구분하는 기상 예보 기준은 두 기록을 대조하여 기본 지시와 예외 지시의 우선순위를 정하고, 서로 다른 출처의 정보를 하나의 사실로 합치지 않도록 한다.`
4. `작업 기록과 순환팬 지시의 자동 복귀 순서는 경보가 겹친 상황에서 먼저 확인할 조건을 정하고, 나머지 항목은 대기시켰다가 조건이 해소되면 다시 판단하는 순서다.`
5. `양액 탱크와 환기창 충돌 시 환경 제어기 보류 판단은 교대 기록의 우선순위와 적용 범위를 다시 확인하여 충돌을 숨기지 않고, 같은 대상에 두 지시를 동시에 부여하지 않도록 하는 판단이다.`
6. `배수관과 압력 조절기의 야간 점검 충돌 조정은 운영표에서 먼저 적용할 규칙과 나중에 검토할 예외를 구분하고, 충돌한 근거의 출처를 남기는 조정 절차다.`
7. `함수율 센서를 우선하는 환경 제어기 예외의 승인 절차는 정책 기록과 현장 신호가 맞지 않을 때 충돌한 두 관계를 나란히 보존하고, 한쪽을 지워 단일 경로로 만들지 않도록 한다.`
8. `교대 인계에서 재배 베드와 관수 밸브를 구분하는 차광 모터 기준은 두 담당자의 표가 다를 때 어느 표가 최신인지 확인하고, 최신성 판단과 내용의 타당성을 분리해 남기는 기준이다.`
9. `순환팬 기록과 기상 예보 지시의 현장 인계 우선순위는 판정 담당자가 일치하는 기록과 어긋난 기록을 구분하고, 예외가 승인되었는지 확인하여 적용 순서를 정하는 기준이다. 승인되지 않은 예외는 실행 근거로 쓰지 않는다.`
10. `차광 모터와 환기창 충돌 시 관수 밸브 보류 판단은 기본 순서가 예외 승인으로 바뀐 지점을 표시하고, 변경되지 않은 단계는 원래 순서로 유지하는 판단이다.`

## 원복용 원문

아래 source 행과 registry JSON 행은 변경 전 원문이다. source 행의 relations·other_type은 모두 보존하고, registry에서는 각 행의 `primary` 토큰만 같은 locator에서 바꾼다.

### v02:22

```text
환경 제어기와 함수율 센서의 승인 전 충돌 조정 — 예외 점검|process,state,contrast||예외 목록을 검토하면서 환경 제어기와 함수율 센서의 승인 전 충돌 조정 — 예외 점검은 통상 처리와 제한 처리를 갈라 적는다. 한 번의 예외를 영구 규칙으로 만들지 않는다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":22,"primary":"환경 제어기와 함수율 센서의 승인 전 충돌 조정 — 예외 점검","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

### v02:23

```text
압력 조절기 우선 배수관 예외의 정기 종료 경로 — 독립 확인|boundary,role,attribute||기본 경로가 열려 있어도 압력 조절기 우선 배수관 예외의 정기 종료 경로 — 독립 확인은 예외 조건이 충족되면 일부 조치를 보류한다. 보류 범위와 적용 시점을 함께 기록한다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":23,"primary":"압력 조절기 우선 배수관 예외의 정기 종료 경로 — 독립 확인","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

### v02:24

```text
주기 판정에서 환기창과 양액 탱크를 가르는 기상 예보 기준 — 분기 기록|boundary,comparison,state||두 기록을 대조하면 주기 판정에서 환기창과 양액 탱크를 가르는 기상 예보 기준 — 분기 기록은 기본 지시와 예외 지시를 분리해 우선순위를 정한다. 서로 다른 출처를 하나의 사실로 합치지 않는다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":24,"primary":"주기 판정에서 환기창과 양액 탱크를 가르는 기상 예보 기준 — 분기 기록","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

### v02:25

```text
작업 기록 기록과 순환팬 지시의 자동 복귀 우선순위 — 중간 판정|process,boundary,role||경보가 겹친 상황에서는 작업 기록 기록과 순환팬 지시의 자동 복귀 우선순위 — 중간 판정은 먼저 확인할 조건을 정하고 나머지는 대기시킨다. 조건이 풀리면 대기 항목을 다시 판정한다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":25,"primary":"작업 기록 기록과 순환팬 지시의 자동 복귀 우선순위 — 중간 판정","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

### v02:26

```text
양액 탱크와 환기창이 만날 때 환경 제어기를 보류하는 판단 — 신호 전달|state,contrast,comparison||교대 기록에서 양액 탱크와 환기창이 만날 때 환경 제어기를 보류하는 판단 — 신호 전달은 우선순위와 적용 범위를 다시 확인해 충돌을 숨기지 않는다. 같은 대상에 두 지시를 동시에 부여하지 않는다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":26,"primary":"양액 탱크와 환기창이 만날 때 환경 제어기를 보류하는 판단 — 신호 전달","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

### v02:27

```text
배수관과 압력 조절기의 야간 점검 충돌 조정 — 대상 추적|classification,boundary,function||운영표에는 배수관과 압력 조절기의 야간 점검 충돌 조정 — 대상 추적은 먼저 적용할 규칙과 나중에 살필 예외가 함께 적힌다. 충돌한 근거의 출처를 남긴다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":27,"primary":"배수관과 압력 조절기의 야간 점검 충돌 조정 — 대상 추적","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

### v02:28

```text
함수율 센서 우선 환경 제어기 예외의 승인 전 경로 — 순서 기록|process,state,contrast||정책 기록과 현장 신호가 맞지 않으면 함수율 센서 우선 환경 제어기 예외의 승인 전 경로 — 순서 기록은 충돌한 두 관계를 병렬로 보존한다. 한쪽을 지우고 단일 경로로 만들지 않는다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":28,"primary":"함수율 센서 우선 환경 제어기 예외의 승인 전 경로 — 순서 기록","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

### v02:29

```text
교대 인계에서 재배 베드와 관수 밸브를 가르는 차광 모터 기준 — 상태 묶음|boundary,role,attribute||두 담당자의 표가 다를 때 교대 인계에서 재배 베드와 관수 밸브를 가르는 차광 모터 기준 — 상태 묶음은 어느 표가 최신인지 확인한다. 최신이라는 판단과 내용의 타당성은 별도로 남긴다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":29,"primary":"교대 인계에서 재배 베드와 관수 밸브를 가르는 차광 모터 기준 — 상태 묶음","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

### v02:30

```text
순환팬 기록과 기상 예보 지시의 현장 인계 우선순위 — 우선 처리|boundary,comparison,state||판정 담당은 순환팬 기록과 기상 예보 지시의 현장 인계 우선순위 — 우선 처리는 일치하는 기록과 어긋난 기록을 나누고 예외가 승인됐는지 확인한다. 승인되지 않은 예외는 실행 근거가 아니다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":30,"primary":"순환팬 기록과 기상 예보 지시의 현장 인계 우선순위 — 우선 처리","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

### v02:31

```text
차광 모터와 환기창이 만날 때 관수 밸브를 보류하는 판단 — 연결 확인|process,boundary,role||관리자는 차광 모터와 환기창이 만날 때 관수 밸브를 보류하는 판단 — 연결 확인은 기본 순서가 예외 승인으로 바뀐 지점을 표시한다. 변경되지 않은 단계는 원래 순서를 유지한다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":31,"primary":"차광 모터와 환기창이 만날 때 관수 밸브를 보류하는 판단 — 연결 확인","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

## 적용·원복 조건

1. updater가 현재 registry SHA, 모든 old primary, 10개 locator의 유일성을 먼저 확인한다.
2. candidate는 target 10행의 `primary` raw JSON token만 바꾸며, 비대상 registry 행의 body·terminator byte mismatch가 0이어야 한다.
3. source와 registry는 한 묶음으로만 반영한다. registry 반영 실패 시 source의 정확한 10행을 이 문서의 원문으로 즉시 원복한다.
4. 반영 후 source/registry 행 수, JSON parse, locator 누락·중복, `concept`↔`primary` mismatch, source hard structure를 다시 확인한다.
