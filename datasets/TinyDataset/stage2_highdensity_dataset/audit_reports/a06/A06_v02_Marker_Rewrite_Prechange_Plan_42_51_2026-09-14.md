# A06 v02 표식형 primary 재서술 — 사전 변경계획 (physical line 42~51)

## 사전조건

- source v02 SHA-256 `4D3F738EF32C535646EA2BB0F4A9B2122EDDAB0C9BE23868AD896293DBF7BAB6`, registry SHA-256 `22A71110A5CF76300880D60DB26FE732811DDB493E207448F0B23DB5F29FBC4A`.
- 범위는 source physical line 42~51과 같은 `source_file + source_line` registry locator 10개다. source의 concept·text 및 registry의 primary만 변경한다.
- relations·other_type·행 순서, registry의 locator/definition/provenance/review_status와 v01·비대상 source·중앙/공용 경로는 보존한다.

## 변경안과 직접 의미 검토

| locator | 기존 concept | 새 concept | relations 보존 | 재서술 근거 |
|---|---|---|---|---|
| v02:42 | 순환팬과 기상 예보의 경계 이후 충돌 조정 — 중간 판정 | 순환팬과 기상 예보의 운전 경계에서 발생한 충돌 조정 | `boundary,comparison,state` | 불투명한 `경계 이후`와 표식을, 운전 경계에서 생긴 실제 충돌로 바꾼다. |
| v02:43 | 차광 모터 우선 환기창 예외의 부분 회복 경로 — 신호 전달 | 차광 모터를 우선하는 환기창 예외의 부분 복구 절차 | `process,boundary,role` | 조사 생략·표식을 없애고 부분 복구의 절차와 보류 범위를 직접 표현한다. |
| v02:44 | 장기 관찰에서 기상 예보와 순환팬을 가르는 함수율 센서 기준 — 대상 추적 | 장기 관찰에서 기상 예보와 순환팬을 구분하는 함수율 센서 기준 | `state,contrast,comparison` | `대상 추적`은 표식이며, 장기 관찰에서 두 지시를 구분하는 센서 기준으로 풀어 쓴다. |
| v02:45 | 관수 밸브 기록과 재배 베드 지시의 대체 자원 우선순위 — 순서 기록 | 관수 밸브 기록과 재배 베드 지시의 대체 자원 우선순위 | `classification,boundary,function` | 중심 개념은 자연스러워 표식만 제거하고, 대체 자원 선택의 실제 기준을 text에 명시한다. |
| v02:46 | 환경 제어기와 함수율 센서가 만날 때 순환팬을 보류하는 판단 — 상태 묶음 | 환경 제어기와 함수율 센서 충돌 시 순환팬 보류 판단 | `process,state,contrast` | `만날 때`·표식을 충돌 조건과 보류 결정으로 바꾼다. |
| v02:47 | 압력 조절기와 배수관의 자동 복귀 충돌 조정 — 우선 처리 | 압력 조절기와 배수관의 자동 복귀 충돌 조정 | `boundary,role,attribute` | 자연스러운 중심 명사구는 유지하고 검수 표식만 제거한다. |
| v02:48 | 환기창 우선 양액 탱크 예외의 재검 표본 경로 — 연결 확인 | 환기창을 우선하는 양액 탱크 예외의 재검토 절차 | `boundary,comparison,state` | 어색한 `재검 표본 경로`를 두 관계를 다시 대조하는 절차로 바꾼다. |
| v02:49 | 정상 복귀에서 작업 기록과 순환팬을 가르는 배수관 기준 — 출처 대조 | 정상 복귀에서 작업 기록과 순환팬을 구분하는 배수관 기준 | `process,boundary,role` | `출처 대조`는 표식이며, 복귀 단계에서 대상을 가르는 배수관 기준을 남긴다. |
| v02:50 | 양액 탱크 기록과 환기창 지시의 전원 대기 우선순위 — 범위 확인 | 양액 탱크 기록과 환기창 지시의 전원 대기 우선순위 | `state,contrast,comparison` | 표식만 제거하고, 전원 대기 중 기록과 지시를 비교하는 우선순위를 text에서 설명한다. |
| v02:51 | 배수관과 압력 조절기가 만날 때 재배 베드를 보류하는 판단 — 운영 인계 | 배수관과 압력 조절기 충돌 시 재배 베드 보류 판단 | `classification,boundary,function,other` | 충돌·보류 대상·판단을 명시하고 `식별 기록 상충` other_type literal을 보존한다. |

