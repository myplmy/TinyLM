# A06 v06:72~80 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `DE53BF64D8FBA28282C723603CA803D268BEEB5EA5170593E5349E5D04C1774C`
- registry SHA-256: `30F565B3C6586ADDC7BE3529B5F091B0DAACC4E202AD17569F4594F82FC356E5`
- 감사 대기열에 남은 locator만 `stage2_(16)relational_composition_high_density_train_v06.source.psv:72~80`으로 고정한다. 81행은 표식·대기열이 없어 보존한다. source concept/text와 같은 locator registry primary 외 field·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v06_semantic_rewrite_72_80_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 72 | 염소 주입기 관측 공백에서 저수조 범위 제한 — 연결 확인 → 염소 주입량 공백 시 저수조 수위 확인 | `process,boundary,attribute` | 확인 수위와 누락된 주입량을 구분하고 투입 변경을 멈춘다. |
| 73 | 보류 해제에 확인된 응집조와 여과지의 부분 경로 — 출처 대조 → 응집조와 여과지 동시 회복 판단 | `part_of,state,other` | 전체 과정에서 겹친 회복 구간과 원인 불가분을 표현한다. |
| 74 | 저수조 표본 부족 뒤 운영 당직표 연결을 보류하는 저부하 운전 — 범위 확인 → 저수조 표본 부족 시 저부하 운전 보류 | `state,boundary,other` | 확인 수위와 미확인 운전 지시를 구분해 저부하 운전을 보류한다. |
| 75 | 보이지 않은 누수 감시기와 확인된 정수 펌프의 구분 — 운영 인계 → 누수 감시기 기록 공백의 펌프 점검 인계 | `process,other,role` | 교대자가 펌프 전류와 누락된 경보를 구분해 점검을 인계한다. |
| 76 | 배수문의 일부 기록만으로 운영 당직표를 추정하지 않은 경로 — 회복 판정 → 배수문 부분 기록의 운전 지시 분류 | `classification,boundary,state` | 위치 기록과 미확인 당직 지시를 구분해 상태를 분류한다. |
| 77 | 수압 센서 관측 공백에서 수질 계측기 범위 제한 — 경로 보존 → 수압 기록 누락 시 수질 측정 대조 | `state,comparison,other` | 수압·탁도 추세의 관측 범위를 비교하고 출력 조정을 보류한다. |
| 78 | 긴급 확인에 확인된 여과지와 원수 유입구의 부분 경로 — 결과 검증 → 여과지와 원수 유입 긴급 점검 | `process,boundary,attribute` | 압력·유입량 변화의 시점을 구분해 유입 조정을 결정한다. |
| 79 | 방류 기록 표본 부족 뒤 수질 계측기 연결을 보류하는 경보 누적 — 영향 검토 → 방류 기록 표본 부족 시 수질 점검 보류 | `part_of,state,other` | 전체 처리 과정의 확인된 방류 단계와 다음 측정 결측을 분리한다. |
| 80 | 보이지 않은 원수 유입구와 확인된 여과지의 구분 — 예외 점검 → 원수 유입 측정 공백의 여과지 점검 | `state,boundary,other` | 확인 압력과 누락 유입량을 구분해 증량을 보류한다. |

## 새 text

