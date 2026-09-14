# A06 v06:92~101 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `F7DE37F9C36E61BD1E1AD67276853D8AE8954D834B74722F2C040A1D9DC58203`
- registry SHA-256: `BEC2AF565F3D268CEF2EAEAF81E5A90351355EFAD83192DE5DAA23245062150C`
- locator는 `stage2_(16)relational_composition_high_density_train_v06.source.psv:92~101`으로 고정한다. source concept/text와 같은 locator registry primary 외 field·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v06_semantic_rewrite_92_101_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 92 | 원수 유입구 관측 공백에서 여과지 범위 제한 — 운영 인계 → 원수 유입 기록 공백의 여과지 운전 보류 | `state,boundary,other` | 유입량 결측과 확인 압력을 구분해 운전을 보류한다. |
| 93 | 다음 교대에 확인된 수질 계측기와 수압 센서의 부분 경로 — 회복 판정 → 수질 계측기와 수압 센서 교대 점검 인계 | `process,other,role` | 교대자가 출처·시점을 확인해 점검을 인계한다. |
| 94 | 운영 당직표 표본 부족 뒤 여과지 연결을 보류하는 경계 직전 — 경로 보존 → 당직표 표본 부족 시 여과지 연결 분류 | `classification,boundary,state` | 확인 압력과 미확인 지시를 구분해 운전 상태를 분류한다. |
| 95 | 보이지 않은 정수 펌프와 확인된 누수 감시기의 구분 — 결과 검증 → 정수 펌프 재검의 누수 감시기 대조 | `state,comparison,other` | 재검 전류와 감시기 압력을 비교해 단정을 멈춘다. |
| 96 | 염소 주입기의 일부 기록만으로 저수조를 추정하지 않은 경로 — 영향 검토 → 염소 주입 부분 기록의 저수조 수위 점검 | `process,boundary,attribute` | 주입량 기록과 수위 변화의 시점을 구분한다. |
| 97 | 응집조 관측 공백에서 여과지 범위 제한 — 예외 점검 → 응집조 수위 공백 시 여과지 단계 확인 | `part_of,state,other` | 전체 정수 과정의 확인 여과 단계만 나타내고 조치를 보류한다. |
| 98 | 교차 확인에 확인된 저수조와 염소 주입기의 부분 경로 — 독립 확인 → 저수조와 염소 주입기 기록 교차 점검 | `state,boundary,other` | 확인 수위·주입량과 후속 결측 구간을 구분한다. |
| 99 | 누수 감시기 표본 부족 뒤 수압 센서 연결을 보류하는 중앙 표본 — 분기 기록 → 누수 감시기 표본 부족의 수압 점검 인계 | `process,other,role` | 교대자가 경보·수압 기록을 구분해 점검을 인계한다. |
| 100 | 보이지 않은 배수문과 확인된 운영 당직표의 구분 — 중간 판정 → 배수문 위치 기록의 당직표 지시 분류 | `classification,boundary,state` | 확인 위치와 누락 지시를 구분해 상태를 분류한다. |
| 101 | 수압 센서의 일부 기록만으로 수질 계측기를 추정하지 않은 경로 — 신호 전달 → 수압 센서 부분 기록의 수질 계측 대조 | `state,comparison,other` | 압력·탁도 추세를 대조하고 출력 조정을 보류한다. |

## 새 text

