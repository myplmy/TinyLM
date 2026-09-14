# A06 v06:52~61 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `217D43FB6E704226296DAB28AC1CB9CA526E318E0FD1294311B08DC45A1E9765`
- registry SHA-256: `6ACA776480854F0E0DE765755101F1EA1D7EE82A85B4FD1B713704A4A5D2970A`
- locator는 `stage2_(16)relational_composition_high_density_train_v06.source.psv:52~61`으로 고정한다. source concept/text와 같은 locator registry primary 외 field·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v06_semantic_rewrite_52_61_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 52 | 배수문 관측 공백에서 운영 당직표 범위 제한 — 순서 기록 → 배수문 기록 공백의 운전 지시 분류 | `classification,boundary,state` | 조작 지시와 미확인 위치를 구분해 보류로 분류한다. |
| 53 | 현장 재검에 확인된 수압 센서와 수질 계측기의 부분 경로 — 상태 묶음 → 수압 센서와 수질 계측기 채널 대조 | `state,comparison,other` | 같은 시각의 압력·탁도 수치를 비교한다. |
| 54 | 여과지 표본 부족 뒤 저수조 연결을 보류하는 경계 직전 — 우선 처리 → 여과지 표본 부족 시 저수조 연결 점검 | `process,boundary,attribute` | 압력과 미확인 수위 변화를 구분해 연결 여부를 점검한다. |
| 55 | 보이지 않은 방류 기록과 확인된 염소 주입기의 구분 — 연결 확인 → 방류 기록 공백 시 염소 주입 보류 | `part_of,state,other` | 전체 정수 과정 중 확인된 주입 단계의 범위를 제한하고 결정을 보류한다. |
| 56 | 원수 유입구의 일부 기록만으로 여과지를 추정하지 않은 경로 — 출처 대조 → 원수 유입 부분 기록의 여과지 점검 | `state,boundary,other` | 부분 유입 기록과 비어 있는 압력 기록을 구분해 증량을 보류한다. |
| 57 | 수질 계측기 관측 공백에서 수압 센서 범위 제한 — 범위 확인 → 수질 계측기 공백의 수압 점검 인계 | `process,other,role` | 교대자가 수압값 출처를 확인해 수질 점검을 인계한다. |
| 58 | 후속 입력에 확인된 운영 당직표와 배수문의 부분 경로 — 운영 인계 → 후속 당직표의 배수문 상태 분류 | `classification,boundary,state` | 새 지시와 미확인 위치를 구분해 상태를 보류로 분류한다. |
| 59 | 정수 펌프 표본 부족 뒤 응집조 연결을 보류하는 중앙 표본 — 회복 판정 → 정수 펌프 표본 부족 시 응집조 연결 보류 | `state,comparison,other` | 전류·수위 수치를 비교하고 상충 상태에서 연결을 보류한다. |
| 60 | 보이지 않은 염소 주입기와 확인된 저수조의 구분 — 경로 보존 → 염소 주입 기록 공백의 저수조 점검 | `process,boundary,attribute` | 수위와 누락된 주입량을 구분해 농도 조정을 멈춘다. |
| 61 | 응집조의 일부 기록만으로 여과지를 추정하지 않은 경로 — 결과 검증 → 응집조 부분 기록의 여과지 범위 | `part_of,state,other` | 전체 과정 중 확인된 응집 단계만 한정하고 효과 판단을 보류한다. |

## 새 text

