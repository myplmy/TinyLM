# A06 v06:32~41 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `77E316233D81B81587DDB753AF306213D59F28ECBC5FD7391007A438F4C2C9DF`
- registry SHA-256: `02342D33A8EB77CBF09425F97CA35391FCE930BCEE51FC2FFB5B6424825B7D38`
- locator는 `stage2_(16)relational_composition_high_density_train_v06.source.psv:32~41`으로 고정한다. source의 concept/text와 같은 locator의 registry primary 외 필드·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v06_semantic_rewrite_32_41_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 32 | 원수 유입구 관측 공백에서 여과지 범위 제한 — 중간 판정 → 원수 유입 기록 공백 시 여과지 점검 | `state,boundary,other` | 유입·압력 기록 사이의 수위 결측 때문에 증량을 보류하는 판단을 명시한다. |
| 33 | 다음 교대에 확인된 수질 계측기와 수압 센서의 부분 경로 — 신호 전달 → 수질 계측기와 수압 센서 기록 인계 | `process,other,role` | 교대자·출처·시점 확인 뒤 점검을 인계하는 과정을 명시한다. |
| 34 | 운영 당직표 표본 부족 뒤 여과지 연결을 보류하는 저부하 운전 — 대상 추적 → 저부하 여과지 연결 보류 상태 | `classification,boundary,state` | 확인된 압력 기록과 미확인 우회 지시를 구분·분류하고 보류한다. |
| 35 | 보이지 않은 정수 펌프와 확인된 누수 감시기의 구분 — 순서 기록 → 정수 펌프와 누수 감시기 기록 대조 | `state,comparison,other` | 전류·압력 수치를 비교하고 상충 상태에서 누수 단정을 멈춘다. |
| 36 | 염소 주입기의 일부 기록만으로 저수조를 추정하지 않은 경로 — 상태 묶음 → 염소 주입 기록 부족 시 저수조 확인 | `process,boundary,attribute` | 서로 다른 측정 시각과 실제 수위 변화를 구분하는 과정을 쓴다. |
| 37 | 응집조 관측 공백에서 여과지 범위 제한 — 우선 처리 → 응집조 관측 공백의 여과지 범위 | `part_of,state,other` | 전체 정수 과정 중 확인된 여과 단계를 한정하고 조치를 보류한다. |
| 38 | 교차 확인에 확인된 저수조와 염소 주입기의 부분 경로 — 연결 확인 → 저수조와 염소 주입 기록 연결 보류 | `state,boundary,other` | 확인된 두 기록과 미확인 후속 구간을 구분해 주입 증가를 보류한다. |
| 39 | 누수 감시기 표본 부족 뒤 수압 센서 연결을 보류하는 경보 누적 — 출처 대조 → 누수 감시기 표본 부족 시 수압 점검 인계 | `process,other,role` | 교대자가 경보·압력 변화의 확인 범위를 구분하여 현장 점검을 인계한다. |
| 40 | 보이지 않은 배수문과 확인된 운영 당직표의 구분 — 범위 확인 → 당직표 기록의 배수문 상태 분류 | `classification,boundary,state` | 확인된 운전 지시와 미확인 배수문 상태를 구분하여 보류로 분류한다. |
| 41 | 수압 센서의 일부 기록만으로 수질 계측기를 추정하지 않은 경로 — 운영 인계 → 수압 센서 표본과 수질 계측값 비교 | `state,comparison,other` | 다른 채널의 수압·수질 값을 비교하고 출력 조정을 보류한다. |

## 새 text