| line | text |
|---:|---|
| 92 | 원수 유입량 기록이 비어 있고 여과지 압력만 확인될 때, 원수 유입 기록 공백의 여과지 운전 보류에서는 운영자가 확인된 압력과 확인되지 않은 유입량을 구분한다. 중간 관측 결측 때문에 유입량 증가는 보류하여 여과지 압력 급등을 막는다. |
| 93 | 수질 계측기 탁도 기록과 수압 센서 값이 서로 다른 교대에 작성됐을 때, 수질 계측기와 수압 센서 교대 점검 인계는 교대자가 두 기록의 출처와 시점을 확인해 다음 당직자에게 점검을 넘기는 과정이다. 출처 연결 불명 상태에서는 펌프 출력을 바꾸지 않아 압력 변동을 막는다. |
| 94 | 당직표의 여과지 우회 지시 표본이 적고 압력 기록만 남았을 때, 당직표 표본 부족 시 여과지 연결 분류에서는 운영자가 확인된 압력과 확인되지 않은 운전 지시를 구분해 운전 보류 상태로 분류한다. 추가 측정 전에는 우회 운전을 시작하지 않아 처리수 경로를 잘못 바꾸지 않는다. |
| 95 | 정수 펌프 전류를 다시 측정했지만 누수 감시기 압력은 낮게 남아 있을 때, 정수 펌프 재검의 누수 감시기 대조에서는 운영자가 두 기록의 수치를 비교한다. 식별 기록 상충 상태에서는 누수로 단정하지 않아 불필요한 펌프 정지를 막는다. |
| 96 | 염소 주입량은 일부 시각에만 기록되고 저수조 수위는 다른 시각에 변했을 때, 염소 주입 부분 기록의 저수조 수위 점검은 운영자가 두 변화의 시점과 수치를 구분하는 과정이다. 두 기록이 같은 시각에 확인되기 전에는 주입량을 늘리지 않아 저수조 농도 변동을 막는다. |
| 97 | 응집조 수위 기록이 비어 있고 여과지 압력만 남았을 때, 응집조 수위 공백 시 여과지 단계 확인은 전체 정수 과정 중 확인된 여과 단계만 가리키는 보류 상태다. 동시 개입 분리 불가 때문에 응집조 조치의 효과를 확정하지 않고 유입량 증가는 보류하여 압력 급등을 막는다. |
| 98 | 저수조 수위 기록과 염소 주입기 유량 로그 사이의 후속 측정이 없을 때, 저수조와 염소 주입기 기록 교차 점검에서는 운영자가 확인된 두 기록과 확인되지 않은 후속 구간을 구분한다. 후속 검증 누락 때문에 주입량 증가는 보류하여 저수조 농도 변동을 막는다. |
| 99 | 누수 감시기 경보 표본이 적고 수압 센서 값은 다른 교대에 기록됐을 때, 누수 감시기 표본 부족의 수압 점검 인계는 교대자가 확인된 경보와 확인되지 않은 압력 변화를 구분해 다음 당직자에게 현장 점검을 넘기는 과정이다. 예외 승인 시각 미상일 때는 펌프 출력을 바꾸지 않아 압력 변동을 막는다. |
| 100 | 배수문 위치 기록은 남았지만 당직표 지시가 비어 있을 때, 배수문 위치 기록의 당직표 지시 분류에서는 운영자가 확인된 위치와 확인되지 않은 운전 지시를 구분해 운전 보류 상태로 분류한다. 지시가 확인되기 전에는 배수문을 개방 상태로 확정하지 않아 과다 방류를 막는다. |
| 101 | 수압 센서 기록이 일부 시각에만 있고 수질 계측기 탁도값은 다른 채널에 있을 때, 수압 센서 부분 기록의 수질 계측 대조에서는 운영자가 두 추세를 비교한다. 센서 채널 불일치 상태에서는 펌프 출력을 조정하지 않아 불필요한 급수 제한을 막는다. |

## 원복 source 행

