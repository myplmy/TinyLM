# A06 v06:62~71 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `7D72199D4C9666AE352BFDE7B915C4BCDFA52896EB2283E6B45CEEA5D85991A0`
- registry SHA-256: `D10C2262BF642E060777ABD235AFA632AA02BF19B0D13F2445BD198B2E817162`
- locator는 `stage2_(16)relational_composition_high_density_train_v06.source.psv:62~71`으로 고정한다. source concept/text와 같은 locator registry primary 외 field·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v06_semantic_rewrite_62_71_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 62 | 저수조 관측 공백에서 염소 주입기 범위 제한 — 영향 검토 → 저수조 기록 공백 시 염소 주입 점검 | `state,boundary,other` | 수위 결측에서 주입 증량을 보류하는 판단을 쓴다. |
| 63 | 다음 교대에 확인된 누수 감시기와 정수 펌프의 부분 경로 — 예외 점검 → 누수 감시기와 정수 펌프 교대 인계 | `process,other,role` | 교대자가 기록 출처·시점을 확인해 현장 점검을 인계한다. |
| 64 | 배수문 표본 부족 뒤 염소 주입기 연결을 보류하는 배치 변경 — 독립 확인 → 배수문 표본 부족 시 염소 주입 경로 분류 | `classification,boundary,state,other` | 배수문 위치와 우회 배관 기록을 구분하여 운전 보류로 분류한다. |
| 65 | 보이지 않은 수압 센서와 확인된 수질 계측기의 구분 — 분기 기록 → 수압 센서 공백의 수질 계측 비교 | `state,comparison,other` | 서로 다른 시점의 압력·탁도 추세를 함께 비교한다. |
| 66 | 여과지의 일부 기록만으로 원수 유입구를 추정하지 않은 경로 — 중간 판정 → 여과지 부분 기록의 원수 유입 점검 | `process,boundary,attribute` | 압력 표본과 유입량을 구분해 증량 전 점검한다. |
| 67 | 방류 기록 관측 공백에서 염소 주입기 범위 제한 — 신호 전달 → 방류 기록 누락에 따른 염소 주입 보류 | `part_of,state,other` | 전체 처리 과정의 확인된 주입 단계만 남기고 결정을 보류한다. |
| 68 | 교차 확인에 확인된 원수 유입구와 여과지의 부분 경로 — 대상 추적 → 원수 유입과 여과지 기록의 교차 확인 | `state,boundary,other` | 같은 시각의 확인값과 중간 결측 구간을 구분한다. |
| 69 | 수질 계측기 표본 부족 뒤 정수 펌프 연결을 보류하는 정상 복귀 — 순서 기록 → 수질 계측기 표본 부족 시 펌프 점검 인계 | `process,other,role` | 교대자가 탁도 표본·전류 기록의 출처를 확인해 인계한다. |
| 70 | 보이지 않은 운영 당직표와 확인된 배수문의 구분 — 상태 묶음 → 당직표 누락 시 배수문 상태 분류 | `classification,boundary,state` | 위치 기록과 누락된 지시를 구분해 운전 보류 상태로 분류한다. |
| 71 | 정수 펌프의 일부 기록만으로 누수 감시기를 추정하지 않은 경로 — 우선 처리 → 정수 펌프 부분 기록의 누수 감시기 대조 | `state,comparison,other` | 전류·압력 추세를 대조하고 누수 단정을 멈춘다. |

## 새 text

