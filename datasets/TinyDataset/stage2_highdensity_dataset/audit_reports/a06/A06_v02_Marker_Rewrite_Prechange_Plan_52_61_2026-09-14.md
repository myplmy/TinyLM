# A06 v02 표식형 primary 재서술 — 사전 변경계획 (physical line 52~61)

## 사전조건·보호 범위

- source v02 SHA-256 `DF12FA874F2A117A1F277B1CF995379A8657F129C3B5308969325F9B3178E00F`, registry SHA-256 `835750A8228CBAF14887BE27C2E378280D47CC49E9EA3991880383C1FA66D24B`.
- source physical line 52~61과 같은 registry locator의 `primary`만 함께 바꾼다. source `concept`·`text`, relations·other_type·행 순서, registry locator/definition/provenance/review_status는 정해진 방식으로 보존한다.
- v01·비대상 source·다른 영역·중앙 원장·manifest·공용 train/val·checkpoint·공용 감사기는 수정하지 않는다.

## locator별 직접 재서술 계획

| locator | 기존 concept | 새 concept | relations | 예정 text의 의미 |
|---|---|---|---|---|
| v02:52 | 함수율 센서와 환경 제어기의 승인 전 충돌 조정 — 회복 판정 | 함수율 센서와 환경 제어기의 승인 전 충돌 조정 | `process,state,contrast` | 통상·제한 처리의 대비와 일회성 예외의 비영구성을 설명한다. |
| v02:53 | 재배 베드 우선 관수 밸브 예외의 예비 경로 — 경로 보존 | 재배 베드를 우선하는 관수 밸브 예외의 예비 처리 절차 | `boundary,role,attribute` | 예외가 남을 때 보류 범위와 처리 시점을 정하는 절차로 풀어 쓴다. |
| v02:54 | 주기 판정에서 순환팬과 기상 예보를 가르는 양액 탱크 기준 — 결과 검증 | 주기별 운전에서 순환팬과 기상 예보를 구분하는 양액 탱크 기준 | `boundary,comparison,state` | 두 출처를 대조하되 하나의 사실로 성급히 합치지 않는 기준이다. |
| v02:55 | 차광 모터 기록과 환기창 지시의 후속 입력 우선순위 — 영향 검토 | 차광 모터 기록과 환기창 지시의 후속 입력 우선순위 | `process,boundary,role` | 경보 뒤 우선 확인할 조건과 대기 항목을 정한다. |
| v02:56 | 기상 예보와 순환팬이 만날 때 함수율 센서를 보류하는 판단 — 예외 점검 | 기상 예보와 순환팬 충돌 시 함수율 센서 보류 판단 | `state,contrast,comparison` | 충돌 시 센서 조치를 보류하는 조건과 동시 지시 금지를 명시한다. |
| v02:57 | 관수 밸브와 재배 베드의 야간 점검 충돌 조정 — 독립 확인 | 관수 밸브와 재배 베드의 야간 점검 충돌 조정 | `classification,boundary,function` | 규칙과 예외의 적용 순서를 가르는 야간 점검 조정이다. |
| v02:58 | 환경 제어기 우선 함수율 센서 예외의 비상 확인 경로 — 분기 기록 | 환경 제어기를 우선하는 함수율 센서 예외의 비상 확인 절차 | `process,state,contrast` | 현장 신호와 정책 기록이 어긋날 때 두 관계를 병렬로 보존한다. |
| v02:59 | 교대 인계에서 압력 조절기와 배수관을 가르는 작업 기록 기준 — 중간 판정 | 교대 인계에서 압력 조절기와 배수관을 구분하는 작업 기록 기준 | `boundary,role,attribute` | 교대 표의 최신성과 내용 타당성을 분리해 판단한다. |
| v02:60 | 환기창 기록과 양액 탱크 지시의 동시 기록 우선순위 — 신호 전달 | 환기창 기록과 양액 탱크 지시의 동시 기록 우선순위 | `boundary,comparison,state` | 일치·불일치 기록 및 예외 승인 여부에 따라 순서를 정한다. |
| v02:61 | 작업 기록과 순환팬이 만날 때 배수관을 보류하는 판단 — 대상 추적 | 작업 기록과 순환팬 충돌 시 배수관 보류 판단 | `process,boundary,role` | 예외 승인으로 바뀐 단계만 표시하고 나머지는 원래 순서를 유지한다. |

