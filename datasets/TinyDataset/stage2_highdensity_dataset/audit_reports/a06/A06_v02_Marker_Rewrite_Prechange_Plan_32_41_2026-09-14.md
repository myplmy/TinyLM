# A06 v02 표식형 primary 재서술 — 사전 변경계획 (physical line 32~41)

## 사전조건과 범위

- source v02 SHA-256: `3AA1D22764C0A794517278DF25A461D634D2DCFA25078BC09A8722F5DE5EB3BD`; registry SHA-256: `BFFB72A88E1227A62F2635826E03C8E664C33174DC9EFCB07393B4763551A955`.
- source v02는 150 data rows, registry는 7,800 JSONL rows다. 대상은 source physical line 32~41과 같은 locator의 registry `primary` 10행뿐이다.
- relations·other_type·source 행 순서와 registry의 locator/definition/provenance/review_status는 보존한다. v01, 비대상 source, 다른 영역과 중앙·공용 경로는 변경하지 않는다.

## locator별 변경·의미 판단

| locator | 기존 concept / registry primary | 새 concept / registry primary | relations 보존 | 직접 판단 |
|---|---|---|---|---|
| v02:32 | 기상 예보와 순환팬의 저부하 운전 충돌 조정 — 출처 대조 | 기상 예보와 순환팬의 저부하 운전 충돌 조정 | `state,contrast,comparison` | `출처 대조`는 검수 표식이다. 저부하 운전의 충돌 조정은 절차적 명사구로 자연스럽다. |
| v02:33 | 관수 밸브 우선 재배 베드 예외의 통신 재시도 경로 — 범위 확인 | 관수 밸브를 우선하는 재배 베드 제어 예외의 통신 재시도 절차 | `classification,boundary,function` | 조사 생략과 표식을 제거하고, 우선 제어 예외에서 통신 재시도를 정하는 절차로 구체화한다. |
| v02:34 | 원격 관찰에서 환경 제어기와 함수율 센서를 가르는 순환팬 기준 — 운영 인계 | 원격 관찰에서 환경 제어기와 함수율 센서를 구분할 때 쓰는 순환팬 기준 | `process,state,contrast,other` | `운영 인계`는 표식이다. `부분 표본의 해석 한계` other_type literal은 text에 유지한다. |
| v02:35 | 압력 조절기 기록과 배수관 지시의 교대 기록 우선순위 — 회복 판정 | 압력 조절기 기록과 배수관 지시의 교대 인계 우선순위 | `boundary,role,attribute` | 중복된 `기록`과 `회복 판정` 표식을 교대 인계에서 적용할 우선순위로 바꾼다. |
| v02:36 | 환기창과 양액 탱크가 만날 때 기상 예보를 보류하는 판단 — 경로 보존 | 환기창과 양액 탱크 충돌 시 기상 예보 보류 판단 | `boundary,comparison,state` | 불투명한 `만날 때`·표식을 실제 충돌 조건과 보류 판단으로 바꾼다. |
| v02:37 | 작업 기록과 순환팬의 복구 직후 충돌 조정 — 결과 검증 | 작업 기록과 순환팬의 복구 직후 충돌 조정 | `process,boundary,role` | 중심 명사구는 유지하고, `결과 검증` 표식만 제거한다. |
| v02:38 | 양액 탱크 우선 환기창 예외의 발생 직후 경로 — 영향 검토 | 양액 탱크를 우선하는 환기창 예외의 발생 직후 처리 절차 | `state,contrast,comparison` | 조사 생략·표식을 고치고, 예외 발생 직후 어떤 관계를 보존하는지 text에 설명한다. |
| v02:39 | 초기 입력에서 배수관과 압력 조절기를 가르는 재배 베드 기준 — 예외 점검 | 초기 입력에서 배수관과 압력 조절기를 구분하는 재배 베드 기준 | `classification,boundary,function` | `예외 점검`은 표식이다. 초기 입력 단계에서 대상을 구분하는 기준으로 직접 표현한다. |
| v02:40 | 함수율 센서 기록과 환경 제어기 지시의 예외 기간 우선순위 — 독립 확인 | 함수율 센서 기록과 환경 제어기 지시의 예외 기간 우선순위 | `process,state,contrast` | `독립 확인` 표식을 제거하고, 예외 기간에 출처가 충돌할 때의 우선순위로 의미를 유지한다. |
| v02:41 | 재배 베드와 관수 밸브가 만날 때 차광 모터를 보류하는 판단 — 분기 기록 | 재배 베드와 관수 밸브 충돌 시 차광 모터 보류 판단 | `boundary,role,attribute` | 충돌 조건·보류 대상·판단을 명시해 기계적 합성어를 피한다. |

