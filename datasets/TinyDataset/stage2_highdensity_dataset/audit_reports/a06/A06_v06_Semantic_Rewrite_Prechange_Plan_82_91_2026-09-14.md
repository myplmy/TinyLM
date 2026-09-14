# A06 v06:82~91 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `151E35D3CBC21D0DA934D785E68D129651BB1805A4906934BA82D4169483BD7D`
- registry SHA-256: `DE8755D196F1151E2BE2AC1918C141E50D44286876C60827F0E51F622403B38F`
- locator는 `stage2_(16)relational_composition_high_density_train_v06.source.psv:82~91`으로 고정한다. source concept/text와 같은 locator registry primary 외 field·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v06_semantic_rewrite_82_91_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 82 | 운영 당직표 관측 공백에서 배수문 범위 제한 — 분기 기록 → 운영 당직표 공백의 배수문 지시 분류 | `classification,boundary,state` | 당직 지시와 위치 기록을 구분해 상태를 분류한다. |
| 83 | 현장 재검에 확인된 정수 펌프와 누수 감시기의 부분 경로 — 중간 판정 → 정수 펌프와 누수 감시기 현장 재검 | `state,comparison,other` | 전류·압력 기록을 현장에서 대조하고 누수 단정을 멈춘다. |
| 84 | 염소 주입기 표본 부족 뒤 원수 유입구 연결을 보류하는 우회 승인 — 신호 전달 → 염소 주입 표본 부족 시 원수 유입 점검 | `process,boundary,attribute` | 주입량·유입량 측정 시각을 구분해 우회 승인을 보류한다. |
| 85 | 보이지 않은 응집조와 확인된 여과지의 구분 — 대상 추적 → 응집조와 여과지 동시 변화 보류 | `part_of,state,other` | 전체 과정 중 두 설비 변화가 겹친 구간을 보류 상태로 나타낸다. |
| 86 | 저수조의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 순서 기록 → 저수조 부분 기록의 염소 주입 보류 | `state,boundary,other` | 확인 수위와 누락 주입량을 구분해 증량을 멈춘다. |
| 87 | 누수 감시기 관측 공백에서 정수 펌프 범위 제한 — 상태 묶음 → 누수 감시기 공백의 펌프 운전 인계 | `process,other,role` | 교대자가 펌프 기록과 누락 경보를 구분해 운전을 인계한다. |
| 88 | 후속 입력에 확인된 배수문과 운영 당직표의 부분 경로 — 우선 처리 → 후속 당직표의 배수문 지시 분류 | `classification,boundary,state` | 새 지시와 미확인 위치를 구분해 우선 조치를 분류한다. |
| 89 | 수압 센서 표본 부족 뒤 방류 기록 연결을 보류하는 장기 관찰 — 연결 확인 → 수압 센서 표본 부족 시 방류 기록 대조 | `state,comparison,other` | 압력·방류 기록의 시간과 수치를 대조해 연결을 보류한다. |
| 90 | 보이지 않은 여과지와 확인된 원수 유입구의 구분 — 출처 대조 → 여과지 압력 공백의 원수 유입 확인 | `process,boundary,attribute` | 유입량과 누락 압력값을 구분해 증량 전 확인한다. |
| 91 | 방류 기록의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 범위 확인 → 방류 기록 부분의 염소 주입 보류 | `part_of,state,other` | 전체 처리 과정의 확인 방류 단계와 누락 주입 단계를 나눈다. |

## 새 text

