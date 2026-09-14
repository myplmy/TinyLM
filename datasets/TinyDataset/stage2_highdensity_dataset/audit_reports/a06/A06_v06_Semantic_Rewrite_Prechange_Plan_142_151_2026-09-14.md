# A06 v06:142~151 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `A7180E8B714834D059D0D3B489FEDB823E000E424B22023D8E6FD0416729F0E5`
- registry SHA-256: `BDF3C60E1D0728793710E1CC9F1EE66F150F7F97B9B6F43385C2CE9693E08356`
- locator는 `stage2_(16)relational_composition_high_density_train_v06.source.psv:142~151`으로 고정한다. source concept/text와 같은 locator registry primary 외 field·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v06_semantic_rewrite_142_151_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 142 | 운영 당직표 관측 공백에서 배수문 범위 제한 — 범위 확인 → 배수문 위치만 기록된 당직표의 운전 보류 분류 | `classification,boundary,state` | 확인 위치와 미확인 조작 지시를 구분해 운전 보류로 분류한다. |
| 143 | 현장 재검에 확인된 정수 펌프와 누수 감시기의 부분 경로 — 운영 인계 → 정수 펌프 운전 기록과 누수 경보 대조 | `state,comparison,other` | 펌프 전류와 누수 압력의 시각·위치를 비교해 고장 단정을 막는다. |
| 144 | 염소 주입기 표본 부족 뒤 원수 유입구 연결을 보류하는 배치 변경 — 회복 판정 → 염소 주입 표본 부족 시 원수 유입 조정 | `process,boundary,attribute` | 확인 잔류 염소와 미확인 주입량을 구분해 유입량을 조정한다. |
| 145 | 보이지 않은 응집조와 확인된 여과지의 구분 — 경로 보존 → 응집조 교반과 여과지 세척의 동시 조치 보류 | `part_of,state,other` | 전체 정수 과정에서 동시 조치의 원인을 나누지 못해 변경을 보류한다. |
| 146 | 저수조의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 결과 검증 → 저수조 수위 재검 전 염소 농도 조정 보류 | `state,boundary,other` | 확인 농도와 미확인 수위를 구분해 농도 조정을 보류한다. |
| 147 | 누수 감시기 관측 공백에서 정수 펌프 범위 제한 — 영향 검토 → 정수 펌프 우회 승인 시각 확인 교대 점검 | `process,other,role` | 교대자가 확인 경보와 승인 시각을 대조해 현장 점검을 인계한다. |
| 148 | 후속 입력에 확인된 배수문과 운영 당직표의 부분 경로 — 예외 점검 → 배수문 위치·당직 지시 불일치 분류 | `classification,boundary,state` | 확인 위치와 미확인 지시를 구분해 정상 운전 분류를 보류한다. |
| 149 | 수압 센서 표본 부족 뒤 방류 기록 연결을 보류하는 정상 복귀 — 독립 확인 → 수압 센서와 방류 기록 시각차 대조 | `state,comparison,other` | 압력값과 방류 기록의 시각을 비교해 정상 복귀 단정을 막는다. |
| 150 | 보이지 않은 여과지와 확인된 원수 유입구의 구분 — 분기 기록 → 여과지 압력 미확인 시 원수 유입 감량 | `process,boundary,attribute` | 확인 유입량과 미확인 압력을 구분해 밸브를 줄인다. |
| 151 | 방류 기록의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 중간 판정 → 방류량 확인 전 염소 주입 보류 | `part_of,state,other` | 전체 처리 과정의 확인 방류와 비어 있는 다음 입력을 나눈다. |

## 새 text

