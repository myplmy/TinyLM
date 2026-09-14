# A06 v06:112~121 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `2F919323E17C1F3A0A3F34461B29BD61D0C5C4CA193AEFF0A5D4941039C685A3`
- registry SHA-256: `D778756C12B1A62A7581904484A3F54525234DC56C4937F0D4CE255793F38BD7`
- locator는 `stage2_(16)relational_composition_high_density_train_v06.source.psv:112~121`으로 고정한다. source concept/text와 같은 locator registry primary 외 field·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v06_semantic_rewrite_112_121_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 112 | 배수문 관측 공백에서 운영 당직표 범위 제한 — 결과 검증 → 배수문 위치 공백 시 당직표 운전 분류 | `classification,boundary,state` | 조작 시각과 미확인 위치를 구분해 운전 보류로 분류한다. |
| 113 | 현장 재검에 확인된 수압 센서와 수질 계측기의 부분 경로 — 영향 검토 → 수압·수질 센서값 불일치 검토 | `state,comparison,other` | 수압·수질 센서의 시각과 위치를 비교해 고장 상태 단정을 보류한다. |
| 114 | 여과지 표본 부족 뒤 저수조 연결을 보류하는 저부하 운전 — 예외 점검 → 여과지 표본 부족 시 저수조 저부하 운전 | `process,boundary,attribute` | 확인된 탁도와 미확인 여과 상태를 나누어 유량을 낮춘다. |
| 115 | 보이지 않은 방류 기록과 확인된 염소 주입기의 구분 — 독립 확인 → 방류량 미기록 시 염소 주입 보류 | `part_of,state,other` | 처리 과정의 확인 주입 단계와 비어 있는 방류 단계를 구분한다. |
| 116 | 원수 유입구의 일부 기록만으로 여과지를 추정하지 않은 경로 — 분기 기록 → 원수 유입 기록 공백 시 여과지 운전 보류 | `state,boundary,other` | 확인 유입 변화와 미확인 여과 상태를 구분해 우회 운전을 보류한다. |
| 117 | 수질 계측기 관측 공백에서 수압 센서 범위 제한 — 중간 판정 → 수질 계측값 누락 시 수압 기록 인계 | `process,other,role` | 교대자가 수압 변화의 출처를 확인해 현장 수질 점검을 인계한다. |
| 118 | 후속 입력에 확인된 운영 당직표와 배수문의 부분 경로 — 신호 전달 → 배수문 조작 시각 기록의 운전 보류 분류 | `classification,boundary,state` | 조작 시간과 미확인 개방 정도를 구분해 정상 운전 분류를 보류한다. |
| 119 | 정수 펌프 표본 부족 뒤 응집조 연결을 보류하는 경보 누적 — 대상 추적 → 펌프 전류·응집조 수위 기록 상충 검토 | `state,comparison,other` | 두 측정의 시각·위치를 비교해 과부하 상태 단정을 막는다. |
| 120 | 보이지 않은 염소 주입기와 확인된 저수조의 구분 — 순서 기록 → 저수조 수위 누락 시 염소 주입 순서 확인 | `process,boundary,attribute` | 주입량과 미확인 수위 변화를 구분해 증량을 보류한다. |
| 121 | 응집조의 일부 기록만으로 여과지를 추정하지 않은 경로 — 상태 묶음 → 응집조·여과지 동시 경보의 운전 보류 | `part_of,state,other` | 두 경보 원인을 분리할 수 없을 때 전체 과정의 운전 변경을 보류한다. |

## 새 text

