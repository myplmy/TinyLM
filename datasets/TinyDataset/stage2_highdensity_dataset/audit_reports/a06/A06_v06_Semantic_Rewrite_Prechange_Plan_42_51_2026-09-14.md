# A06 v06:42~51 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `03AC2DD55FBDDE4A27DF14AF510112250803B838D2BA2803998E1691AD465E99`
- registry SHA-256: `C91EAB08CDE2406669F4CF9F00310241BF825FB539693D01B33A78B7A9FB2AA4`
- locator는 `stage2_(16)relational_composition_high_density_train_v06.source.psv:42~51`으로 고정한다. source concept/text와 같은 locator registry primary 외 field·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v06_semantic_rewrite_42_51_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 42 | 여과지 관측 공백에서 원수 유입구 범위 제한 — 회복 판정 → 여과지 기록 공백의 원수 유입 점검 | `process,boundary,attribute` | 유입량과 누락된 압력 변화를 구분하고 증량을 멈춘다. |
| 43 | 보류 해제에 확인된 방류 기록과 염소 주입기의 부분 경로 — 경로 보존 → 방류 기록의 염소 주입 연결 보류 | `part_of,state,other` | 전체 정수 과정의 방류 단계와 빈 주입 단계를 나누어 보류한다. |
| 44 | 원수 유입구 표본 부족 뒤 배수문 연결을 보류하는 우회 승인 — 결과 검증 → 원수 유입 표본 부족 시 배수문 연결 보류 | `state,boundary,other` | 확인된 유입 변화와 미확인 배수문 이동을 구분해 우회를 보류한다. |
| 45 | 보이지 않은 수질 계측기와 확인된 수압 센서의 구분 — 영향 검토 → 수질 계측기 공백의 수압 기록 인계 | `process,other,role` | 교대자가 수압 기록의 출처를 확인해 수질 측정을 인계한다. |
| 46 | 운영 당직표의 일부 기록만으로 배수문을 추정하지 않은 경로 — 예외 점검 → 당직표 부분 기록의 배수문 상태 분류 | `classification,boundary,state` | 조작 기록과 미확인 위치 변화를 구분하여 보류로 분류한다. |
| 47 | 정수 펌프 관측 공백에서 누수 감시기 범위 제한 — 독립 확인 → 정수 펌프 공백의 누수 감시기 비교 | `state,comparison,other` | 이전·현재 압력값을 비교하고 고장 단정을 막는다. |
| 48 | 긴급 확인에 확인된 염소 주입기와 저수조의 부분 경로 — 분기 기록 → 염소 주입기와 저수조 긴급 확인 | `process,boundary,attribute` | 주입량·수위 변화의 시점을 구분해 조치 기준을 확인한다. |
| 49 | 응집조 표본 부족 뒤 누수 감시기 연결을 보류하는 장기 관찰 — 중간 판정 → 응집조 표본 부족 시 누수 경보 연결 보류 | `part_of,state,other` | 전체 과정 중 확인된 응집조 변화와 미확인 누수 원인을 나눈다. |
| 50 | 보이지 않은 저수조와 확인된 염소 주입기의 구분 — 신호 전달 → 저수조 기록 공백의 염소 주입 확인 | `state,boundary,other` | 주입량과 미확인 수위 변화를 구분해 증량을 보류한다. |
| 51 | 누수 감시기의 일부 기록만으로 정수 펌프를 추정하지 않은 경로 — 대상 추적 → 누수 감시기 부분 기록의 펌프 점검 인계 | `process,other,role` | 교대자가 경보·펌프 상태를 구분하고 점검을 인계한다. |

## 새 text