| line | text |
|---:|---|
| 142 | 당직표에는 배수문 위치만 남아 있고 조작 지시가 없을 때, 배수문 위치만 기록된 당직표의 운전 보류 분류에서 운영자는 확인된 위치와 확인되지 않은 지시를 구분한다. 지시가 확인되기 전에는 배수문을 정상 운전으로 분류하지 않아 과다 방류를 막는다. |
| 143 | 정수 펌프 전류는 증가했는데 누수 감시기 압력은 변하지 않을 때, 정수 펌프 운전 기록과 누수 경보 대조에서는 운영자가 두 기록의 시각과 측정 위치를 비교한다. 식별 기록 상충이 해소되기 전에는 펌프 고장 상태로 확정하지 않아 불필요한 운전 중단을 막는다. |
| 144 | 염소 주입량 표본이 적고 원수 유입량이 늘어날 때, 염소 주입 표본 부족 시 원수 유입 조정은 운영자가 확인된 잔류 염소와 확인되지 않은 주입량을 구분해 유입 밸브를 조정하는 과정이다. 주입량이 확인되기 전에는 유입량을 더 늘리지 않아 저수조 농도 변동을 막는다. |
| 145 | 응집조 교반을 시작한 시각과 여과지 세척을 시작한 시각이 겹쳐 수위와 압력이 함께 변할 때, 응집조 교반과 여과지 세척의 동시 조치 보류는 전체 정수 과정에서 원인을 나누지 못한 보류 상태다. 동시 개입 분리 불가 때문에 두 설비의 운전을 함께 바꾸지 않아 급수 압력 변동을 막는다. |
| 146 | 저수조 수위는 일부 기록만 있고 현재 염소 농도만 확인될 때, 저수조 수위 재검 전 염소 농도 조정 보류에서는 운영자가 확인된 농도와 확인되지 않은 수위 변화를 구분한다. 후속 검증 누락 때문에 주입량을 바꾸지 않아 저수조 농도 상승을 막는다. |
| 147 | 누수 감시기 경보는 남아 있지만 정수 펌프 우회 승인 시각이 없을 때, 정수 펌프 우회 승인 시각 확인 교대 점검은 교대자가 확인된 경보와 승인 시각을 대조해 다음 당직자에게 현장 점검을 넘기는 과정이다. 예외 승인 시각 미상일 때는 펌프 출력을 바꾸지 않아 압력 변동을 막는다. |
| 148 | 배수문 위치는 확인됐지만 당직표의 조작 지시가 다를 때, 배수문 위치·당직 지시 불일치 분류에서 운영자는 확인된 위치와 확인되지 않은 지시를 구분한다. 지시가 확인되기 전에는 배수문을 정상 운전으로 분류하지 않아 과다 방류를 막는다. |
| 149 | 수압 센서 압력값은 들어왔지만 방류 기록 시각이 늦게 남았을 때, 수압 센서와 방류 기록 시각차 대조에서는 운영자가 두 기록의 시각과 측정 지점을 비교한다. 센서 채널 불일치가 해소되기 전에는 정상 복귀 상태로 확정하지 않아 잘못된 방류량 증가를 막는다. |
| 150 | 여과지 압력 기록은 없는데 원수 유입량이 늘어날 때, 여과지 압력 미확인 시 원수 유입 감량은 운영자가 확인된 유입량과 확인되지 않은 여과 저항을 구분해 밸브를 줄이는 과정이다. 압력값이 확인되기 전에는 유입량을 되돌리지 않아 여과지 넘침을 막는다. |
| 151 | 방류량은 일부 기록만 있고 다음 단계 염소 주입량이 비어 있을 때, 방류량 확인 전 염소 주입 보류는 전체 정수 처리 과정 중 확인된 방류 단계와 비어 있는 주입 단계를 나누는 보류 상태다. 다음 단계 입력 결측 때문에 주입량을 정상으로 확정하지 않아 과다 투입을 막는다. |

## 원복 source 행

