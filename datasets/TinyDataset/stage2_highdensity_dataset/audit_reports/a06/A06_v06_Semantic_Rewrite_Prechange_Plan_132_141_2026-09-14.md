# A06 v06:132~141 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `2098BA9725D8F5FDCBCA9B162455001296279ECC0D6EC1D80F6BEA67FD2A97E3`
- registry SHA-256: `446588E22C3B65CC86516DB1EA0C0D2B4396AF700B4C49277885524B55FC0E1C`
- locator는 `stage2_(16)relational_composition_high_density_train_v06.source.psv:132~141`으로 고정한다. source concept/text와 같은 locator registry primary 외 field·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v06_semantic_rewrite_132_141_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 132 | 염소 주입기 관측 공백에서 저수조 범위 제한 — 독립 확인 → 염소 주입 기록 공백의 저수조 수위 확인 | `process,boundary,attribute,other` | 확인 수위와 미확인 주입량을 나누어 증량을 막는다. |
| 133 | 보류 해제에 확인된 응집조와 여과지의 부분 경로 — 분기 기록 → 응집조 수위와 여과지 압력 동시 변화 보류 | `part_of,state,other` | 전체 과정에서 두 변화의 원인을 분리할 수 없어 운전 변경을 보류한다. |
| 134 | 저수조 표본 부족 뒤 운영 당직표 연결을 보류하는 경계 직전 — 중간 판정 → 저수조 표본 부족 시 당직 운전 보류 | `state,boundary,other` | 확인 수위와 미확인 지시를 구분해 조작을 보류한다. |
| 135 | 보이지 않은 누수 감시기와 확인된 정수 펌프의 구분 — 신호 전달 → 누수 감시기 공백의 정수 펌프 교대 점검 | `process,other,role` | 교대자가 확인 경보와 미확인 우회를 구분해 점검을 인계한다. |
| 136 | 배수문의 일부 기록만으로 운영 당직표를 추정하지 않은 경로 — 대상 추적 → 배수문 조작 기록 부족 시 당직 운전 분류 | `classification,boundary,state` | 조작 기록과 미확인 지시를 구분해 운전 보류 상태로 분류한다. |
| 137 | 수압 센서 관측 공백에서 수질 계측기 범위 제한 — 순서 기록 → 수압·수질 센서 기록 공백 대조 | `state,comparison,other` | 누락 압력값과 지속된 탁도값을 비교해 설비 이상 단정을 막는다. |
| 138 | 긴급 확인에 확인된 여과지와 원수 유입구의 부분 경로 — 상태 묶음 → 여과지 압력 저하 시 원수 유입량 조정 | `process,boundary,attribute` | 확인 압력 저하와 미확인 원수 부족을 구분해 밸브를 조정한다. |
| 139 | 방류 기록 표본 부족 뒤 수질 계측기 연결을 보류하는 중앙 표본 — 우선 처리 → 방류 표본 부족 시 수질 검사 단계 보류 | `part_of,state,other` | 전체 과정의 확인 방류 단계와 누락 수질 검사 단계를 나눈다. |
| 140 | 보이지 않은 원수 유입구와 확인된 여과지의 구분 — 연결 확인 → 원수 유입 중간 기록 결측의 여과지 운전 보류 | `state,boundary,other` | 확인 유입량과 중간에 빠진 여과지 압력을 구분해 밸브 조작을 보류한다. |
| 141 | 수질 계측기의 일부 기록만으로 수압 센서를 추정하지 않은 경로 — 출처 대조 → 수질 표본 누락 시 수압 이상 교대 인계 | `process,other,role` | 교대자가 수압 급락과 미확인 수질 원인을 구분해 현장 점검을 넘긴다. |

## 새 text

