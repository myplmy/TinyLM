# A06 v06:122~131 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `879A201C10C8826B2F59E182AD970989380F91FC386A2224C6159CE02D91F212`
- registry SHA-256: `205E45BD6F9EC3620BB0E455430C3E96620D32BE73E8A209599946738184A1BB`
- locator는 `stage2_(16)relational_composition_high_density_train_v06.source.psv:122~131`으로 고정한다. source concept/text와 같은 locator registry primary 외 field·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v06_semantic_rewrite_122_131_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 122 | 저수조 관측 공백에서 염소 주입기 범위 제한 — 우선 처리 → 저수조 수위 재검 전 염소 주입 보류 | `state,boundary,other` | 확인 주입량과 미확인 수위를 구분해 증량을 보류한다. |
| 123 | 다음 교대에 확인된 누수 감시기와 정수 펌프의 부분 경로 — 연결 확인 → 누수 경보 기록 공백의 펌프 교대 인계 | `process,other,role` | 교대자가 확인 경보와 승인되지 않은 우회를 구분해 점검을 넘긴다. |
| 124 | 배수문 표본 부족 뒤 염소 주입기 연결을 보류하는 우회 승인 — 출처 대조 → 배수문 표본 부족 시 우회 운전 보류 분류 | `classification,boundary,state` | 위치 변화와 약품 주입 원인을 구분해 우회 운전 분류를 보류한다. |
| 125 | 보이지 않은 수압 센서와 확인된 수질 계측기의 구분 — 범위 확인 → 수압·수질 센서 시간차 대조 | `state,comparison,other` | 두 센서의 시각과 측정 지점을 비교해 관로 이상 단정을 막는다. |
| 126 | 여과지의 일부 기록만으로 원수 유입구를 추정하지 않은 경로 — 운영 인계 → 여과지 압력 누락 시 원수 유입 감량 | `process,boundary,attribute` | 유입량과 미확인 여과 저항을 구분해 밸브를 줄인다. |
| 127 | 방류 기록 관측 공백에서 염소 주입기 범위 제한 — 회복 판정 → 방류량 누락 시 염소 주입 단계 보류 | `part_of,state,other` | 전체 처리 과정의 확인 주입 단계와 누락된 방류 단계를 나눈다. |
| 128 | 교차 확인에 확인된 원수 유입구와 여과지의 부분 경로 — 경로 보존 → 원수 유입 후 여과지 기록 공백의 운전 보류 | `state,boundary,other` | 확인 유입 변화와 미확인 여과 상태를 구분해 밸브 조작을 보류한다. |
| 129 | 수질 계측기 표본 부족 뒤 정수 펌프 연결을 보류하는 장기 관찰 — 결과 검증 → 수질 표본 부족 시 펌프 점검 인계 | `process,other,role` | 교대자가 전류 변화와 미확인 수질 원인을 구분해 현장 점검을 넘긴다. |
| 130 | 보이지 않은 운영 당직표와 확인된 배수문의 구분 — 영향 검토 → 당직표 누락 시 배수문 운전 보류 분류 | `classification,boundary,state` | 확인 위치와 미확인 지시를 구분해 정상 운전 분류를 보류한다. |
| 131 | 정수 펌프의 일부 기록만으로 누수 감시기를 추정하지 않은 경로 — 예외 점검 → 펌프 전류와 누수 압력의 기록 상충 검토 | `state,comparison,other` | 두 값의 시각·위치를 비교해 펌프 고장 상태 단정을 막는다. |

## 새 text