## 예정 text

1. `순환팬과 기상 예보의 운전 경계에서 발생한 충돌 조정은 예외 목록을 검토해 통상 운전과 제한 운전을 구분하고, 일시 승인된 예외를 영구 규칙으로 바꾸지 않도록 하는 절차다.`
2. `차광 모터를 우선하는 환기창 예외의 부분 복구 절차는 기본 경로가 열려도 예외 조건이 남아 있으면 일부 조치를 보류하고, 보류 범위와 복구 시점을 함께 정한다.`
3. `장기 관찰에서 기상 예보와 순환팬을 구분하는 함수율 센서 기준은 두 기록을 대조해 기본 지시와 예외 지시의 우선순위를 정하고, 서로 다른 출처의 정보를 하나의 사실로 합치지 않도록 한다.`
4. `관수 밸브 기록과 재배 베드 지시의 대체 자원 우선순위는 경보가 겹쳤을 때 먼저 확인할 조건을 정하고, 대체 자원을 쓸 수 있는 항목과 대기해야 할 항목을 구분하는 순서다.`
5. `환경 제어기와 함수율 센서 충돌 시 순환팬 보류 판단은 교대 기록에 나타난 우선순위와 적용 범위를 다시 확인하고, 같은 대상에 두 지시가 동시에 적용되지 않도록 하는 판단이다.`
6. `압력 조절기와 배수관의 자동 복귀 충돌 조정은 운영표에서 우선 적용할 규칙과 후속으로 검토할 예외를 구분하고, 충돌 근거의 출처를 남기는 조정 절차다.`
7. `환기창을 우선하는 양액 탱크 예외의 재검토 절차는 정책 기록과 현장 신호가 맞지 않을 때 두 관계를 나란히 보존하고, 하나를 지워 단일 경로인 것처럼 만들지 않도록 한다.`
8. `정상 복귀에서 작업 기록과 순환팬을 구분하는 배수관 기준은 두 담당자의 표가 다를 때 어느 표가 최신인지 확인하고, 최신성 판단과 내용의 타당성을 분리해 남기는 기준이다.`
9. `양액 탱크 기록과 환기창 지시의 전원 대기 우선순위는 일치하는 기록과 어긋난 기록을 구분하고, 예외가 승인되었는지 확인하여 적용 순서를 정하는 기준이다. 승인되지 않은 예외는 실행 근거로 쓰지 않는다.`
10. `배수관과 압력 조절기 충돌 시 재배 베드 보류 판단은 기본 순서가 예외 승인으로 바뀐 지점을 표시하고, 식별 기록 상충이 있으면 확인된 관계만 확정하며 변경되지 않은 단계는 원래 순서로 유지하는 판단이다.`

## 원복용 원문 source rows