| line | text |
|---:|---|
| 62 | 저수조 수위 기록이 없고 염소 주입량만 남아 있을 때, 저수조 기록 공백 시 염소 주입 점검에서는 당직자가 확인된 주입량과 확인되지 않은 수위 변화를 구분한다. 후속 검증 누락 때문에 주입량 증가는 보류하여 저수조 농도 변동을 막는다. |
| 63 | 누수 감시기 경보와 정수 펌프 전류값이 다음 교대에 함께 확인됐을 때, 누수 감시기와 정수 펌프 교대 인계는 교대자가 두 기록의 시간과 출처를 확인해 다음 당직자에게 현장 점검을 넘기는 과정이다. 예외 승인 시각 미상일 때는 펌프 출력을 바꾸지 않아 압력 변동을 막는다. |
| 64 | 배수문 위치 표본이 적고 염소 주입기의 우회 배관 기록도 없을 때, 배수문 표본 부족 시 염소 주입 경로 분류에서는 운영자가 확인된 배수문 위치와 확인되지 않은 우회 배관을 구분해 운전 보류 상태로 분류한다. 대체 경로 기록 결측 때문에 주입 위치를 바꾸지 않아 농도 편차를 막는다. |
| 65 | 수압 센서 값이 비어 있고 수질 계측기 탁도값만 들어올 때, 수압 센서 공백의 수질 계측 비교에서는 운영자가 이전 수압 추세와 현재 탁도 추세를 함께 비교한다. 센서 채널 불일치 상태에서는 관로 막힘으로 단정하지 않아 불필요한 펌프 정지를 막는다. |
| 66 | 여과지 압력 기록이 일부 시각에만 있고 원수 유입량이 새로 들어올 때, 여과지 부분 기록의 원수 유입 점검은 운영자가 확인된 압력 표본과 유입량을 구분해 증량 여부를 점검하는 과정이다. 압력 측정 전에는 유입량을 늘리지 않아 여과지 막힘 위험을 낮춘다. |
| 67 | 방류량 기록이 누락되고 염소 주입기 유량만 남아 있을 때, 방류 기록 누락에 따른 염소 주입 보류는 전체 처리 과정 중 확인된 주입 단계만 가리키는 보류 상태다. 다음 단계 입력 결측 때문에 방류량을 추정해 주입량을 바꾸지 않아 근거 없는 농도 조정을 막는다. |
| 68 | 원수 유입량과 여과지 압력 기록이 서로 다른 시각에만 확인될 때, 원수 유입과 여과지 기록의 교차 확인에서는 운영자가 동시에 확인된 값과 중간에 비어 있는 값의 구간을 구분한다. 중간 관측 결측 때문에 유입량 증가는 보류하여 여과지 압력 급등을 막는다. |
| 69 | 수질 계측기 탁도 표본이 적고 펌프 전류 기록은 다음 교대에 이어질 때, 수질 계측기 표본 부족 시 펌프 점검 인계는 교대자가 두 기록의 출처와 시점을 확인해 현장 점검을 넘기는 과정이다. 출처 연결 불명 상태에서는 펌프 출력을 바꾸지 않아 압력 변동을 막는다. |
| 70 | 당직표 지시가 누락되고 배수문 위치 기록만 남을 때, 당직표 누락 시 배수문 상태 분류에서는 운영자가 확인된 위치와 확인되지 않은 운전 지시를 구분해 운전 보류 상태로 분류한다. 지시가 확인되기 전에는 배수문을 개방 상태로 확정하지 않아 과다 방류를 막는다. |
| 71 | 정수 펌프 전류 기록이 일부 시각에만 있고 누수 감시기 압력이 낮게 나타날 때, 정수 펌프 부분 기록의 누수 감시기 대조에서는 운영자가 두 추세를 비교한다. 식별 기록 상충 상태에서는 누수로 단정하지 않아 불필요한 펌프 정지를 막는다. |

## 원복 source 행