```text
운영 당직표 관측 공백에서 배수문 범위 제한 — 범위 확인|classification,boundary,state||관측 범위가 제한된 보고서에서 운영 당직표 관측 공백에서 배수문 범위 제한 — 범위 확인은 보이는 단계만 책임 있게 설명한다. 누락된 단계는 추가 확인 항목으로 넘긴다.
현장 재검에 확인된 정수 펌프와 누수 감시기의 부분 경로 — 운영 인계|state,comparison,other|식별 기록 상충|자료가 서로 다른 시점에 모였다면 현장 재검에 확인된 정수 펌프와 누수 감시기의 부분 경로 — 운영 인계는 확인 시점이 겹치는 구간만 연결한다. 나머지는 보류 상태로 남긴다. 식별 기록 상충 항목은 확인된 관계만 확정하게 한다.
염소 주입기 표본 부족 뒤 원수 유입구 연결을 보류하는 배치 변경 — 회복 판정|process,boundary,attribute||센서 기록이 끊긴 지점 뒤에는 염소 주입기 표본 부족 뒤 원수 유입구 연결을 보류하는 배치 변경 — 회복 판정은 가능한 범위를 좁혀 둔다. 추가 측정 전에는 경로를 확정하지 않는다.
보이지 않은 응집조와 확인된 여과지의 구분 — 경로 보존|part_of,state,other|동시 개입 분리 불가|확인된 표본이 적을수록 보이지 않은 응집조와 확인된 여과지의 구분 — 경로 보존은 연결의 방향과 범위를 보수적으로 적는다. 결측을 정상 상태로 간주하지 않는다. 동시 개입 분리 불가 항목은 확인된 관계만 확정하게 한다.
저수조의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 결과 검증|state,boundary,other|후속 검증 누락|한 채널의 응답만으로 저수조의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 결과 검증은 전체 연결을 판정하지 않는다. 다른 채널이 채워질 때까지 가능한 경로를 열어 둔다. 후속 검증 누락 항목은 확인된 관계만 확정하게 한다.
누수 감시기 관측 공백에서 정수 펌프 범위 제한 — 영향 검토|process,other,role|예외 승인 시각 미상|현장에 남은 자료는 누수 감시기 관측 공백에서 정수 펌프 범위 제한 — 영향 검토는 전체 경로 중 일부만 보여 준다. 보이지 않은 단계를 사실처럼 서술하지 않는다. 예외 승인 시각 미상 항목은 확인된 관계만 확정하게 한다.
후속 입력에 확인된 배수문과 운영 당직표의 부분 경로 — 예외 점검|classification,boundary,state||관측표에 보이는 구간만으로 후속 입력에 확인된 배수문과 운영 당직표의 부분 경로 — 예외 점검은 확인된 관계를 적는다. 빈 구간을 임의의 연결로 채우지 않는다.
수압 센서 표본 부족 뒤 방류 기록 연결을 보류하는 정상 복귀 — 독립 확인|state,comparison,other|센서 채널 불일치|부분 로그를 읽을 때 수압 센서 표본 부족 뒤 방류 기록 연결을 보류하는 정상 복귀 — 독립 확인은 기록된 사실과 기록되지 않은 가능성을 구분한다. 가능성은 확정 문장으로 바꾸지 않는다. 센서 채널 불일치 항목은 확인된 관계만 확정하게 한다.
보이지 않은 여과지와 확인된 원수 유입구의 구분 — 분기 기록|process,boundary,attribute||검토표에서 보이지 않은 여과지와 확인된 원수 유입구의 구분 — 분기 기록은 관측 빈칸과 확인값을 나눠 표시한다. 마지막 결과만으로 중간 관계를 복원하지 않는다.
방류 기록의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 중간 판정|part_of,state,other|다음 단계 입력 결측|일부 표본만 남은 상황에서 방류 기록의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 중간 판정은 관측된 단계와 추정된 단계를 분리한다. 미확인된 노드는 결론에 넣지 않는다. 다음 단계 입력 결측 항목은 확인된 관계만 확정하게 한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":142,"primary":"운영 당직표 관측 공백에서 배수문 범위 제한 — 범위 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":143,"primary":"현장 재검에 확인된 정수 펌프와 누수 감시기의 부분 경로 — 운영 인계","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":144,"primary":"염소 주입기 표본 부족 뒤 원수 유입구 연결을 보류하는 배치 변경 — 회복 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":145,"primary":"보이지 않은 응집조와 확인된 여과지의 구분 — 경로 보존","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":146,"primary":"저수조의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 결과 검증","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":147,"primary":"누수 감시기 관측 공백에서 정수 펌프 범위 제한 — 영향 검토","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":148,"primary":"후속 입력에 확인된 배수문과 운영 당직표의 부분 경로 — 예외 점검","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":149,"primary":"수압 센서 표본 부족 뒤 방류 기록 연결을 보류하는 정상 복귀 — 독립 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":150,"primary":"보이지 않은 여과지와 확인된 원수 유입구의 구분 — 분기 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":151,"primary":"방류 기록의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 중간 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 10개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