| line | text |
|---:|---|
| 122 | 저수조 수위는 마지막 기록만 있고 그 뒤 확인값이 없을 때, 저수조 수위 재검 전 염소 주입 보류에서는 운영자가 확인된 주입량과 확인되지 않은 수위 변화를 구분한다. 후속 검증 누락 때문에 주입량을 늘리지 않아 저수조 농도 상승을 막는다. |
| 123 | 누수 감시기 경보 시각은 남아 있지만 펌프 우회 승인 시각이 없을 때, 누수 경보 기록 공백의 펌프 교대 인계는 교대자가 확인된 경보와 승인되지 않은 우회를 구분해 다음 당직자에게 현장 점검을 넘기는 과정이다. 예외 승인 시각 미상일 때는 펌프 출력을 바꾸지 않아 압력 변동을 막는다. |
| 124 | 배수문 위치 표본이 적고 염소 주입기 유량도 같은 시간에 바뀔 때, 배수문 표본 부족 시 우회 운전 보류 분류에서 운영자는 확인된 위치 변화와 확인되지 않은 약품 주입 원인을 구분한다. 추가 측정 전에는 우회 운전으로 분류하지 않아 정수 농도 변동을 막는다. |
| 125 | 수압 센서 압력 저하 기록보다 수질 계측기 탁도 상승 기록이 늦게 들어올 때, 수압·수질 센서 시간차 대조에서 운영자는 두 센서의 기록 시각과 측정 지점을 비교한다. 센서 채널 불일치가 해소되기 전에는 관로 이상 상태로 확정하지 않아 불필요한 급수 중단을 막는다. |
| 126 | 여과지 압력 기록은 끊겼지만 원수 유입량이 계속 증가할 때, 여과지 압력 누락 시 원수 유입 감량은 운영자가 확인된 유입량과 확인되지 않은 여과 저항을 구분해 밸브를 줄이는 과정이다. 압력값이 확인되기 전에는 유입량을 되돌리지 않아 여과지 넘침을 막는다. |
| 127 | 방류량은 기록되지 않았고 염소 주입기 유량만 남았을 때, 방류량 누락 시 염소 주입 단계 보류는 전체 정수 처리 과정 중 확인된 주입 단계와 비어 있는 방류 단계를 나누는 보류 상태다. 다음 단계 입력 결측 때문에 주입량을 정상으로 확정하지 않아 과다 투입을 막는다. |
| 128 | 원수 유입량은 확인됐지만 여과지 압력 기록이 중간에 빠졌을 때, 원수 유입 후 여과지 기록 공백의 운전 보류에서는 운영자가 확인된 유입 변화와 확인되지 않은 여과 상태를 구분한다. 중간 관측 결측 때문에 유입 밸브를 바로 열지 않아 압력 급락을 막는다. |
| 129 | 수질 계측기 표본이 적고 정수 펌프 전류가 변할 때, 수질 표본 부족 시 펌프 점검 인계는 교대자가 확인된 전류 변화와 확인되지 않은 수질 원인을 구분해 다음 당직자에게 현장 점검을 넘기는 과정이다. 출처 연결 불명 상태에서는 펌프 출력을 올리지 않아 수압 변동을 막는다. |
| 130 | 당직표에는 배수문 위치가 남아 있지만 조작 지시가 없을 때, 당직표 누락 시 배수문 운전 보류 분류에서 운영자는 확인된 위치와 확인되지 않은 지시를 구분한다. 지시가 확인되기 전에는 배수문을 정상 운전으로 분류하지 않아 과다 방류를 막는다. |
| 131 | 정수 펌프 전류는 상승했는데 누수 감시기 압력은 변하지 않을 때, 펌프 전류와 누수 압력의 기록 상충 검토에서는 운영자가 두 값의 기록 시각과 측정 위치를 비교한다. 식별 기록 상충이 해소되기 전에는 펌프 고장 상태로 확정하지 않아 불필요한 운전 중단을 막는다. |

## 원복 source 행