```text
순환팬과 기상 예보의 경계 이후 충돌 조정 — 중간 판정|boundary,comparison,state||예외 목록을 검토하면서 순환팬과 기상 예보의 경계 이후 충돌 조정 — 중간 판정은 통상 처리와 제한 처리를 갈라 적는다. 한 번의 예외를 영구 규칙으로 만들지 않는다.
차광 모터 우선 환기창 예외의 부분 회복 경로 — 신호 전달|process,boundary,role||기본 경로가 열려 있어도 차광 모터 우선 환기창 예외의 부분 회복 경로 — 신호 전달은 예외 조건이 충족되면 일부 조치를 보류한다. 보류 범위와 적용 시점을 함께 기록한다.
장기 관찰에서 기상 예보와 순환팬을 가르는 함수율 센서 기준 — 대상 추적|state,contrast,comparison||두 기록을 대조하면 장기 관찰에서 기상 예보와 순환팬을 가르는 함수율 센서 기준 — 대상 추적은 기본 지시와 예외 지시를 분리해 우선순위를 정한다. 서로 다른 출처를 하나의 사실로 합치지 않는다.
관수 밸브 기록과 재배 베드 지시의 대체 자원 우선순위 — 순서 기록|classification,boundary,function||경보가 겹친 상황에서는 관수 밸브 기록과 재배 베드 지시의 대체 자원 우선순위 — 순서 기록은 먼저 확인할 조건을 정하고 나머지는 대기시킨다. 조건이 풀리면 대기 항목을 다시 판정한다.
환경 제어기와 함수율 센서가 만날 때 순환팬을 보류하는 판단 — 상태 묶음|process,state,contrast||교대 기록에서 환경 제어기와 함수율 센서가 만날 때 순환팬을 보류하는 판단 — 상태 묶음은 우선순위와 적용 범위를 다시 확인해 충돌을 숨기지 않는다. 같은 대상에 두 지시를 동시에 부여하지 않는다.
압력 조절기와 배수관의 자동 복귀 충돌 조정 — 우선 처리|boundary,role,attribute||운영표에는 압력 조절기와 배수관의 자동 복귀 충돌 조정 — 우선 처리는 먼저 적용할 규칙과 나중에 살필 예외가 함께 적힌다. 충돌한 근거의 출처를 남긴다.
환기창 우선 양액 탱크 예외의 재검 표본 경로 — 연결 확인|boundary,comparison,state||정책 기록과 현장 신호가 맞지 않으면 환기창 우선 양액 탱크 예외의 재검 표본 경로 — 연결 확인은 충돌한 두 관계를 병렬로 보존한다. 한쪽을 지우고 단일 경로로 만들지 않는다.
정상 복귀에서 작업 기록과 순환팬을 가르는 배수관 기준 — 출처 대조|process,boundary,role||두 담당자의 표가 다를 때 정상 복귀에서 작업 기록과 순환팬을 가르는 배수관 기준 — 출처 대조는 어느 표가 최신인지 확인한다. 최신이라는 판단과 내용의 타당성은 별도로 남긴다.
양액 탱크 기록과 환기창 지시의 전원 대기 우선순위 — 범위 확인|state,contrast,comparison||판정 담당은 양액 탱크 기록과 환기창 지시의 전원 대기 우선순위 — 범위 확인은 일치하는 기록과 어긋난 기록을 나누고 예외가 승인됐는지 확인한다. 승인되지 않은 예외는 실행 근거가 아니다.
배수관과 압력 조절기가 만날 때 재배 베드를 보류하는 판단 — 운영 인계|classification,boundary,function,other|식별 기록 상충|관리자는 배수관과 압력 조절기가 만날 때 재배 베드를 보류하는 판단 — 운영 인계는 기본 순서가 예외 승인으로 바뀐 지점을 표시한다. 변경되지 않은 단계는 원래 순서를 유지한다. 식별 기록 상충 항목은 확인된 관계만 확정하게 한다.
```

## 원복용 원문 registry JSON rows

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":42,"primary":"순환팬과 기상 예보의 경계 이후 충돌 조정 — 중간 판정","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":43,"primary":"차광 모터 우선 환기창 예외의 부분 회복 경로 — 신호 전달","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":44,"primary":"장기 관찰에서 기상 예보와 순환팬을 가르는 함수율 센서 기준 — 대상 추적","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":45,"primary":"관수 밸브 기록과 재배 베드 지시의 대체 자원 우선순위 — 순서 기록","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":46,"primary":"환경 제어기와 함수율 센서가 만날 때 순환팬을 보류하는 판단 — 상태 묶음","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":47,"primary":"압력 조절기와 배수관의 자동 복귀 충돌 조정 — 우선 처리","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":48,"primary":"환기창 우선 양액 탱크 예외의 재검 표본 경로 — 연결 확인","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":49,"primary":"정상 복귀에서 작업 기록과 순환팬을 가르는 배수관 기준 — 출처 대조","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":50,"primary":"양액 탱크 기록과 환기창 지시의 전원 대기 우선순위 — 범위 확인","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v02.source.psv","source_line":51,"primary":"배수관과 압력 조절기가 만날 때 재배 베드를 보류하는 판단 — 운영 인계","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-002","review_status":"generated_pending_semantic_review"}
```

## 적용·원복 조건

- A06 전체 exact primary 및 이번 10개 내부에서 새 concept 중복이 0이어야 한다.
- candidate는 current registry SHA·old primary·10 locator를 확인하고, target primary 10개 외 registry byte가 바뀌지 않아야 한다.
- registry 반영 실패 시 source 10행을 위 원문으로 정확히 원복한다. 반영 후 source/registry 행 수·JSON parse·locator set·primary literal·relations 구조를 다시 확인한다.