| line | text |
|---:|---|
| 82 | 당직표에 배수문 관련 지시가 비어 있고 위치 기록만 남았을 때, 운영 당직표 공백의 배수문 지시 분류에서는 운영자가 확인된 위치와 확인되지 않은 운전 지시를 구분해 운전 보류 상태로 분류한다. 지시가 확인되기 전에는 개방 순서를 확정하지 않아 과다 방류를 막는다. |
| 83 | 현장 재검에서 정수 펌프 전류는 정상인데 누수 감시기 압력은 낮게 나타날 때, 정수 펌프와 누수 감시기 현장 재검에서는 운영자가 두 기록의 수치를 비교한다. 식별 기록 상충 상태에서는 누수로 단정하지 않아 불필요한 펌프 정지를 막는다. |
| 84 | 염소 주입량 표본이 한 차례뿐이고 원수 유입량은 다른 시각에 바뀌었을 때, 염소 주입 표본 부족 시 원수 유입 점검은 운영자가 두 측정의 시각과 수치를 구분하는 과정이다. 유입량을 늘리기 전에는 주입량을 확인해 저수조 농도 변동을 막는다. |
| 85 | 응집조 수위와 여과지 압력이 같은 시각에 바뀌었을 때, 응집조와 여과지 동시 변화 보류는 전체 정수 과정 중 두 변화가 겹친 구간을 나타내는 보류 상태다. 동시 개입 분리 불가 때문에 어느 설비 조치가 먼저 효과를 냈는지 확정하지 않아 성급한 유입 증가를 막는다. |
| 86 | 저수조 수위는 일부 시각에만 기록되고 염소 주입량은 그 뒤에 누락됐을 때, 저수조 부분 기록의 염소 주입 보류에서는 운영자가 확인된 수위와 확인되지 않은 주입량을 구분한다. 후속 검증 누락 때문에 주입량 증가는 보류하여 저수조 농도 변동을 막는다. |
| 87 | 누수 감시기 경보가 비어 있고 정수 펌프 운전 기록만 남았을 때, 누수 감시기 공백의 펌프 운전 인계는 교대자가 확인된 펌프 상태와 확인되지 않은 경보를 구분해 다음 당직자에게 운전 점검을 넘기는 과정이다. 예외 승인 시각 미상일 때는 펌프 출력을 바꾸지 않아 압력 변동을 막는다. |
| 88 | 당직표에 새 배수문 지시는 있지만 위치 기록이 아직 들어오지 않을 때, 후속 당직표의 배수문 지시 분류에서는 운영자가 확인된 지시와 확인되지 않은 위치를 구분해 운전 보류 상태로 분류한다. 위치가 확인되기 전에는 자동 복귀를 시작하지 않아 과다 방류를 막는다. |
| 89 | 수압 센서 표본이 적고 방류 기록이 다른 채널에서 늦게 들어올 때, 수압 센서 표본 부족 시 방류 기록 대조에서는 운영자가 두 기록의 시간과 수치를 비교한다. 센서 채널 불일치 상태에서는 펌프 출력을 조정하지 않아 불필요한 급수 제한을 막는다. |
| 90 | 여과지 압력 기록이 비어 있고 원수 유입량만 확인될 때, 여과지 압력 공백의 원수 유입 확인은 운영자가 확인된 유입량과 확인되지 않은 압력값을 구분하는 과정이다. 압력 측정 전에는 유입량을 늘리지 않아 여과지 막힘 위험을 낮춘다. |
| 91 | 방류량은 일부 시각에만 기록되고 다음 단계 염소 주입량은 없을 때, 방류 기록 부분의 염소 주입 보류는 전체 처리 과정 중 확인된 방류 단계와 비어 있는 주입 단계를 나누는 보류 상태다. 다음 단계 입력 결측 때문에 주입량을 정상으로 확정하지 않아 근거 없는 농도 조정을 막는다. |

## 원복 source 행