| line | text |
|---:|---|
| 52 | 배수문 위치 기록이 비어 있고 당직표에 조작 지시만 남았을 때, 배수문 기록 공백의 운전 지시 분류에서는 운영자가 확인된 조작 지시와 확인되지 않은 배수문 상태를 구분해 보류로 분류한다. 위치가 확인되기 전에는 개방 순서를 확정하지 않아 과다 방류를 막는다. |
| 53 | 수압 센서와 수질 계측기 값이 서로 다른 채널에 들어올 때, 수압 센서와 수질 계측기 채널 대조에서는 교대자가 같은 시각의 압력값과 탁도값을 비교한다. 센서 채널 불일치 상태에서는 펌프 출력을 조정하지 않아 불필요한 급수 제한을 막는다. |
| 54 | 여과지 압력 표본이 적고 저수조 수위도 새로 확인되지 않을 때, 여과지 표본 부족 시 저수조 연결 점검은 운영자가 확인된 압력값과 확인되지 않은 수위 변화를 구분해 연결 여부를 점검하는 과정이다. 수위 측정 전에는 유입량을 늘리지 않아 저수조 넘침을 막는다. |
| 55 | 방류량 기록은 비어 있지만 염소 주입량은 확인될 때, 방류 기록 공백 시 염소 주입 보류는 전체 정수 과정 중 확인된 주입 단계만 가리키는 보류 상태다. 다음 단계 입력 결측 때문에 방류량을 추정해 주입량을 바꾸지 않아 근거 없는 농도 조정을 막는다. |
| 56 | 원수 유입량이 일부 시각에만 있고 여과지 압력 기록이 없을 때, 원수 유입 부분 기록의 여과지 점검에서는 운영자가 확인된 유입량과 확인되지 않은 압력 변화를 구분한다. 중간 관측 결측 때문에 유입량 증가는 보류하여 여과지 압력 급등을 막는다. |
| 57 | 수질 계측기 측정값이 누락되고 수압 센서 값만 들어올 때, 수질 계측기 공백의 수압 점검 인계는 교대자가 수압값의 출처를 확인해 다음 당직자에게 현장 수질 점검을 넘기는 과정이다. 출처 연결 불명 상태에서는 펌프 출력을 바꾸지 않아 압력 변동을 막는다. |
| 58 | 당직표에 새 배수문 지시는 있지만 위치 기록이 없을 때, 후속 당직표의 배수문 상태 분류에서는 운영자가 확인된 운전 지시와 확인되지 않은 배수문 상태를 구분해 보류로 분류한다. 위치가 확인되기 전에는 자동 복귀로 확정하지 않아 과다 방류를 막는다. |
| 59 | 정수 펌프 전류 표본이 적고 응집조 수위는 다른 시각에 기록됐을 때, 정수 펌프 표본 부족 시 응집조 연결 보류에서는 운영자가 두 수치를 비교한다. 식별 기록 상충 상태에서는 응집조 고장으로 단정하지 않아 불필요한 펌프 정지를 막는다. |
| 60 | 염소 주입기 유량 기록이 없는데 저수조 수위는 확인될 때, 염소 주입 기록 공백의 저수조 점검은 운영자가 확인된 수위와 확인되지 않은 주입량을 구분하는 과정이다. 주입량이 확인되기 전에는 농도 조정을 하지 않아 저수조 수질 변동을 막는다. |
| 61 | 응집조 수위가 일부 시간에만 있고 여과지 압력도 같은 시각에 없을 때, 응집조 부분 기록의 여과지 범위는 전체 정수 과정 중 확인된 응집 단계를 한정하는 보류 상태다. 동시 개입 분리 불가 때문에 응집조 조치의 효과를 확정하지 않고 유입량 증가는 보류하여 여과지 압력 급등을 막는다. |

## 원복 source 행