| line | text |
|---:|---|
| 132 | 염소 주입기 유량은 기록되지 않았고 저수조 수위만 낮아질 때, 염소 주입 기록 공백의 저수조 수위 확인은 운영자가 확인된 수위 변화와 확인되지 않은 주입량을 구분하는 과정이다. 범위 자료 부족 때문에 주입량을 늘리지 않아 저수조 농도 상승을 막는다. |
| 133 | 응집조 수위 저하와 여과지 압력 상승이 같은 시각에 나타나지만 어떤 조치가 먼저였는지 알 수 없을 때, 응집조 수위와 여과지 압력 동시 변화 보류는 전체 정수 과정에서 원인을 나누지 못한 보류 상태다. 동시 개입 분리 불가 때문에 펌프와 배수문을 함께 조정하지 않아 급수 압력 변동을 막는다. |
| 134 | 저수조 수위 표본이 적고 당직표에는 조작 시각만 남았을 때, 저수조 표본 부족 시 당직 운전 보류에서는 운영자가 확인된 수위 변화와 확인되지 않은 조작 지시를 구분한다. 후속 검증 누락 때문에 배수문을 조작하지 않아 과다 방류를 막는다. |
| 135 | 누수 감시기 경보가 특정 시각에만 있고 정수 펌프 우회 승인 시각이 없을 때, 누수 감시기 공백의 정수 펌프 교대 점검은 교대자가 확인된 경보와 승인되지 않은 우회를 구분해 현장 점검을 넘기는 과정이다. 예외 승인 시각 미상일 때는 펌프 출력을 바꾸지 않아 압력 변동을 막는다. |
| 136 | 배수문 조작 기록은 일부 남았지만 당직표에 지시와 위치가 없을 때, 배수문 조작 기록 부족 시 당직 운전 분류에서 운영자는 확인된 조작과 확인되지 않은 지시를 구분해 운전 보류 상태로 분류한다. 지시가 확인되기 전에는 배수문을 개방 상태로 확정하지 않아 과다 방류를 막는다. |
| 137 | 수압 센서 압력값은 누락됐는데 수질 계측기 탁도값은 계속 들어올 때, 수압·수질 센서 기록 공백 대조에서는 운영자가 이전 압력값과 현재 탁도값의 시각과 측정 지점을 비교한다. 센서 채널 불일치가 해소되기 전에는 관로 이상 상태로 확정하지 않아 불필요한 급수 중단을 막는다. |
| 138 | 여과지 압력이 낮아지고 원수 유입량도 줄어들 때, 여과지 압력 저하 시 원수 유입량 조정은 운영자가 확인된 압력 저하와 확인되지 않은 원수 부족을 구분해 밸브를 조정하는 과정이다. 유입 원인이 확인되기 전에는 유량을 늘리지 않아 여과지 압력 급락을 막는다. |
| 139 | 방류량 표본이 적고 다음 단계 수질 계측값이 없을 때, 방류 표본 부족 시 수질 검사 단계 보류는 전체 정수 처리 과정 중 확인된 방류 단계와 비어 있는 수질 검사 단계를 나누는 보류 상태다. 다음 단계 입력 결측 때문에 방류량을 정상으로 확정하지 않아 잘못된 수질 판정을 막는다. |
| 140 | 원수 유입량은 확인됐지만 여과지 압력 기록이 중간에 빠졌을 때, 원수 유입 중간 기록 결측의 여과지 운전 보류에서는 운영자가 확인된 유입량과 확인되지 않은 압력 변화를 구분한다. 중간 관측 결측 때문에 유입 밸브를 바로 열지 않아 여과지 압력 급락을 막는다. |
| 141 | 수질 계측기 표본은 일부 있고 수압 센서는 급락을 보낼 때, 수질 표본 누락 시 수압 이상 교대 인계는 교대자가 확인된 압력 변화와 확인되지 않은 수질 원인을 구분해 다음 당직자에게 현장 점검을 넘기는 과정이다. 출처 연결 불명 상태에서는 펌프 출력을 올리지 않아 압력 변동을 막는다. |

## 원복 source 행