| line | text |
|---:|---|
| 72 | 염소 주입기 유량 기록이 비어 있고 저수조 수위만 확인될 때, 염소 주입량 공백 시 저수조 수위 확인은 운영자가 확인된 수위와 확인되지 않은 주입량을 구분하는 과정이다. 주입량이 확인되기 전에는 투입량을 바꾸지 않아 저수조 농도 변동을 막는다. |
| 73 | 응집조 수위와 여과지 압력이 같은 시각에 함께 낮아졌을 때, 응집조와 여과지 동시 회복 판단은 전체 정수 과정 중 두 변화가 겹친 구간을 나타내는 보류 상태다. 동시 개입 분리 불가 때문에 운영자는 어느 조치가 먼저 효과를 냈는지 확정하지 않아 성급한 유입 증가를 막는다. |
| 74 | 저수조 수위 표본이 적고 저부하 운전 지시만 당직표에 남았을 때, 저수조 표본 부족 시 저부하 운전 보류에서는 운영자가 확인된 수위와 확인되지 않은 운전 지시를 구분한다. 후속 검증 누락 때문에 저부하 운전을 시작하지 않아 저수조 수위 급락을 막는다. |
| 75 | 누수 감시기 경보 기록이 비어 있지만 정수 펌프 전류는 확인될 때, 누수 감시기 기록 공백의 펌프 점검 인계는 교대자가 확인된 펌프 전류와 확인되지 않은 누수 경보를 구분해 다음 당직자에게 현장 점검을 넘기는 과정이다. 예외 승인 시각 미상일 때는 펌프 출력을 바꾸지 않아 압력 변동을 막는다. |
| 76 | 배수문 위치는 일부 시각에만 기록되고 당직표 지시는 확인되지 않을 때, 배수문 부분 기록의 운전 지시 분류에서는 운영자가 확인된 위치와 확인되지 않은 운전 지시를 구분해 운전 보류 상태로 분류한다. 지시가 확인되기 전에는 배수문을 개방 상태로 확정하지 않아 과다 방류를 막는다. |
| 77 | 수압 센서 값이 누락되고 수질 계측기 탁도값만 들어올 때, 수압 기록 누락 시 수질 측정 대조에서는 운영자가 이전 수압 추세와 현재 탁도 추세를 비교한다. 센서 채널 불일치 상태에서는 관로 막힘으로 단정하지 않아 불필요한 펌프 정지를 막는다. |
| 78 | 여과지 압력이 갑자기 오르고 원수 유입량도 변할 때, 여과지와 원수 유입 긴급 점검은 운영자가 두 변화의 시점과 수치를 구분해 원인을 확인하는 과정이다. 압력이 더 높아지면 유입량을 줄여 여과지 막힘을 막는다. |
| 79 | 방류 기록 표본이 적고 다음 수질 측정값도 들어오지 않을 때, 방류 기록 표본 부족 시 수질 점검 보류는 전체 처리 과정 중 확인된 방류 단계와 비어 있는 수질 측정 단계를 나누는 보류 상태다. 다음 단계 입력 결측 때문에 방류량을 기준으로 약품 투입량을 바꾸지 않아 근거 없는 농도 조정을 막는다. |
| 80 | 원수 유입량 기록이 없고 여과지 압력만 확인될 때, 원수 유입 측정 공백의 여과지 점검에서는 운영자가 확인된 압력과 확인되지 않은 유입량을 구분한다. 중간 관측 결측 때문에 유입량 증가는 보류하여 여과지 압력 급등을 막는다. |

## 원복 source 행