| line | text |
|---:|---|
| 32 | 원수 유입량 기록과 여과지 압력 기록 사이의 수위 자료가 없을 때, 원수 유입 기록 공백 시 여과지 점검에서는 운영자가 확인된 두 기록과 확인되지 않은 중간 구간을 구분한다. 중간 관측 결측 때문에 유입량 증가는 보류하여 여과지 압력 급등을 막는다. |
| 33 | 수질 계측기 탁도 기록과 수압 센서 값의 작성 시점이 서로 다른 교대에 걸칠 때, 수질 계측기와 수압 센서 기록 인계는 교대자가 두 기록의 출처와 시점을 확인해 다음 당직자에게 점검을 넘기는 과정이다. 출처 연결 불명 상태에서는 펌프 출력을 바꾸지 않아 급수 압력 변동을 막는다. |
| 34 | 저부하 운전 중 당직표에 여과지 우회 지시가 없고 압력 표본도 적을 때, 저부하 여과지 연결 보류 상태에서는 운영자가 확인된 압력 기록과 확인되지 않은 운전 지시를 구분해 분류한다. 추가 측정 전에는 우회 운전을 시작하지 않아 처리수 경로를 잘못 바꾸지 않는다. |
| 35 | 정수 펌프 전류값은 정상인데 누수 감시기 압력 기록은 낮을 때, 정수 펌프와 누수 감시기 기록 대조에서는 운영자가 두 기록의 수치를 비교한다. 식별 기록 상충 상태에서는 현장 점검 전까지 누수로 단정하지 않아 불필요한 펌프 정지를 막는다. |
| 36 | 염소 주입량 기록은 한 차례뿐이고 저수조 수위는 다른 시각에 측정됐을 때, 염소 주입 기록 부족 시 저수조 확인은 운영자가 측정 시각 차이와 실제 수위 변화를 구분하는 과정이다. 두 수치가 같은 시각에 확인될 때까지 주입량을 늘리지 않아 저수조 염소 농도 변동을 막는다. |
| 37 | 응집조 수위 기록이 비어 있고 여과지 압력만 남았을 때, 응집조 관측 공백의 여과지 범위는 전체 정수 과정 중 확인된 여과 단계만 가리킨다. 동시 개입 분리 불가 상태이므로 당직자는 응집조 조치의 효과를 확정하지 않고 유입량 증가는 보류하여 여과지 압력 급등을 막는다. |
| 38 | 저수조 수위 기록과 염소 주입기 로그 사이의 후속 측정이 없을 때, 저수조와 염소 주입 기록 연결 보류에서는 운영자가 확인된 두 기록과 확인되지 않은 후속 구간을 구분한다. 후속 검증 누락 때문에 주입량 증가는 보류하여 저수조 농도 변동을 막는다. |
| 39 | 누수 감시기 경보 표본이 적고 수압 센서 값이 다른 교대에 기록됐을 때, 누수 감시기 표본 부족 시 수압 점검 인계는 교대자가 확인된 경보와 확인되지 않은 압력 변화를 구분해 다음 당직자에게 현장 점검을 넘기는 과정이다. 예외 승인 시각 미상이라서 승인 전에는 펌프 출력을 바꾸지 않아 압력 변동을 막는다. |
| 40 | 당직표에는 배수문 지시가 있지만 위치 기록이 없을 때, 당직표 기록의 배수문 상태 분류에서는 운영자가 확인된 운전 지시와 확인되지 않은 배수문 상태를 구분해 보류로 분류한다. 위치 값이 확인되기 전에는 배수문을 정상 운전으로 확정하지 않아 과다 방류를 막는다. |
| 41 | 수압 센서 표본은 남았지만 수질 계측기 기록이 다른 채널에만 있을 때, 수압 센서 표본과 수질 계측값 비교에서는 운영자가 두 기록의 수치를 비교한다. 센서 채널 불일치 상태에서는 수질 측정이 일치할 때까지 펌프 출력을 조정하지 않아 불필요한 급수 제한을 막는다. |

## 원복 source 행