## 예정 text와 원복용 원문

각 source 원문은 `concept|relations|other_type|text`, 그 아래 줄은 같은 locator의 변경 전 registry JSON이다.

### v02:32

```text
기상 예보와 순환팬의 저부하 운전 충돌 조정 — 출처 대조|state,contrast,comparison||예외 목록을 검토하면서 기상 예보와 순환팬의 저부하 운전 충돌 조정 — 출처 대조는 통상 처리와 제한 처리를 갈라 적는다. 한 번의 예외를 영구 규칙으로 만들지 않는다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":32,"primary":"기상 예보와 순환팬의 저부하 운전 충돌 조정 — 출처 대조","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

예정 text: `기상 예보와 순환팬의 저부하 운전 충돌 조정은 예외 목록을 살펴 통상 처리와 제한 처리를 구분하고, 한 번 승인된 예외를 영구 규칙으로 취급하지 않도록 하는 절차다.`

### v02:33

```text
관수 밸브 우선 재배 베드 예외의 통신 재시도 경로 — 범위 확인|classification,boundary,function||기본 경로가 열려 있어도 관수 밸브 우선 재배 베드 예외의 통신 재시도 경로 — 범위 확인은 예외 조건이 충족되면 일부 조치를 보류한다. 보류 범위와 적용 시점을 함께 기록한다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":33,"primary":"관수 밸브 우선 재배 베드 예외의 통신 재시도 경로 — 범위 확인","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

예정 text: `관수 밸브를 우선하는 재배 베드 제어 예외의 통신 재시도 절차는 기본 경로가 열려 있어도 예외 조건이 남아 있으면 일부 조치를 보류하고, 보류 범위와 재시도 시점을 함께 정하는 절차다.`

### v02:34

```text
원격 관찰에서 환경 제어기와 함수율 센서를 가르는 순환팬 기준 — 운영 인계|process,state,contrast,other|부분 표본의 해석 한계|두 기록을 대조하면 원격 관찰에서 환경 제어기와 함수율 센서를 가르는 순환팬 기준 — 운영 인계는 기본 지시와 예외 지시를 분리해 우선순위를 정한다. 서로 다른 출처를 하나의 사실로 합치지 않는다. 부분 표본의 해석 한계 항목은 확인된 관계만 확정하게 한다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":34,"primary":"원격 관찰에서 환경 제어기와 함수율 센서를 가르는 순환팬 기준 — 운영 인계","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

예정 text: `원격 관찰에서 환경 제어기와 함수율 센서를 구분할 때 쓰는 순환팬 기준은 두 기록을 대조해 기본 지시와 예외 지시의 우선순위를 정한다. 부분 표본의 해석 한계가 있으므로 서로 다른 출처를 하나의 사실로 합치지 않는다.`

### v02:35

```text
압력 조절기 기록과 배수관 지시의 교대 기록 우선순위 — 회복 판정|boundary,role,attribute||경보가 겹친 상황에서는 압력 조절기 기록과 배수관 지시의 교대 기록 우선순위 — 회복 판정은 먼저 확인할 조건을 정하고 나머지는 대기시킨다. 조건이 풀리면 대기 항목을 다시 판정한다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":35,"primary":"압력 조절기 기록과 배수관 지시의 교대 기록 우선순위 — 회복 판정","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

예정 text: `압력 조절기 기록과 배수관 지시의 교대 인계 우선순위는 경보가 겹친 상황에서 먼저 확인할 조건을 정하고, 나머지 항목은 대기시켰다가 조건이 해소되면 다시 판단하는 순서다.`

### v02:36

```text
환기창과 양액 탱크가 만날 때 기상 예보를 보류하는 판단 — 경로 보존|boundary,comparison,state||교대 기록에서 환기창과 양액 탱크가 만날 때 기상 예보를 보류하는 판단 — 경로 보존은 우선순위와 적용 범위를 다시 확인해 충돌을 숨기지 않는다. 같은 대상에 두 지시를 동시에 부여하지 않는다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":36,"primary":"환기창과 양액 탱크가 만날 때 기상 예보를 보류하는 판단 — 경로 보존","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

예정 text: `환기창과 양액 탱크 충돌 시 기상 예보 보류 판단은 교대 기록의 우선순위와 적용 범위를 다시 확인하여 충돌을 숨기지 않고, 같은 대상에 두 지시를 동시에 부여하지 않도록 하는 판단이다.`

### v02:37

```text
작업 기록과 순환팬의 복구 직후 충돌 조정 — 결과 검증|process,boundary,role||운영표에는 작업 기록과 순환팬의 복구 직후 충돌 조정 — 결과 검증은 먼저 적용할 규칙과 나중에 살필 예외가 함께 적힌다. 충돌한 근거의 출처를 남긴다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":37,"primary":"작업 기록과 순환팬의 복구 직후 충돌 조정 — 결과 검증","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