```text
염소 주입기 관측 공백에서 저수조 범위 제한 — 독립 확인|process,boundary,attribute,other|범위 자료 부족|관측 범위가 제한된 보고서에서 염소 주입기 관측 공백에서 저수조 범위 제한 — 독립 확인은 보이는 단계만 책임 있게 설명한다. 누락된 단계는 추가 확인 항목으로 넘긴다. 범위 자료 부족 항목은 확인된 관계만 확정하게 한다.
보류 해제에 확인된 응집조와 여과지의 부분 경로 — 분기 기록|part_of,state,other|동시 개입 분리 불가|자료가 서로 다른 시점에 모였다면 보류 해제에 확인된 응집조와 여과지의 부분 경로 — 분기 기록은 확인 시점이 겹치는 구간만 연결한다. 나머지는 보류 상태로 남긴다. 동시 개입 분리 불가 항목은 확인된 관계만 확정하게 한다.
저수조 표본 부족 뒤 운영 당직표 연결을 보류하는 경계 직전 — 중간 판정|state,boundary,other|후속 검증 누락|센서 기록이 끊긴 지점 뒤에는 저수조 표본 부족 뒤 운영 당직표 연결을 보류하는 경계 직전 — 중간 판정은 가능한 범위를 좁혀 둔다. 추가 측정 전에는 경로를 확정하지 않는다. 후속 검증 누락 항목은 확인된 관계만 확정하게 한다.
보이지 않은 누수 감시기와 확인된 정수 펌프의 구분 — 신호 전달|process,other,role|예외 승인 시각 미상|확인된 표본이 적을수록 보이지 않은 누수 감시기와 확인된 정수 펌프의 구분 — 신호 전달은 연결의 방향과 범위를 보수적으로 적는다. 결측을 정상 상태로 간주하지 않는다. 예외 승인 시각 미상 항목은 확인된 관계만 확정하게 한다.
배수문의 일부 기록만으로 운영 당직표를 추정하지 않은 경로 — 대상 추적|classification,boundary,state||한 채널의 응답만으로 배수문의 일부 기록만으로 운영 당직표를 추정하지 않은 경로 — 대상 추적은 전체 연결을 판정하지 않는다. 다른 채널이 채워질 때까지 가능한 경로를 열어 둔다.
수압 센서 관측 공백에서 수질 계측기 범위 제한 — 순서 기록|state,comparison,other|센서 채널 불일치|현장에 남은 자료는 수압 센서 관측 공백에서 수질 계측기 범위 제한 — 순서 기록은 전체 경로 중 일부만 보여 준다. 보이지 않은 단계를 사실처럼 서술하지 않는다. 센서 채널 불일치 항목은 확인된 관계만 확정하게 한다.
긴급 확인에 확인된 여과지와 원수 유입구의 부분 경로 — 상태 묶음|process,boundary,attribute||관측표에 보이는 구간만으로 긴급 확인에 확인된 여과지와 원수 유입구의 부분 경로 — 상태 묶음은 확인된 관계를 적는다. 빈 구간을 임의의 연결로 채우지 않는다.
방류 기록 표본 부족 뒤 수질 계측기 연결을 보류하는 중앙 표본 — 우선 처리|part_of,state,other|다음 단계 입력 결측|부분 로그를 읽을 때 방류 기록 표본 부족 뒤 수질 계측기 연결을 보류하는 중앙 표본 — 우선 처리는 기록된 사실과 기록되지 않은 가능성을 구분한다. 가능성은 확정 문장으로 바꾸지 않는다. 다음 단계 입력 결측 항목은 확인된 관계만 확정하게 한다.
보이지 않은 원수 유입구와 확인된 여과지의 구분 — 연결 확인|state,boundary,other|중간 관측 결측|검토표에서 보이지 않은 원수 유입구와 확인된 여과지의 구분 — 연결 확인은 관측 빈칸과 확인값을 나눠 표시한다. 마지막 결과만으로 중간 관계를 복원하지 않는다. 중간 관측 결측 항목은 확인된 관계만 확정하게 한다.
수질 계측기의 일부 기록만으로 수압 센서를 추정하지 않은 경로 — 출처 대조|process,other,role|출처 연결 불명|일부 표본만 남은 상황에서 수질 계측기의 일부 기록만으로 수압 센서를 추정하지 않은 경로 — 출처 대조는 관측된 단계와 추정된 단계를 분리한다. 미확인된 노드는 결론에 넣지 않는다. 출처 연결 불명 항목은 확인된 관계만 확정하게 한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":132,"primary":"염소 주입기 관측 공백에서 저수조 범위 제한 — 독립 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":133,"primary":"보류 해제에 확인된 응집조와 여과지의 부분 경로 — 분기 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":134,"primary":"저수조 표본 부족 뒤 운영 당직표 연결을 보류하는 경계 직전 — 중간 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":135,"primary":"보이지 않은 누수 감시기와 확인된 정수 펌프의 구분 — 신호 전달","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":136,"primary":"배수문의 일부 기록만으로 운영 당직표를 추정하지 않은 경로 — 대상 추적","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":137,"primary":"수압 센서 관측 공백에서 수질 계측기 범위 제한 — 순서 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":138,"primary":"긴급 확인에 확인된 여과지와 원수 유입구의 부분 경로 — 상태 묶음","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":139,"primary":"방류 기록 표본 부족 뒤 수질 계측기 연결을 보류하는 중앙 표본 — 우선 처리","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":140,"primary":"보이지 않은 원수 유입구와 확인된 여과지의 구분 — 연결 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v06.source.psv","source_line":141,"primary":"수질 계측기의 일부 기록만으로 수압 센서를 추정하지 않은 경로 — 출처 대조","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-006","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 10개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