```text
염소 주입기 관측 공백에서 저수조 범위 제한 — 연결 확인|process,boundary,attribute||관측 범위가 제한된 보고서에서 염소 주입기 관측 공백에서 저수조 범위 제한 — 연결 확인은 보이는 단계만 책임 있게 설명한다. 누락된 단계는 추가 확인 항목으로 넘긴다.
보류 해제에 확인된 응집조와 여과지의 부분 경로 — 출처 대조|part_of,state,other|동시 개입 분리 불가|자료가 서로 다른 시점에 모였다면 보류 해제에 확인된 응집조와 여과지의 부분 경로 — 출처 대조는 확인 시점이 겹치는 구간만 연결한다. 나머지는 보류 상태로 남긴다. 동시 개입 분리 불가 항목은 확인된 관계만 확정하게 한다.
저수조 표본 부족 뒤 운영 당직표 연결을 보류하는 저부하 운전 — 범위 확인|state,boundary,other|후속 검증 누락|센서 기록이 끊긴 지점 뒤에는 저수조 표본 부족 뒤 운영 당직표 연결을 보류하는 저부하 운전 — 범위 확인은 가능한 범위를 좁혀 둔다. 추가 측정 전에는 경로를 확정하지 않는다. 후속 검증 누락 항목은 확인된 관계만 확정하게 한다.
보이지 않은 누수 감시기와 확인된 정수 펌프의 구분 — 운영 인계|process,other,role|예외 승인 시각 미상|확인된 표본이 적을수록 보이지 않은 누수 감시기와 확인된 정수 펌프의 구분 — 운영 인계는 연결의 방향과 범위를 보수적으로 적는다. 결측을 정상 상태로 간주하지 않는다. 예외 승인 시각 미상 항목은 확인된 관계만 확정하게 한다.
배수문의 일부 기록만으로 운영 당직표를 추정하지 않은 경로 — 회복 판정|classification,boundary,state||한 채널의 응답만으로 배수문의 일부 기록만으로 운영 당직표를 추정하지 않은 경로 — 회복 판정은 전체 연결을 판정하지 않는다. 다른 채널이 채워질 때까지 가능한 경로를 열어 둔다.
수압 센서 관측 공백에서 수질 계측기 범위 제한 — 경로 보존|state,comparison,other|센서 채널 불일치|현장에 남은 자료는 수압 센서 관측 공백에서 수질 계측기 범위 제한 — 경로 보존은 전체 경로 중 일부만 보여 준다. 보이지 않은 단계를 사실처럼 서술하지 않는다. 센서 채널 불일치 항목은 확인된 관계만 확정하게 한다.
긴급 확인에 확인된 여과지와 원수 유입구의 부분 경로 — 결과 검증|process,boundary,attribute||관측표에 보이는 구간만으로 긴급 확인에 확인된 여과지와 원수 유입구의 부분 경로 — 결과 검증은 확인된 관계를 적는다. 빈 구간을 임의의 연결로 채우지 않는다.
방류 기록 표본 부족 뒤 수질 계측기 연결을 보류하는 경보 누적 — 영향 검토|part_of,state,other|다음 단계 입력 결측|부분 로그를 읽을 때 방류 기록 표본 부족 뒤 수질 계측기 연결을 보류하는 경보 누적 — 영향 검토는 기록된 사실과 기록되지 않은 가능성을 구분한다. 가능성은 확정 문장으로 바꾸지 않는다. 다음 단계 입력 결측 항목은 확인된 관계만 확정하게 한다.
보이지 않은 원수 유입구와 확인된 여과지의 구분 — 예외 점검|state,boundary,other|중간 관측 결측|검토표에서 보이지 않은 원수 유입구와 확인된 여과지의 구분 — 예외 점검은 관측 빈칸과 확인값을 나눠 표시한다. 마지막 결과만으로 중간 관계를 복원하지 않는다. 중간 관측 결측 항목은 확인된 관계만 확정하게 한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":72,"primary":"염소 주입기 관측 공백에서 저수조 범위 제한 — 연결 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":73,"primary":"보류 해제에 확인된 응집조와 여과지의 부분 경로 — 출처 대조","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":74,"primary":"저수조 표본 부족 뒤 운영 당직표 연결을 보류하는 저부하 운전 — 범위 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":75,"primary":"보이지 않은 누수 감시기와 확인된 정수 펌프의 구분 — 운영 인계","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":76,"primary":"배수문의 일부 기록만으로 운영 당직표를 추정하지 않은 경로 — 회복 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":77,"primary":"수압 센서 관측 공백에서 수질 계측기 범위 제한 — 경로 보존","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":78,"primary":"긴급 확인에 확인된 여과지와 원수 유입구의 부분 경로 — 결과 검증","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":79,"primary":"방류 기록 표본 부족 뒤 수질 계측기 연결을 보류하는 경보 누적 — 영향 검토","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":80,"primary":"보이지 않은 원수 유입구와 확인된 여과지의 구분 — 예외 점검","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 9개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