```text
원수 유입구 관측 공백에서 여과지 범위 제한 — 중간 판정|state,boundary,other|중간 관측 결측|관측 범위가 제한된 보고서에서 원수 유입구 관측 공백에서 여과지 범위 제한 — 중간 판정은 보이는 단계만 책임 있게 설명한다. 누락된 단계는 추가 확인 항목으로 넘긴다. 중간 관측 결측 항목은 확인된 관계만 확정하게 한다.
다음 교대에 확인된 수질 계측기와 수압 센서의 부분 경로 — 신호 전달|process,other,role|출처 연결 불명|자료가 서로 다른 시점에 모였다면 다음 교대에 확인된 수질 계측기와 수압 센서의 부분 경로 — 신호 전달은 확인 시점이 겹치는 구간만 연결한다. 나머지는 보류 상태로 남긴다. 출처 연결 불명 항목은 확인된 관계만 확정하게 한다.
운영 당직표 표본 부족 뒤 여과지 연결을 보류하는 저부하 운전 — 대상 추적|classification,boundary,state||센서 기록이 끊긴 지점 뒤에는 운영 당직표 표본 부족 뒤 여과지 연결을 보류하는 저부하 운전 — 대상 추적은 가능한 범위를 좁혀 둔다. 추가 측정 전에는 경로를 확정하지 않는다.
보이지 않은 정수 펌프와 확인된 누수 감시기의 구분 — 순서 기록|state,comparison,other|식별 기록 상충|확인된 표본이 적을수록 보이지 않은 정수 펌프와 확인된 누수 감시기의 구분 — 순서 기록은 연결의 방향과 범위를 보수적으로 적는다. 결측을 정상 상태로 간주하지 않는다. 식별 기록 상충 항목은 확인된 관계만 확정하게 한다.
염소 주입기의 일부 기록만으로 저수조를 추정하지 않은 경로 — 상태 묶음|process,boundary,attribute||한 채널의 응답만으로 염소 주입기의 일부 기록만으로 저수조를 추정하지 않은 경로 — 상태 묶음은 전체 연결을 판정하지 않는다. 다른 채널이 채워질 때까지 가능한 경로를 열어 둔다.
응집조 관측 공백에서 여과지 범위 제한 — 우선 처리|part_of,state,other|동시 개입 분리 불가|현장에 남은 자료는 응집조 관측 공백에서 여과지 범위 제한 — 우선 처리는 전체 경로 중 일부만 보여 준다. 보이지 않은 단계를 사실처럼 서술하지 않는다. 동시 개입 분리 불가 항목은 확인된 관계만 확정하게 한다.
교차 확인에 확인된 저수조와 염소 주입기의 부분 경로 — 연결 확인|state,boundary,other|후속 검증 누락|관측표에 보이는 구간만으로 교차 확인에 확인된 저수조와 염소 주입기의 부분 경로 — 연결 확인은 확인된 관계를 적는다. 빈 구간을 임의의 연결로 채우지 않는다. 후속 검증 누락 항목은 확인된 관계만 확정하게 한다.
누수 감시기 표본 부족 뒤 수압 센서 연결을 보류하는 경보 누적 — 출처 대조|process,other,role|예외 승인 시각 미상|부분 로그를 읽을 때 누수 감시기 표본 부족 뒤 수압 센서 연결을 보류하는 경보 누적 — 출처 대조는 기록된 사실과 기록되지 않은 가능성을 구분한다. 가능성은 확정 문장으로 바꾸지 않는다. 예외 승인 시각 미상 항목은 확인된 관계만 확정하게 한다.
보이지 않은 배수문과 확인된 운영 당직표의 구분 — 범위 확인|classification,boundary,state||검토표에서 보이지 않은 배수문과 확인된 운영 당직표의 구분 — 범위 확인은 관측 빈칸과 확인값을 나눠 표시한다. 마지막 결과만으로 중간 관계를 복원하지 않는다.
수압 센서의 일부 기록만으로 수질 계측기를 추정하지 않은 경로 — 운영 인계|state,comparison,other|센서 채널 불일치|일부 표본만 남은 상황에서 수압 센서의 일부 기록만으로 수질 계측기를 추정하지 않은 경로 — 운영 인계는 관측된 단계와 추정된 단계를 분리한다. 미확인된 노드는 결론에 넣지 않는다. 센서 채널 불일치 항목은 확인된 관계만 확정하게 한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":32,"primary":"원수 유입구 관측 공백에서 여과지 범위 제한 — 중간 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":33,"primary":"다음 교대에 확인된 수질 계측기와 수압 센서의 부분 경로 — 신호 전달","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":34,"primary":"운영 당직표 표본 부족 뒤 여과지 연결을 보류하는 저부하 운전 — 대상 추적","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":35,"primary":"보이지 않은 정수 펌프와 확인된 누수 감시기의 구분 — 순서 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":36,"primary":"염소 주입기의 일부 기록만으로 저수조를 추정하지 않은 경로 — 상태 묶음","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":37,"primary":"응집조 관측 공백에서 여과지 범위 제한 — 우선 처리","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":38,"primary":"교차 확인에 확인된 저수조와 염소 주입기의 부분 경로 — 연결 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":39,"primary":"누수 감시기 표본 부족 뒤 수압 센서 연결을 보류하는 경보 누적 — 출처 대조","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":40,"primary":"보이지 않은 배수문과 확인된 운영 당직표의 구분 — 범위 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":41,"primary":"수압 센서의 일부 기록만으로 수질 계측기를 추정하지 않은 경로 — 운영 인계","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 10개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