| line | text |
|---:|---|
| 42 | 여과지 압력 기록이 비어 있고 원수 유입량만 확인될 때, 여과지 기록 공백의 원수 유입 점검은 운영자가 확인된 유입량과 확인되지 않은 여과지 압력 변화를 구분하는 과정이다. 압력값이 들어오기 전에는 유입량을 늘리지 않아 여과지 막힘 위험을 낮춘다. |
| 43 | 방류량 기록은 있지만 다음 단계 염소 주입량이 입력되지 않았을 때, 방류 기록의 염소 주입 연결 보류는 전체 정수 과정 중 확인된 방류 단계와 비어 있는 주입 단계를 나누는 보류 상태다. 다음 단계 입력 결측 때문에 주입량을 정상으로 확정하지 않아 근거 없는 농도 조정을 막는다. |
| 44 | 원수 유입량 표본이 적고 배수문 위치 기록도 중간에 비어 있을 때, 원수 유입 표본 부족 시 배수문 연결 보류에서는 운영자가 확인된 유입 변화와 확인되지 않은 배수문 이동을 구분한다. 중간 관측 결측 때문에 우회 운전 승인은 보류하여 과다 방류를 막는다. |
| 45 | 수질 계측기 값은 없고 수압 센서 기록만 남았을 때, 수질 계측기 공백의 수압 기록 인계는 교대자가 수압 변화의 출처를 확인해 다음 당직자에게 수질 측정을 요청하는 과정이다. 출처 연결 불명 상태에서는 펌프 출력을 바꾸지 않아 압력 변동을 막는다. |
| 46 | 당직표에는 일부 배수문 조작만 기록되고 위치 값이 없을 때, 당직표 부분 기록의 배수문 상태 분류에서는 운영자가 확인된 조작 기록과 확인되지 않은 위치 변화를 구분해 보류로 분류한다. 위치가 확인되기 전에는 배수문을 개방 상태로 확정하지 않아 과다 방류를 막는다. |
| 47 | 정수 펌프 운전 기록이 없는데 누수 감시기 압력은 낮을 때, 정수 펌프 공백의 누수 감시기 비교에서는 운영자가 이전 교대의 압력값과 현재 감시기 값을 비교한다. 식별 기록 상충 상태에서는 펌프 고장으로 단정하지 않아 불필요한 급수 중단을 막는다. |
| 48 | 염소 주입기 유량이 갑자기 바뀌고 저수조 수위도 떨어질 때, 염소 주입기와 저수조 긴급 확인은 운영자가 주입량 변화와 수위 변화의 시점을 구분해 원인을 확인하는 과정이다. 수위가 더 낮아지면 주입량을 줄여 저수조의 염소 농도 상승을 막는다. |
| 49 | 응집조 수위 표본이 적고 누수 감시기 경보도 같은 시각에 여러 설비에서 울릴 때, 응집조 표본 부족 시 누수 경보 연결 보류는 전체 정수 과정 중 확인된 응집조 변화와 확인되지 않은 누수 원인을 나누는 보류 상태다. 동시 개입 분리 불가 때문에 펌프 출력을 바로 낮추지 않아 급수 압력 급락을 막는다. |
| 50 | 저수조 수위 기록은 비어 있고 염소 주입량만 확인될 때, 저수조 기록 공백의 염소 주입 확인에서는 운영자가 확인된 주입량과 확인되지 않은 수위 변화를 구분한다. 후속 검증 누락 때문에 주입량을 늘리지 않아 저수조 농도 변동을 막는다. |
| 51 | 누수 감시기 경보가 일부 시각에만 있고 정수 펌프 운전 기록도 끊겼을 때, 누수 감시기 부분 기록의 펌프 점검 인계는 교대자가 확인된 경보와 확인되지 않은 펌프 상태를 구분해 다음 당직자에게 현장 점검을 넘기는 과정이다. 예외 승인 시각 미상이라서 승인 전에는 펌프 출력을 바꾸지 않아 압력 변동을 막는다. |

## 원복 source 행