| line | text |
|---:|---|
| 112 | 배수문 위치 기록이 비어 있고 당직표에는 조작 시각만 남았을 때, 배수문 위치 공백 시 당직표 운전 분류는 운영자가 확인된 조작과 확인되지 않은 위치 변화를 구분해 운전 보류 상태로 분류하는 일이다. 위치가 확인되기 전에는 배수문을 개방 상태로 확정하지 않아 과다 방류를 막는다. |
| 113 | 수압 센서는 급수관 압력 저하를, 수질 계측기는 정상 수질을 같은 시각에 보낼 때, 수압·수질 센서값 불일치 검토에서 운영자는 두 센서의 기록 시각과 측정 위치를 비교한다. 센서 채널 불일치가 해소되기 전에는 펌프 고장 상태로 확정하지 않아 불필요한 급수 중단을 막는다. |
| 114 | 여과지 탁도 표본이 적고 저수조 수위가 낮을 때, 여과지 표본 부족 시 저수조 저부하 운전은 운영자가 확인된 탁도 변화와 확인되지 않은 여과 상태를 구분해 펌프 유량을 낮추는 과정이다. 추가 표본이 나오기 전에는 유량을 정상 수준으로 올리지 않아 저수조 수위 급락을 막는다. |
| 115 | 방류량은 기록되지 않았는데 염소 주입량만 남았을 때, 방류량 미기록 시 염소 주입 보류는 정수 처리 과정 중 확인된 주입 단계와 비어 있는 방류 단계를 나누는 보류 상태다. 다음 단계 입력 결측 때문에 주입량을 정상으로 확정하지 않아 과다 투입을 막는다. |
| 116 | 원수 유입량은 초반 기록만 있고 여과지 압력 기록이 중간에 끊겼을 때, 원수 유입 기록 공백 시 여과지 운전 보류에서는 운영자가 확인된 유입 변화와 확인되지 않은 여과 상태를 구분한다. 중간 관측 결측 때문에 우회 운전을 시작하지 않아 여과지 압력 급락을 막는다. |
| 117 | 수질 계측값은 없고 수압 센서 기록만 남았을 때, 수질 계측값 누락 시 수압 기록 인계는 교대자가 수압 변화의 출처를 확인해 다음 당직자에게 현장 수질 점검을 넘기는 과정이다. 출처 연결 불명 상태에서는 펌프 출력 변경을 보류해 압력 변동을 막는다. |
| 118 | 당직표에는 배수문 조작 시각만 있고 개방 정도가 없을 때, 배수문 조작 시각 기록의 운전 보류 분류에서 운영자는 확인된 조작 시간과 확인되지 않은 개방 정도를 구분한다. 개방 정도가 확인되기 전에는 배수문을 정상 운전으로 분류하지 않아 과다 방류를 막는다. |
| 119 | 정수 펌프 전류는 증가했는데 응집조 수위 기록은 변하지 않을 때, 펌프 전류·응집조 수위 기록 상충 검토에서는 운영자가 두 값의 기록 시각과 측정 위치를 비교한다. 식별 기록 상충이 해소되기 전에는 펌프 과부하 상태로 확정하지 않아 불필요한 운전 중단을 막는다. |
| 120 | 저수조 수위 기록은 비어 있는데 염소 주입 시각과 주입량만 남았을 때, 저수조 수위 누락 시 염소 주입 순서 확인은 운영자가 확인된 주입량과 확인되지 않은 수위 변화를 구분하는 과정이다. 수위가 확인될 때까지 주입량을 늘리지 않아 저수조 농도 상승을 막는다. |
| 121 | 응집조 수위 저하와 여과지 압력 저하가 같은 시각에 나타나지만 어느 설비가 먼저 변했는지 알 수 없을 때, 응집조·여과지 동시 경보의 운전 보류는 전체 정수 과정 중 두 경보의 원인을 나누지 못한 보류 상태다. 동시 개입 분리 불가 때문에 펌프 출력을 바로 낮추지 않아 급수 압력 급락을 막는다. |

## 원복 source 행