```text
저수조 관측 공백에서 염소 주입기 범위 제한 — 우선 처리|state,boundary,other|후속 검증 누락|관측 범위가 제한된 보고서에서 저수조 관측 공백에서 염소 주입기 범위 제한 — 우선 처리는 보이는 단계만 책임 있게 설명한다. 누락된 단계는 추가 확인 항목으로 넘긴다. 후속 검증 누락 항목은 확인된 관계만 확정하게 한다.
다음 교대에 확인된 누수 감시기와 정수 펌프의 부분 경로 — 연결 확인|process,other,role|예외 승인 시각 미상|자료가 서로 다른 시점에 모였다면 다음 교대에 확인된 누수 감시기와 정수 펌프의 부분 경로 — 연결 확인은 확인 시점이 겹치는 구간만 연결한다. 나머지는 보류 상태로 남긴다. 예외 승인 시각 미상 항목은 확인된 관계만 확정하게 한다.
배수문 표본 부족 뒤 염소 주입기 연결을 보류하는 우회 승인 — 출처 대조|classification,boundary,state||센서 기록이 끊긴 지점 뒤에는 배수문 표본 부족 뒤 염소 주입기 연결을 보류하는 우회 승인 — 출처 대조는 가능한 범위를 좁혀 둔다. 추가 측정 전에는 경로를 확정하지 않는다.
보이지 않은 수압 센서와 확인된 수질 계측기의 구분 — 범위 확인|state,comparison,other|센서 채널 불일치|확인된 표본이 적을수록 보이지 않은 수압 센서와 확인된 수질 계측기의 구분 — 범위 확인은 연결의 방향과 범위를 보수적으로 적는다. 결측을 정상 상태로 간주하지 않는다. 센서 채널 불일치 항목은 확인된 관계만 확정하게 한다.
여과지의 일부 기록만으로 원수 유입구를 추정하지 않은 경로 — 운영 인계|process,boundary,attribute||한 채널의 응답만으로 여과지의 일부 기록만으로 원수 유입구를 추정하지 않은 경로 — 운영 인계는 전체 연결을 판정하지 않는다. 다른 채널이 채워질 때까지 가능한 경로를 열어 둔다.
방류 기록 관측 공백에서 염소 주입기 범위 제한 — 회복 판정|part_of,state,other|다음 단계 입력 결측|현장에 남은 자료는 방류 기록 관측 공백에서 염소 주입기 범위 제한 — 회복 판정은 전체 경로 중 일부만 보여 준다. 보이지 않은 단계를 사실처럼 서술하지 않는다. 다음 단계 입력 결측 항목은 확인된 관계만 확정하게 한다.
교차 확인에 확인된 원수 유입구와 여과지의 부분 경로 — 경로 보존|state,boundary,other|중간 관측 결측|관측표에 보이는 구간만으로 교차 확인에 확인된 원수 유입구와 여과지의 부분 경로 — 경로 보존은 확인된 관계를 적는다. 빈 구간을 임의의 연결로 채우지 않는다. 중간 관측 결측 항목은 확인된 관계만 확정하게 한다.
수질 계측기 표본 부족 뒤 정수 펌프 연결을 보류하는 장기 관찰 — 결과 검증|process,other,role|출처 연결 불명|부분 로그를 읽을 때 수질 계측기 표본 부족 뒤 정수 펌프 연결을 보류하는 장기 관찰 — 결과 검증은 기록된 사실과 기록되지 않은 가능성을 구분한다. 가능성은 확정 문장으로 바꾸지 않는다. 출처 연결 불명 항목은 확인된 관계만 확정하게 한다.
보이지 않은 운영 당직표와 확인된 배수문의 구분 — 영향 검토|classification,boundary,state||검토표에서 보이지 않은 운영 당직표와 확인된 배수문의 구분 — 영향 검토는 관측 빈칸과 확인값을 나눠 표시한다. 마지막 결과만으로 중간 관계를 복원하지 않는다.
정수 펌프의 일부 기록만으로 누수 감시기를 추정하지 않은 경로 — 예외 점검|state,comparison,other|식별 기록 상충|일부 표본만 남은 상황에서 정수 펌프의 일부 기록만으로 누수 감시기를 추정하지 않은 경로 — 예외 점검은 관측된 단계와 추정된 단계를 분리한다. 미확인된 노드는 결론에 넣지 않는다. 식별 기록 상충 항목은 확인된 관계만 확정하게 한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":122,"primary":"저수조 관측 공백에서 염소 주입기 범위 제한 — 우선 처리","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":123,"primary":"다음 교대에 확인된 누수 감시기와 정수 펌프의 부분 경로 — 연결 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":124,"primary":"배수문 표본 부족 뒤 염소 주입기 연결을 보류하는 우회 승인 — 출처 대조","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":125,"primary":"보이지 않은 수압 센서와 확인된 수질 계측기의 구분 — 범위 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":126,"primary":"여과지의 일부 기록만으로 원수 유입구를 추정하지 않은 경로 — 운영 인계","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":127,"primary":"방류 기록 관측 공백에서 염소 주입기 범위 제한 — 회복 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":128,"primary":"교차 확인에 확인된 원수 유입구와 여과지의 부분 경로 — 경로 보존","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":129,"primary":"수질 계측기 표본 부족 뒤 정수 펌프 연결을 보류하는 장기 관찰 — 결과 검증","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":130,"primary":"보이지 않은 운영 당직표와 확인된 배수문의 구분 — 영향 검토","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":131,"primary":"정수 펌프의 일부 기록만으로 누수 감시기를 추정하지 않은 경로 — 예외 점검","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 10개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