```text
원수 유입구 관측 공백에서 여과지 범위 제한 — 운영 인계|state,boundary,other|중간 관측 결측|관측 범위가 제한된 보고서에서 원수 유입구 관측 공백에서 여과지 범위 제한 — 운영 인계는 보이는 단계만 책임 있게 설명한다. 누락된 단계는 추가 확인 항목으로 넘긴다. 중간 관측 결측 항목은 확인된 관계만 확정하게 한다.
다음 교대에 확인된 수질 계측기와 수압 센서의 부분 경로 — 회복 판정|process,other,role|출처 연결 불명|자료가 서로 다른 시점에 모였다면 다음 교대에 확인된 수질 계측기와 수압 센서의 부분 경로 — 회복 판정은 확인 시점이 겹치는 구간만 연결한다. 나머지는 보류 상태로 남긴다. 출처 연결 불명 항목은 확인된 관계만 확정하게 한다.
운영 당직표 표본 부족 뒤 여과지 연결을 보류하는 경계 직전 — 경로 보존|classification,boundary,state||센서 기록이 끊긴 지점 뒤에는 운영 당직표 표본 부족 뒤 여과지 연결을 보류하는 경계 직전 — 경로 보존은 가능한 범위를 좁혀 둔다. 추가 측정 전에는 경로를 확정하지 않는다.
보이지 않은 정수 펌프와 확인된 누수 감시기의 구분 — 결과 검증|state,comparison,other|식별 기록 상충|확인된 표본이 적을수록 보이지 않은 정수 펌프와 확인된 누수 감시기의 구분 — 결과 검증은 연결의 방향과 범위를 보수적으로 적는다. 결측을 정상 상태로 간주하지 않는다. 식별 기록 상충 항목은 확인된 관계만 확정하게 한다.
염소 주입기의 일부 기록만으로 저수조를 추정하지 않은 경로 — 영향 검토|process,boundary,attribute||한 채널의 응답만으로 염소 주입기의 일부 기록만으로 저수조를 추정하지 않은 경로 — 영향 검토는 전체 연결을 판정하지 않는다. 다른 채널이 채워질 때까지 가능한 경로를 열어 둔다.
응집조 관측 공백에서 여과지 범위 제한 — 예외 점검|part_of,state,other|동시 개입 분리 불가|현장에 남은 자료는 응집조 관측 공백에서 여과지 범위 제한 — 예외 점검은 전체 경로 중 일부만 보여 준다. 보이지 않은 단계를 사실처럼 서술하지 않는다. 동시 개입 분리 불가 항목은 확인된 관계만 확정하게 한다.
교차 확인에 확인된 저수조와 염소 주입기의 부분 경로 — 독립 확인|state,boundary,other|후속 검증 누락|관측표에 보이는 구간만으로 교차 확인에 확인된 저수조와 염소 주입기의 부분 경로 — 독립 확인은 확인된 관계를 적는다. 빈 구간을 임의의 연결로 채우지 않는다. 후속 검증 누락 항목은 확인된 관계만 확정하게 한다.
누수 감시기 표본 부족 뒤 수압 센서 연결을 보류하는 중앙 표본 — 분기 기록|process,other,role|예외 승인 시각 미상|부분 로그를 읽을 때 누수 감시기 표본 부족 뒤 수압 센서 연결을 보류하는 중앙 표본 — 분기 기록은 기록된 사실과 기록되지 않은 가능성을 구분한다. 가능성은 확정 문장으로 바꾸지 않는다. 예외 승인 시각 미상 항목은 확인된 관계만 확정하게 한다.
보이지 않은 배수문과 확인된 운영 당직표의 구분 — 중간 판정|classification,boundary,state||검토표에서 보이지 않은 배수문과 확인된 운영 당직표의 구분 — 중간 판정은 관측 빈칸과 확인값을 나눠 표시한다. 마지막 결과만으로 중간 관계를 복원하지 않는다.
수압 센서의 일부 기록만으로 수질 계측기를 추정하지 않은 경로 — 신호 전달|state,comparison,other|센서 채널 불일치|일부 표본만 남은 상황에서 수압 센서의 일부 기록만으로 수질 계측기를 추정하지 않은 경로 — 신호 전달은 관측된 단계와 추정된 단계를 분리한다. 미확인된 노드는 결론에 넣지 않는다. 센서 채널 불일치 항목은 확인된 관계만 확정하게 한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":92,"primary":"원수 유입구 관측 공백에서 여과지 범위 제한 — 운영 인계","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":93,"primary":"다음 교대에 확인된 수질 계측기와 수압 센서의 부분 경로 — 회복 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":94,"primary":"운영 당직표 표본 부족 뒤 여과지 연결을 보류하는 경계 직전 — 경로 보존","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":95,"primary":"보이지 않은 정수 펌프와 확인된 누수 감시기의 구분 — 결과 검증","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":96,"primary":"염소 주입기의 일부 기록만으로 저수조를 추정하지 않은 경로 — 영향 검토","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":97,"primary":"응집조 관측 공백에서 여과지 범위 제한 — 예외 점검","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":98,"primary":"교차 확인에 확인된 저수조와 염소 주입기의 부분 경로 — 독립 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":99,"primary":"누수 감시기 표본 부족 뒤 수압 센서 연결을 보류하는 중앙 표본 — 분기 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":100,"primary":"보이지 않은 배수문과 확인된 운영 당직표의 구분 — 중간 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":101,"primary":"수압 센서의 일부 기록만으로 수질 계측기를 추정하지 않은 경로 — 신호 전달","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 10개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