## 예정 text

```text
함수율 센서와 환경 제어기의 승인 전 충돌 조정은 예외 목록을 살펴 통상 처리와 제한 처리를 구분하고, 한 번 승인된 예외를 영구 규칙으로 취급하지 않도록 하는 절차다.
재배 베드를 우선하는 관수 밸브 예외의 예비 처리 절차는 기본 경로가 열려도 예외 조건이 남아 있으면 일부 조치를 보류하고, 보류 범위와 처리 시점을 함께 정한다.
주기별 운전에서 순환팬과 기상 예보를 구분하는 양액 탱크 기준은 두 기록을 대조해 기본 지시와 예외 지시의 우선순위를 정하고, 서로 다른 출처의 정보를 하나의 사실로 합치지 않도록 한다.
차광 모터 기록과 환기창 지시의 후속 입력 우선순위는 경보가 겹친 상황에서 먼저 확인할 조건을 정하고, 나머지 항목은 대기시켰다가 조건이 해소되면 다시 판단하는 순서다.
기상 예보와 순환팬 충돌 시 함수율 센서 보류 판단은 교대 기록에 나타난 우선순위와 적용 범위를 다시 확인하고, 같은 대상에 두 지시가 동시에 적용되지 않도록 하는 판단이다.
관수 밸브와 재배 베드의 야간 점검 충돌 조정은 운영표에서 먼저 적용할 규칙과 나중에 검토할 예외를 구분하고, 충돌 근거의 출처를 남기는 조정 절차다.
환경 제어기를 우선하는 함수율 센서 예외의 비상 확인 절차는 정책 기록과 현장 신호가 맞지 않을 때 충돌한 두 관계를 나란히 보존하고, 한쪽을 지워 단일 경로로 만들지 않도록 한다.
교대 인계에서 압력 조절기와 배수관을 구분하는 작업 기록 기준은 두 담당자의 표가 다를 때 어느 표가 최신인지 확인하고, 최신성 판단과 내용의 타당성을 분리해 남기는 기준이다.
환기창 기록과 양액 탱크 지시의 동시 기록 우선순위는 일치하는 기록과 어긋난 기록을 구분하고, 예외가 승인되었는지 확인하여 적용 순서를 정하는 기준이다. 승인되지 않은 예외는 실행 근거로 쓰지 않는다.
작업 기록과 순환팬 충돌 시 배수관 보류 판단은 기본 순서가 예외 승인으로 바뀐 지점을 표시하고, 변경되지 않은 단계는 원래 순서로 유지하는 판단이다.
```

## 원복용 source rows