```text
배수문 관측 공백에서 운영 당직표 범위 제한 — 결과 검증|classification,boundary,state||관측 범위가 제한된 보고서에서 배수문 관측 공백에서 운영 당직표 범위 제한 — 결과 검증은 보이는 단계만 책임 있게 설명한다. 누락된 단계는 추가 확인 항목으로 넘긴다.
현장 재검에 확인된 수압 센서와 수질 계측기의 부분 경로 — 영향 검토|state,comparison,other|센서 채널 불일치|자료가 서로 다른 시점에 모였다면 현장 재검에 확인된 수압 센서와 수질 계측기의 부분 경로 — 영향 검토는 확인 시점이 겹치는 구간만 연결한다. 나머지는 보류 상태로 남긴다. 센서 채널 불일치 항목은 확인된 관계만 확정하게 한다.
여과지 표본 부족 뒤 저수조 연결을 보류하는 저부하 운전 — 예외 점검|process,boundary,attribute||센서 기록이 끊긴 지점 뒤에는 여과지 표본 부족 뒤 저수조 연결을 보류하는 저부하 운전 — 예외 점검은 가능한 범위를 좁혀 둔다. 추가 측정 전에는 경로를 확정하지 않는다.
보이지 않은 방류 기록과 확인된 염소 주입기의 구분 — 독립 확인|part_of,state,other|다음 단계 입력 결측|확인된 표본이 적을수록 보이지 않은 방류 기록과 확인된 염소 주입기의 구분 — 독립 확인은 연결의 방향과 범위를 보수적으로 적는다. 결측을 정상 상태로 간주하지 않는다. 다음 단계 입력 결측 항목은 확인된 관계만 확정하게 한다.
원수 유입구의 일부 기록만으로 여과지를 추정하지 않은 경로 — 분기 기록|state,boundary,other|중간 관측 결측|한 채널의 응답만으로 원수 유입구의 일부 기록만으로 여과지를 추정하지 않은 경로 — 분기 기록은 전체 연결을 판정하지 않는다. 다른 채널이 채워질 때까지 가능한 경로를 열어 둔다. 중간 관측 결측 항목은 확인된 관계만 확정하게 한다.
수질 계측기 관측 공백에서 수압 센서 범위 제한 — 중간 판정|process,other,role|출처 연결 불명|현장에 남은 자료는 수질 계측기 관측 공백에서 수압 센서 범위 제한 — 중간 판정은 전체 경로 중 일부만 보여 준다. 보이지 않은 단계를 사실처럼 서술하지 않는다. 출처 연결 불명 항목은 확인된 관계만 확정하게 한다.
후속 입력에 확인된 운영 당직표와 배수문의 부분 경로 — 신호 전달|classification,boundary,state||관측표에 보이는 구간만으로 후속 입력에 확인된 운영 당직표와 배수문의 부분 경로 — 신호 전달은 확인된 관계를 적는다. 빈 구간을 임의의 연결로 채우지 않는다.
정수 펌프 표본 부족 뒤 응집조 연결을 보류하는 경보 누적 — 대상 추적|state,comparison,other|식별 기록 상충|부분 로그를 읽을 때 정수 펌프 표본 부족 뒤 응집조 연결을 보류하는 경보 누적 — 대상 추적은 기록된 사실과 기록되지 않은 가능성을 구분한다. 가능성은 확정 문장으로 바꾸지 않는다. 식별 기록 상충 항목은 확인된 관계만 확정하게 한다.
보이지 않은 염소 주입기와 확인된 저수조의 구분 — 순서 기록|process,boundary,attribute||검토표에서 보이지 않은 염소 주입기와 확인된 저수조의 구분 — 순서 기록은 관측 빈칸과 확인값을 나눠 표시한다. 마지막 결과만으로 중간 관계를 복원하지 않는다.
응집조의 일부 기록만으로 여과지를 추정하지 않은 경로 — 상태 묶음|part_of,state,other|동시 개입 분리 불가|일부 표본만 남은 상황에서 응집조의 일부 기록만으로 여과지를 추정하지 않은 경로 — 상태 묶음은 관측된 단계와 추정된 단계를 분리한다. 미확인된 노드는 결론에 넣지 않는다. 동시 개입 분리 불가 항목은 확인된 관계만 확정하게 한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":112,"primary":"배수문 관측 공백에서 운영 당직표 범위 제한 — 결과 검증","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":113,"primary":"현장 재검에 확인된 수압 센서와 수질 계측기의 부분 경로 — 영향 검토","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":114,"primary":"여과지 표본 부족 뒤 저수조 연결을 보류하는 저부하 운전 — 예외 점검","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":115,"primary":"보이지 않은 방류 기록과 확인된 염소 주입기의 구분 — 독립 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":116,"primary":"원수 유입구의 일부 기록만으로 여과지를 추정하지 않은 경로 — 분기 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":117,"primary":"수질 계측기 관측 공백에서 수압 센서 범위 제한 — 중간 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":118,"primary":"후속 입력에 확인된 운영 당직표와 배수문의 부분 경로 — 신호 전달","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":119,"primary":"정수 펌프 표본 부족 뒤 응집조 연결을 보류하는 경보 누적 — 대상 추적","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":120,"primary":"보이지 않은 염소 주입기와 확인된 저수조의 구분 — 순서 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":121,"primary":"응집조의 일부 기록만으로 여과지를 추정하지 않은 경로 — 상태 묶음","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 10개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