```text
저수조 관측 공백에서 염소 주입기 범위 제한 — 영향 검토|state,boundary,other|후속 검증 누락|관측 범위가 제한된 보고서에서 저수조 관측 공백에서 염소 주입기 범위 제한 — 영향 검토는 보이는 단계만 책임 있게 설명한다. 누락된 단계는 추가 확인 항목으로 넘긴다. 후속 검증 누락 항목은 확인된 관계만 확정하게 한다.
다음 교대에 확인된 누수 감시기와 정수 펌프의 부분 경로 — 예외 점검|process,other,role|예외 승인 시각 미상|자료가 서로 다른 시점에 모였다면 다음 교대에 확인된 누수 감시기와 정수 펌프의 부분 경로 — 예외 점검은 확인 시점이 겹치는 구간만 연결한다. 나머지는 보류 상태로 남긴다. 예외 승인 시각 미상 항목은 확인된 관계만 확정하게 한다.
배수문 표본 부족 뒤 염소 주입기 연결을 보류하는 배치 변경 — 독립 확인|classification,boundary,state,other|대체 경로 기록 결측|센서 기록이 끊긴 지점 뒤에는 배수문 표본 부족 뒤 염소 주입기 연결을 보류하는 배치 변경 — 독립 확인은 가능한 범위를 좁혀 둔다. 추가 측정 전에는 경로를 확정하지 않는다. 대체 경로 기록 결측 항목은 확인된 관계만 확정하게 한다.
보이지 않은 수압 센서와 확인된 수질 계측기의 구분 — 분기 기록|state,comparison,other|센서 채널 불일치|확인된 표본이 적을수록 보이지 않은 수압 센서와 확인된 수질 계측기의 구분 — 분기 기록은 연결의 방향과 범위를 보수적으로 적는다. 결측을 정상 상태로 간주하지 않는다. 센서 채널 불일치 항목은 확인된 관계만 확정하게 한다.
여과지의 일부 기록만으로 원수 유입구를 추정하지 않은 경로 — 중간 판정|process,boundary,attribute||한 채널의 응답만으로 여과지의 일부 기록만으로 원수 유입구를 추정하지 않은 경로 — 중간 판정은 전체 연결을 판정하지 않는다. 다른 채널이 채워질 때까지 가능한 경로를 열어 둔다.
방류 기록 관측 공백에서 염소 주입기 범위 제한 — 신호 전달|part_of,state,other|다음 단계 입력 결측|현장에 남은 자료는 방류 기록 관측 공백에서 염소 주입기 범위 제한 — 신호 전달은 전체 경로 중 일부만 보여 준다. 보이지 않은 단계를 사실처럼 서술하지 않는다. 다음 단계 입력 결측 항목은 확인된 관계만 확정하게 한다.
교차 확인에 확인된 원수 유입구와 여과지의 부분 경로 — 대상 추적|state,boundary,other|중간 관측 결측|관측표에 보이는 구간만으로 교차 확인에 확인된 원수 유입구와 여과지의 부분 경로 — 대상 추적은 확인된 관계를 적는다. 빈 구간을 임의의 연결로 채우지 않는다. 중간 관측 결측 항목은 확인된 관계만 확정하게 한다.
수질 계측기 표본 부족 뒤 정수 펌프 연결을 보류하는 정상 복귀 — 순서 기록|process,other,role|출처 연결 불명|부분 로그를 읽을 때 수질 계측기 표본 부족 뒤 정수 펌프 연결을 보류하는 정상 복귀 — 순서 기록은 기록된 사실과 기록되지 않은 가능성을 구분한다. 가능성은 확정 문장으로 바꾸지 않는다. 출처 연결 불명 항목은 확인된 관계만 확정하게 한다.
보이지 않은 운영 당직표와 확인된 배수문의 구분 — 상태 묶음|classification,boundary,state||검토표에서 보이지 않은 운영 당직표와 확인된 배수문의 구분 — 상태 묶음은 관측 빈칸과 확인값을 나눠 표시한다. 마지막 결과만으로 중간 관계를 복원하지 않는다.
정수 펌프의 일부 기록만으로 누수 감시기를 추정하지 않은 경로 — 우선 처리|state,comparison,other|식별 기록 상충|일부 표본만 남은 상황에서 정수 펌프의 일부 기록만으로 누수 감시기를 추정하지 않은 경로 — 우선 처리는 관측된 단계와 추정된 단계를 분리한다. 미확인된 노드는 결론에 넣지 않는다. 식별 기록 상충 항목은 확인된 관계만 확정하게 한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":62,"primary":"저수조 관측 공백에서 염소 주입기 범위 제한 — 영향 검토","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":63,"primary":"다음 교대에 확인된 누수 감시기와 정수 펌프의 부분 경로 — 예외 점검","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":64,"primary":"배수문 표본 부족 뒤 염소 주입기 연결을 보류하는 배치 변경 — 독립 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":65,"primary":"보이지 않은 수압 센서와 확인된 수질 계측기의 구분 — 분기 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":66,"primary":"여과지의 일부 기록만으로 원수 유입구를 추정하지 않은 경로 — 중간 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":67,"primary":"방류 기록 관측 공백에서 염소 주입기 범위 제한 — 신호 전달","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":68,"primary":"교차 확인에 확인된 원수 유입구와 여과지의 부분 경로 — 대상 추적","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":69,"primary":"수질 계측기 표본 부족 뒤 정수 펌프 연결을 보류하는 정상 복귀 — 순서 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":70,"primary":"보이지 않은 운영 당직표와 확인된 배수문의 구분 — 상태 묶음","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":71,"primary":"정수 펌프의 일부 기록만으로 누수 감시기를 추정하지 않은 경로 — 우선 처리","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 10개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