```text
함수율 센서와 환경 제어기의 승인 전 충돌 조정 — 회복 판정|process,state,contrast||예외 목록을 검토하면서 함수율 센서와 환경 제어기의 승인 전 충돌 조정 — 회복 판정은 통상 처리와 제한 처리를 갈라 적는다. 한 번의 예외를 영구 규칙으로 만들지 않는다.
재배 베드 우선 관수 밸브 예외의 예비 경로 — 경로 보존|boundary,role,attribute||기본 경로가 열려 있어도 재배 베드 우선 관수 밸브 예외의 예비 경로 — 경로 보존은 예외 조건이 충족되면 일부 조치를 보류한다. 보류 범위와 적용 시점을 함께 기록한다.
주기 판정에서 순환팬과 기상 예보를 가르는 양액 탱크 기준 — 결과 검증|boundary,comparison,state||두 기록을 대조하면 주기 판정에서 순환팬과 기상 예보를 가르는 양액 탱크 기준 — 결과 검증은 기본 지시와 예외 지시를 분리해 우선순위를 정한다. 서로 다른 출처를 하나의 사실로 합치지 않는다.
차광 모터 기록과 환기창 지시의 후속 입력 우선순위 — 영향 검토|process,boundary,role||경보가 겹친 상황에서는 차광 모터 기록과 환기창 지시의 후속 입력 우선순위 — 영향 검토는 먼저 확인할 조건을 정하고 나머지는 대기시킨다. 조건이 풀리면 대기 항목을 다시 판정한다.
기상 예보와 순환팬이 만날 때 함수율 센서를 보류하는 판단 — 예외 점검|state,contrast,comparison||교대 기록에서 기상 예보와 순환팬이 만날 때 함수율 센서를 보류하는 판단 — 예외 점검은 우선순위와 적용 범위를 다시 확인해 충돌을 숨기지 않는다. 같은 대상에 두 지시를 동시에 부여하지 않는다.
관수 밸브와 재배 베드의 야간 점검 충돌 조정 — 독립 확인|classification,boundary,function||운영표에는 관수 밸브와 재배 베드의 야간 점검 충돌 조정 — 독립 확인은 먼저 적용할 규칙과 나중에 살필 예외가 함께 적힌다. 충돌한 근거의 출처를 남긴다.
환경 제어기 우선 함수율 센서 예외의 비상 확인 경로 — 분기 기록|process,state,contrast||정책 기록과 현장 신호가 맞지 않으면 환경 제어기 우선 함수율 센서 예외의 비상 확인 경로 — 분기 기록은 충돌한 두 관계를 병렬로 보존한다. 한쪽을 지우고 단일 경로로 만들지 않는다.
교대 인계에서 압력 조절기와 배수관을 가르는 작업 기록 기준 — 중간 판정|boundary,role,attribute||두 담당자의 표가 다를 때 교대 인계에서 압력 조절기와 배수관을 가르는 작업 기록 기준 — 중간 판정은 어느 표가 최신인지 확인한다. 최신이라는 판단과 내용의 타당성은 별도로 남긴다.
환기창 기록과 양액 탱크 지시의 동시 기록 우선순위 — 신호 전달|boundary,comparison,state||판정 담당은 환기창 기록과 양액 탱크 지시의 동시 기록 우선순위 — 신호 전달은 일치하는 기록과 어긋난 기록을 나누고 예외가 승인됐는지 확인한다. 승인되지 않은 예외는 실행 근거가 아니다.
작업 기록과 순환팬이 만날 때 배수관을 보류하는 판단 — 대상 추적|process,boundary,role||관리자는 작업 기록과 순환팬이 만날 때 배수관을 보류하는 판단 — 대상 추적은 기본 순서가 예외 승인으로 바뀐 지점을 표시한다. 변경되지 않은 단계는 원래 순서를 유지한다.
```

## 원복용 registry JSON rows

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":52,"primary":"함수율 센서와 환경 제어기의 승인 전 충돌 조정 — 회복 판정","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":53,"primary":"재배 베드 우선 관수 밸브 예외의 예비 경로 — 경로 보존","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":54,"primary":"주기 판정에서 순환팬과 기상 예보를 가르는 양액 탱크 기준 — 결과 검증","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":55,"primary":"차광 모터 기록과 환기창 지시의 후속 입력 우선순위 — 영향 검토","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":56,"primary":"기상 예보와 순환팬이 만날 때 함수율 센서를 보류하는 판단 — 예외 점검","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":57,"primary":"관수 밸브와 재배 베드의 야간 점검 충돌 조정 — 독립 확인","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":58,"primary":"환경 제어기 우선 함수율 센서 예외의 비상 확인 경로 — 분기 기록","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":59,"primary":"교대 인계에서 압력 조절기와 배수관을 가르는 작업 기록 기준 — 중간 판정","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":60,"primary":"환기창 기록과 양액 탱크 지시의 동시 기록 우선순위 — 신호 전달","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":61,"primary":"작업 기록과 순환팬이 만날 때 배수관을 보류하는 판단 — 대상 추적","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

새 primary 10개는 A06 전체 exact primary와 묶음 내부의 중복이 0이어야 하며, candidate는 current SHA와 old primary를 확인하고 target 10개 외 byte가 불변인지 검증한다. registry 반영 실패 시 위 source 원문을 복원한다.