```text
운영 당직표 관측 공백에서 배수문 범위 제한 — 분기 기록|classification,boundary,state||관측 범위가 제한된 보고서에서 운영 당직표 관측 공백에서 배수문 범위 제한 — 분기 기록은 보이는 단계만 책임 있게 설명한다. 누락된 단계는 추가 확인 항목으로 넘긴다.
현장 재검에 확인된 정수 펌프와 누수 감시기의 부분 경로 — 중간 판정|state,comparison,other|식별 기록 상충|자료가 서로 다른 시점에 모였다면 현장 재검에 확인된 정수 펌프와 누수 감시기의 부분 경로 — 중간 판정은 확인 시점이 겹치는 구간만 연결한다. 나머지는 보류 상태로 남긴다. 식별 기록 상충 항목은 확인된 관계만 확정하게 한다.
염소 주입기 표본 부족 뒤 원수 유입구 연결을 보류하는 우회 승인 — 신호 전달|process,boundary,attribute||센서 기록이 끊긴 지점 뒤에는 염소 주입기 표본 부족 뒤 원수 유입구 연결을 보류하는 우회 승인 — 신호 전달은 가능한 범위를 좁혀 둔다. 추가 측정 전에는 경로를 확정하지 않는다.
보이지 않은 응집조와 확인된 여과지의 구분 — 대상 추적|part_of,state,other|동시 개입 분리 불가|확인된 표본이 적을수록 보이지 않은 응집조와 확인된 여과지의 구분 — 대상 추적은 연결의 방향과 범위를 보수적으로 적는다. 결측을 정상 상태로 간주하지 않는다. 동시 개입 분리 불가 항목은 확인된 관계만 확정하게 한다.
저수조의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 순서 기록|state,boundary,other|후속 검증 누락|한 채널의 응답만으로 저수조의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 순서 기록은 전체 연결을 판정하지 않는다. 다른 채널이 채워질 때까지 가능한 경로를 열어 둔다. 후속 검증 누락 항목은 확인된 관계만 확정하게 한다.
누수 감시기 관측 공백에서 정수 펌프 범위 제한 — 상태 묶음|process,other,role|예외 승인 시각 미상|현장에 남은 자료는 누수 감시기 관측 공백에서 정수 펌프 범위 제한 — 상태 묶음은 전체 경로 중 일부만 보여 준다. 보이지 않은 단계를 사실처럼 서술하지 않는다. 예외 승인 시각 미상 항목은 확인된 관계만 확정하게 한다.
후속 입력에 확인된 배수문과 운영 당직표의 부분 경로 — 우선 처리|classification,boundary,state||관측표에 보이는 구간만으로 후속 입력에 확인된 배수문과 운영 당직표의 부분 경로 — 우선 처리는 확인된 관계를 적는다. 빈 구간을 임의의 연결로 채우지 않는다.
수압 센서 표본 부족 뒤 방류 기록 연결을 보류하는 장기 관찰 — 연결 확인|state,comparison,other|센서 채널 불일치|부분 로그를 읽을 때 수압 센서 표본 부족 뒤 방류 기록 연결을 보류하는 장기 관찰 — 연결 확인은 기록된 사실과 기록되지 않은 가능성을 구분한다. 가능성은 확정 문장으로 바꾸지 않는다. 센서 채널 불일치 항목은 확인된 관계만 확정하게 한다.
보이지 않은 여과지와 확인된 원수 유입구의 구분 — 출처 대조|process,boundary,attribute||검토표에서 보이지 않은 여과지와 확인된 원수 유입구의 구분 — 출처 대조는 관측 빈칸과 확인값을 나눠 표시한다. 마지막 결과만으로 중간 관계를 복원하지 않는다.
방류 기록의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 범위 확인|part_of,state,other|다음 단계 입력 결측|일부 표본만 남은 상황에서 방류 기록의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 범위 확인은 관측된 단계와 추정된 단계를 분리한다. 미확인된 노드는 결론에 넣지 않는다. 다음 단계 입력 결측 항목은 확인된 관계만 확정하게 한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":82,"primary":"운영 당직표 관측 공백에서 배수문 범위 제한 — 분기 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":83,"primary":"현장 재검에 확인된 정수 펌프와 누수 감시기의 부분 경로 — 중간 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":84,"primary":"염소 주입기 표본 부족 뒤 원수 유입구 연결을 보류하는 우회 승인 — 신호 전달","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":85,"primary":"보이지 않은 응집조와 확인된 여과지의 구분 — 대상 추적","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":86,"primary":"저수조의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 순서 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":87,"primary":"누수 감시기 관측 공백에서 정수 펌프 범위 제한 — 상태 묶음","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":88,"primary":"후속 입력에 확인된 배수문과 운영 당직표의 부분 경로 — 우선 처리","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":89,"primary":"수압 센서 표본 부족 뒤 방류 기록 연결을 보류하는 장기 관찰 — 연결 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":90,"primary":"보이지 않은 여과지와 확인된 원수 유입구의 구분 — 출처 대조","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":91,"primary":"방류 기록의 일부 기록만으로 염소 주입기를 추정하지 않은 경로 — 범위 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 10개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