```text
배수문 관측 공백에서 운영 당직표 범위 제한 — 순서 기록|classification,boundary,state||관측 범위가 제한된 보고서에서 배수문 관측 공백에서 운영 당직표 범위 제한 — 순서 기록은 보이는 단계만 책임 있게 설명한다. 누락된 단계는 추가 확인 항목으로 넘긴다.
현장 재검에 확인된 수압 센서와 수질 계측기의 부분 경로 — 상태 묶음|state,comparison,other|센서 채널 불일치|자료가 서로 다른 시점에 모였다면 현장 재검에 확인된 수압 센서와 수질 계측기의 부분 경로 — 상태 묶음은 확인 시점이 겹치는 구간만 연결한다. 나머지는 보류 상태로 남긴다. 센서 채널 불일치 항목은 확인된 관계만 확정하게 한다.
여과지 표본 부족 뒤 저수조 연결을 보류하는 경계 직전 — 우선 처리|process,boundary,attribute||센서 기록이 끊긴 지점 뒤에는 여과지 표본 부족 뒤 저수조 연결을 보류하는 경계 직전 — 우선 처리는 가능한 범위를 좁혀 둔다. 추가 측정 전에는 경로를 확정하지 않는다.
보이지 않은 방류 기록과 확인된 염소 주입기의 구분 — 연결 확인|part_of,state,other|다음 단계 입력 결측|확인된 표본이 적을수록 보이지 않은 방류 기록과 확인된 염소 주입기의 구분 — 연결 확인은 연결의 방향과 범위를 보수적으로 적는다. 결측을 정상 상태로 간주하지 않는다. 다음 단계 입력 결측 항목은 확인된 관계만 확정하게 한다.
원수 유입구의 일부 기록만으로 여과지를 추정하지 않은 경로 — 출처 대조|state,boundary,other|중간 관측 결측|한 채널의 응답만으로 원수 유입구의 일부 기록만으로 여과지를 추정하지 않은 경로 — 출처 대조는 전체 연결을 판정하지 않는다. 다른 채널이 채워질 때까지 가능한 경로를 열어 둔다. 중간 관측 결측 항목은 확인된 관계만 확정하게 한다.
수질 계측기 관측 공백에서 수압 센서 범위 제한 — 범위 확인|process,other,role|출처 연결 불명|현장에 남은 자료는 수질 계측기 관측 공백에서 수압 센서 범위 제한 — 범위 확인은 전체 경로 중 일부만 보여 준다. 보이지 않은 단계를 사실처럼 서술하지 않는다. 출처 연결 불명 항목은 확인된 관계만 확정하게 한다.
후속 입력에 확인된 운영 당직표와 배수문의 부분 경로 — 운영 인계|classification,boundary,state||관측표에 보이는 구간만으로 후속 입력에 확인된 운영 당직표와 배수문의 부분 경로 — 운영 인계는 확인된 관계를 적는다. 빈 구간을 임의의 연결로 채우지 않는다.
정수 펌프 표본 부족 뒤 응집조 연결을 보류하는 중앙 표본 — 회복 판정|state,comparison,other|식별 기록 상충|부분 로그를 읽을 때 정수 펌프 표본 부족 뒤 응집조 연결을 보류하는 중앙 표본 — 회복 판정은 기록된 사실과 기록되지 않은 가능성을 구분한다. 가능성은 확정 문장으로 바꾸지 않는다. 식별 기록 상충 항목은 확인된 관계만 확정하게 한다.
보이지 않은 염소 주입기와 확인된 저수조의 구분 — 경로 보존|process,boundary,attribute||검토표에서 보이지 않은 염소 주입기와 확인된 저수조의 구분 — 경로 보존은 관측 빈칸과 확인값을 나눠 표시한다. 마지막 결과만으로 중간 관계를 복원하지 않는다.
응집조의 일부 기록만으로 여과지를 추정하지 않은 경로 — 결과 검증|part_of,state,other|동시 개입 분리 불가|일부 표본만 남은 상황에서 응집조의 일부 기록만으로 여과지를 추정하지 않은 경로 — 결과 검증은 관측된 단계와 추정된 단계를 분리한다. 미확인된 노드는 결론에 넣지 않는다. 동시 개입 분리 불가 항목은 확인된 관계만 확정하게 한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":52,"primary":"배수문 관측 공백에서 운영 당직표 범위 제한 — 순서 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":53,"primary":"현장 재검에 확인된 수압 센서와 수질 계측기의 부분 경로 — 상태 묶음","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":54,"primary":"여과지 표본 부족 뒤 저수조 연결을 보류하는 경계 직전 — 우선 처리","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":55,"primary":"보이지 않은 방류 기록과 확인된 염소 주입기의 구분 — 연결 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":56,"primary":"원수 유입구의 일부 기록만으로 여과지를 추정하지 않은 경로 — 출처 대조","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":57,"primary":"수질 계측기 관측 공백에서 수압 센서 범위 제한 — 범위 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":58,"primary":"후속 입력에 확인된 운영 당직표와 배수문의 부분 경로 — 운영 인계","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":59,"primary":"정수 펌프 표본 부족 뒤 응집조 연결을 보류하는 중앙 표본 — 회복 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":60,"primary":"보이지 않은 염소 주입기와 확인된 저수조의 구분 — 경로 보존","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":61,"primary":"응집조의 일부 기록만으로 여과지를 추정하지 않은 경로 — 결과 검증","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 10개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