예정 text: `작업 기록과 순환팬의 복구 직후 충돌 조정은 운영표에서 먼저 적용할 규칙과 나중에 검토할 예외를 구분하고, 충돌한 근거의 출처를 남기는 조정 절차다.`

### v02:38

```text
양액 탱크 우선 환기창 예외의 발생 직후 경로 — 영향 검토|state,contrast,comparison||정책 기록과 현장 신호가 맞지 않으면 양액 탱크 우선 환기창 예외의 발생 직후 경로 — 영향 검토는 충돌한 두 관계를 병렬로 보존한다. 한쪽을 지우고 단일 경로로 만들지 않는다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":38,"primary":"양액 탱크 우선 환기창 예외의 발생 직후 경로 — 영향 검토","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

예정 text: `양액 탱크를 우선하는 환기창 예외의 발생 직후 처리 절차는 정책 기록과 현장 신호가 맞지 않을 때 충돌한 두 관계를 나란히 보존하고, 한쪽을 지워 단일 경로로 만들지 않도록 한다.`

### v02:39

```text
초기 입력에서 배수관과 압력 조절기를 가르는 재배 베드 기준 — 예외 점검|classification,boundary,function||두 담당자의 표가 다를 때 초기 입력에서 배수관과 압력 조절기를 가르는 재배 베드 기준 — 예외 점검은 어느 표가 최신인지 확인한다. 최신이라는 판단과 내용의 타당성은 별도로 남긴다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":39,"primary":"초기 입력에서 배수관과 압력 조절기를 가르는 재배 베드 기준 — 예외 점검","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

예정 text: `초기 입력에서 배수관과 압력 조절기를 구분하는 재배 베드 기준은 두 담당자의 표가 다를 때 어느 표가 최신인지 확인하고, 최신성 판단과 내용의 타당성을 분리해 남기는 기준이다.`

### v02:40

```text
함수율 센서 기록과 환경 제어기 지시의 예외 기간 우선순위 — 독립 확인|process,state,contrast||판정 담당은 함수율 센서 기록과 환경 제어기 지시의 예외 기간 우선순위 — 독립 확인은 일치하는 기록과 어긋난 기록을 나누고 예외가 승인됐는지 확인한다. 승인되지 않은 예외는 실행 근거가 아니다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":40,"primary":"함수율 센서 기록과 환경 제어기 지시의 예외 기간 우선순위 — 독립 확인","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

예정 text: `함수율 센서 기록과 환경 제어기 지시의 예외 기간 우선순위는 판정 담당자가 일치하는 기록과 어긋난 기록을 구분하고, 예외가 승인되었는지 확인하여 적용 순서를 정하는 기준이다. 승인되지 않은 예외는 실행 근거로 쓰지 않는다.`

### v02:41

```text
재배 베드와 관수 밸브가 만날 때 차광 모터를 보류하는 판단 — 분기 기록|boundary,role,attribute||관리자는 재배 베드와 관수 밸브가 만날 때 차광 모터를 보류하는 판단 — 분기 기록은 기본 순서가 예외 승인으로 바뀐 지점을 표시한다. 변경되지 않은 단계는 원래 순서를 유지한다.
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":41,"primary":"재배 베드와 관수 밸브가 만날 때 차광 모터를 보류하는 판단 — 분기 기록","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

예정 text: `재배 베드와 관수 밸브 충돌 시 차광 모터 보류 판단은 기본 순서가 예외 승인으로 바뀐 지점을 표시하고, 변경되지 않은 단계는 원래 순서로 유지하는 판단이다.`

## 적용·원복 게이트

1. 새 primary 10개는 A06 전체 exact primary 중복과 묶음 내부 중복이 0이어야 한다.
2. registry updater는 현재 SHA와 old primary를 확인하고 candidate가 target `primary` 10개만 바꿨음을 byte level로 확인해야 한다.
3. source와 registry를 같은 transaction으로 반영한다. registry 실패 시 source는 위 원문 10행으로 즉시 원복한다.
4. 반영 후 행 수·JSON parse·locator set·`concept`↔`primary`·controlled relations·primary literal을 다시 검사한다.