```text
여과지 관측 공백에서 원수 유입구 범위 제한 — 회복 판정|process,boundary,attribute||관측 범위가 제한된 보고서에서 여과지 관측 공백에서 원수 유입구 범위 제한 — 회복 판정은 보이는 단계만 책임 있게 설명한다. 누락된 단계는 추가 확인 항목으로 넘긴다.
보류 해제에 확인된 방류 기록과 염소 주입기의 부분 경로 — 경로 보존|part_of,state,other|다음 단계 입력 결측|자료가 서로 다른 시점에 모였다면 보류 해제에 확인된 방류 기록과 염소 주입기의 부분 경로 — 경로 보존은 확인 시점이 겹치는 구간만 연결한다. 나머지는 보류 상태로 남긴다. 다음 단계 입력 결측 항목은 확인된 관계만 확정하게 한다.
원수 유입구 표본 부족 뒤 배수문 연결을 보류하는 우회 승인 — 결과 검증|state,boundary,other|중간 관측 결측|센서 기록이 끊긴 지점 뒤에는 원수 유입구 표본 부족 뒤 배수문 연결을 보류하는 우회 승인 — 결과 검증은 가능한 범위를 좁혀 둔다. 추가 측정 전에는 경로를 확정하지 않는다. 중간 관측 결측 항목은 확인된 관계만 확정하게 한다.
보이지 않은 수질 계측기와 확인된 수압 센서의 구분 — 영향 검토|process,other,role|출처 연결 불명|확인된 표본이 적을수록 보이지 않은 수질 계측기와 확인된 수압 센서의 구분 — 영향 검토는 연결의 방향과 범위를 보수적으로 적는다. 결측을 정상 상태로 간주하지 않는다. 출처 연결 불명 항목은 확인된 관계만 확정하게 한다.
운영 당직표의 일부 기록만으로 배수문을 추정하지 않은 경로 — 예외 점검|classification,boundary,state||한 채널의 응답만으로 운영 당직표의 일부 기록만으로 배수문을 추정하지 않은 경로 — 예외 점검은 전체 연결을 판정하지 않는다. 다른 채널이 채워질 때까지 가능한 경로를 열어 둔다.
정수 펌프 관측 공백에서 누수 감시기 범위 제한 — 독립 확인|state,comparison,other|식별 기록 상충|현장에 남은 자료는 정수 펌프 관측 공백에서 누수 감시기 범위 제한 — 독립 확인은 전체 경로 중 일부만 보여 준다. 보이지 않은 단계를 사실처럼 서술하지 않는다. 식별 기록 상충 항목은 확인된 관계만 확정하게 한다.
긴급 확인에 확인된 염소 주입기와 저수조의 부분 경로 — 분기 기록|process,boundary,attribute||관측표에 보이는 구간만으로 긴급 확인에 확인된 염소 주입기와 저수조의 부분 경로 — 분기 기록은 확인된 관계를 적는다. 빈 구간을 임의의 연결로 채우지 않는다.
응집조 표본 부족 뒤 누수 감시기 연결을 보류하는 장기 관찰 — 중간 판정|part_of,state,other|동시 개입 분리 불가|부분 로그를 읽을 때 응집조 표본 부족 뒤 누수 감시기 연결을 보류하는 장기 관찰 — 중간 판정은 기록된 사실과 기록되지 않은 가능성을 구분한다. 가능성은 확정 문장으로 바꾸지 않는다. 동시 개입 분리 불가 항목은 확인된 관계만 확정하게 한다.
보이지 않은 저수조와 확인된 염소 주입기의 구분 — 신호 전달|state,boundary,other|후속 검증 누락|검토표에서 보이지 않은 저수조와 확인된 염소 주입기의 구분 — 신호 전달은 관측 빈칸과 확인값을 나눠 표시한다. 마지막 결과만으로 중간 관계를 복원하지 않는다. 후속 검증 누락 항목은 확인된 관계만 확정하게 한다.
누수 감시기의 일부 기록만으로 정수 펌프를 추정하지 않은 경로 — 대상 추적|process,other,role|예외 승인 시각 미상|일부 표본만 남은 상황에서 누수 감시기의 일부 기록만으로 정수 펌프를 추정하지 않은 경로 — 대상 추적은 관측된 단계와 추정된 단계를 분리한다. 미확인된 노드는 결론에 넣지 않는다. 예외 승인 시각 미상 항목은 확인된 관계만 확정하게 한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":42,"primary":"여과지 관측 공백에서 원수 유입구 범위 제한 — 회복 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":43,"primary":"보류 해제에 확인된 방류 기록과 염소 주입기의 부분 경로 — 경로 보존","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":44,"primary":"원수 유입구 표본 부족 뒤 배수문 연결을 보류하는 우회 승인 — 결과 검증","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":45,"primary":"보이지 않은 수질 계측기와 확인된 수압 센서의 구분 — 영향 검토","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":46,"primary":"운영 당직표의 일부 기록만으로 배수문을 추정하지 않은 경로 — 예외 점검","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":47,"primary":"정수 펌프 관측 공백에서 누수 감시기 범위 제한 — 독립 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":48,"primary":"긴급 확인에 확인된 염소 주입기와 저수조의 부분 경로 — 분기 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":49,"primary":"응집조 표본 부족 뒤 누수 감시기 연결을 보류하는 장기 관찰 — 중간 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":50,"primary":"보이지 않은 저수조와 확인된 염소 주입기의 구분 — 신호 전달","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":51,"primary":"누수 감시기의 일부 기록만으로 정수 펌프를 추정하지 않은 경로 — 대상 추적","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 10개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
