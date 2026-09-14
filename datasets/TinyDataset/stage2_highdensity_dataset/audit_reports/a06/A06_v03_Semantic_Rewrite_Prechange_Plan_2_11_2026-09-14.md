# A06 v03 의미 재서술 사전 변경 계획 — locator 2~11 (2026-09-14)

## 범위와 precondition

- 대상: `stage2_(16)relational_composition_high_density_train_v03.source.psv`의 physical line 2~11과 같은 locator의 A06 term registry `primary`뿐이다.
- 예약 family: `S2-A06-T-003` — 스마트 온실 관수·환경제어 / 부분 관측에서 가능한 관계망 제한.
- 수정 전 source SHA-256: `663BC5284A20B62B9940B640B4D663CB8F6A688DC183A7D215C88E86FF9D9EAF`.
- 수정 전 registry SHA-256: `15899E70972E512B1F78878EA56A2DC7173AC5296750A08EFC7C818F3049B3DD`.
- `concept`와 `text`는 source에서 함께 바꾸고, registry에서는 정확히 같은 `source_file + source_line`의 `primary` 토큰만 바꾼다. relations, `other_type`, registry의 definition/provenance/review_status, 행 순서와 모든 비대상 바이트는 보존한다.
- v01, v02 잔여 행, A01~A05, package `train/val`, manifest, 중앙 원장, checkpoint, 공용 감사기는 이번 변경에서 제외한다.

## locator별 변경 판단

| locator | 기존 concept | 새 concept | 보존 relations | 재서술 근거 |
|---|---|---|---|---|
| v03:2 | 차광 모터 관측 공백에서 재배 베드 범위 제한 — 우선 처리 | 차광막 위치가 비어 있을 때 베드 상태를 제한하는 기준 | state, comparison, other | 표식과 불투명한 ‘범위 제한’을 차광막 위치 신호·베드 온도·식별 기록 상충·운영자 보류 판단으로 구체화한다. |
| v03:3 | 비상 전환에 확인된 기상 예보와 함수율 센서의 부분 경로 — 연결 확인 | 비상 전환 중 기상 정보와 수분 관측의 연결 범위 | process, boundary, attribute | 비상 전원·두 센서의 수신 시각과 함수율을 제시하고, 단일 표본을 하나의 관수 원인으로 묶지 않는 경계를 명시한다. |
| v03:4 | 관수 밸브 표본 부족 뒤 재배 베드 연결을 보류하는 중앙 표본 — 출처 대조 | 관수 밸브 표본이 부족할 때 베드 연결을 보류하는 기준 | part_of, state, other | 밸브 개폐 기록과 베드 수분 변화가 겹쳐도 동시 개입을 분리할 수 없는 경우를 밝혀 부분 관계 보류의 이유를 독립화한다. |
| v03:5 | 보이지 않은 환경 제어기와 확인된 양액 탱크의 구분 — 범위 확인 | 제어기 기록이 없는 양액 보충의 판단 범위 | state, boundary, other | 제어기 명령 부재와 탱크 수위 감소를 구분하고, 후속 검증 누락 시 수동 작업 기록을 대조하게 한다. |
| v03:6 | 압력 조절기의 일부 기록만으로 작업 기록을 추정하지 않은 경로 — 운영 인계 | 압력 기록만 있을 때 작업 승인 시각을 보류하는 절차 | process, other, role | 압력값, 정비 작업자 승인 기록, 관리자 인계를 명시해 승인 시각을 추정하지 않는 책임 경계를 만든다. |
| v03:7 | 환기창 관측 공백에서 재배 베드 범위 제한 — 회복 판정 | 환기창 관측이 끊긴 구역의 베드 상태 분류 | classification, boundary, state | 환기창 신호 공백과 베드 온도를 기준으로 정상 환기 구역과 구분하며, 회복 완료 오판을 막는 분류를 설명한다. |
| v03:8 | 경계 직전에 확인된 작업 기록과 압력 조절기의 부분 경로 — 경로 보존 | 센서 채널이 다른 압력 기록의 비교 범위 | state, comparison, other | 앞단·뒷단 센서의 시차와 압력값을 비교하고, 동시 구간만 연결해 과도한 조정을 막는 기준으로 바꾼다. |
| v03:9 | 양액 탱크 표본 부족 뒤 함수율 센서 연결을 보류하는 배치 변경 — 결과 검증 | 양액 수위 표본이 부족할 때 수분 연결을 보류하는 절차 | process, boundary, attribute | 수위와 함수율 표본의 순서를 확인하기 전에는 두 값을 같은 관수 원인으로 묶지 않는 과정을 독립적으로 밝힌다. |
| v03:10 | 보이지 않은 배수관과 확인된 관수 밸브의 구분 — 영향 검토 | 배수관 입력이 없을 때 관수 밸브 연결의 범위 | part_of, state, other | 배수관 유량 부재와 밸브 개폐 시각을 구분하고, 확인된 배관 구간만 부분 관계로 기록하게 한다. |
| v03:11 | 함수율 센서의 일부 기록만으로 기상 예보를 추정하지 않은 경로 — 예외 점검 | 수분 기록이 끊긴 뒤 기상 예보 연결을 보류하는 기준 | state, boundary, other | 마지막 수분 측정과 강수 경보의 시간차를 비교해 원인 연결을 보류하고 과습·건조 위험을 줄이는 경계를 설명한다. |

## 반영 예정 source text

1. 온실 제어에서 차광막 위치가 비어 있을 때 베드 상태를 제한하는 기준은 차광막의 현재 위치 신호가 없고 재배 베드의 온도 기록만 남았을 때, 온도 상승을 차광 동작의 결과로 단정하지 않는 상태 판단이다. 식별 기록 상충이 있으면 운영자는 차광막 번호와 베드 번호가 함께 확인된 구역만 비교하고, 그 밖의 연결은 현장 확인 전까지 보류해 잘못된 제어 명령을 막는다.
2. 비상 전환 중 기상 정보와 수분 관측의 연결 범위는 비상 전원이 들어온 뒤 기상 예보 서버의 경보와 함수율 센서의 수분값이 한 차례만 들어왔을 때, 두 값을 하나의 관수 판단 경로로 묶지 않고 별도 정보로 구분하는 절차다. 온실 운영자는 수신 시각과 함수율을 다시 비교한 뒤 다음 표본이 도착할 때까지 환기 명령과 관수 명령을 독립 항목으로 두어 성급한 전환을 막는다.
3. 관수 밸브 표본이 부족할 때 베드 연결을 보류하는 기준은 한 관수 밸브의 개폐 기록과 한 재배 베드의 수분 변화가 같은 시각에 겹쳐도, 다른 밸브의 개입을 분리할 수 없으면 둘을 직접 연결하지 않는 상태 결정이다. 동시 개입 분리 불가가 확인되면 담당자는 확인된 밸브와 베드 조합만 기록하고, 나머지 배관 연결은 추가 표본이 생길 때까지 보류해 잘못된 부분 관계를 막는다.
4. 제어기 기록이 없는 양액 보충의 판단 범위는 환경 제어기의 투입 명령이 남지 않고 양액 탱크 수위만 낮아졌을 때, 수위 감소를 자동 보충의 증거로 처리하지 않는 구분 기준이다. 후속 검증 누락 상태에서는 운영자가 탱크 수위와 수동 작업 기록을 별도로 확인하고, 확인되지 않은 보충 원인은 다음 점검까지 미결로 남겨 제어기와 작업자의 역할을 혼동하지 않게 한다.
5. 압력 기록만 있을 때 작업 승인 시각을 보류하는 절차에서는 압력 조절기의 값이 변했지만 정비 작업자의 승인 기록이 비어 있으면, 그 값을 승인된 조정의 결과로 연결하지 않는다. 예외 승인 시각 미상인 경우 관리자는 압력 변화 시각과 작업자 인계 기록을 따로 보관하고, 승인 시각이 확인될 때까지 자동 복구 작업을 실행하지 않아 책임 범위를 보존한다.
6. 환기창 관측이 끊긴 구역의 베드 상태 분류는 환기창 개방 신호가 사라진 뒤 재배 베드의 온도만 계속 측정될 때, 해당 베드를 정상 환기 구역과 구분하는 분류 작업이다. 관리자는 마지막 개방 시각과 현재 온도 값을 함께 표시하고, 중간 신호가 없는 구역을 회복 완료로 분류하지 않아 잘못된 상태 전환을 막는다.
7. 센서 채널이 다른 압력 기록의 비교 범위는 압력 조절기 앞단 센서와 뒷단 센서가 서로 다른 시각에 값을 보냈을 때, 두 값을 같은 조절 상태로 판단하지 않도록 하는 기준이다. 센서 채널 불일치가 있으면 운영자는 각 채널의 측정 시각과 압력을 비교해 동시 구간만 연결하고, 시차가 큰 값은 경보 원인 판정에서 제외해 과도한 압력 조정을 막는다.
8. 양액 수위 표본이 부족할 때 수분 연결을 보류하는 절차는 양액 탱크의 수위 기록이 드문데 함수율 센서가 낮은 수분값을 보였을 때, 두 값을 같은 관수 원인으로 묶지 않고 별도 관측으로 구분하는 과정이다. 운영자는 수위와 함수율의 다음 표본을 받은 뒤 변화 순서를 확인하고, 확인 전에는 배치 변경을 멈춰 불필요한 양액 공급을 막는다.
9. 배수관 입력이 없을 때 관수 밸브 연결의 범위는 배수관 유량 기록이 비어 있고 관수 밸브의 개폐 시각만 남았을 때, 밸브 개폐를 배수관 흐름의 일부로 단정하지 않는 부분 관계 기준이다. 다음 단계 입력 결측이 있으면 담당자는 확인된 밸브와 재배 베드 배관 구간만 연결하고, 배수관 쪽 원인은 다음 입력이 들어올 때까지 보류해 잘못된 배관 점검을 막는다.
10. 수분 기록이 끊긴 뒤 기상 예보 연결을 보류하는 기준은 함수율 센서의 마지막 값 뒤에 기상 예보의 강수 경보가 도착했을 때, 경보를 기존 수분 상태의 원인으로 확정하지 않는 경계 판단이다. 중간 관측 결측이 있으면 운영자는 센서의 마지막 측정 시각과 예보 발행 시각을 비교하고, 새 측정 전까지 관수량 변경을 보류해 건조와 과습의 위험을 줄인다.

## 원복용 원문

아래는 source의 수정 전 10행이다. 같은 locator의 registry 원문은 아래 JSONL로 보존되며, 실제 반영 시 updater가 `old_primary` 일치를 사전 조건으로 다시 확인한다.

```text
차광 모터 관측 공백에서 재배 베드 범위 제한 — 우선 처리|state,comparison,other|식별 기록 상충|확인된 표본이 적을수록 차광 모터 관측 공백에서 재배 베드 범위 제한 — 우선 처리는 연결의 방향과 범위를 보수적으로 적는다. 결측을 정상 상태로 간주하지 않는다. 식별 기록 상충 항목은 확인된 관계만 확정하게 한다.
비상 전환에 확인된 기상 예보와 함수율 센서의 부분 경로 — 연결 확인|process,boundary,attribute||한 채널의 응답만으로 비상 전환에 확인된 기상 예보와 함수율 센서의 부분 경로 — 연결 확인은 전체 연결을 판정하지 않는다. 다른 채널이 채워질 때까지 가능한 경로를 열어 둔다.
관수 밸브 표본 부족 뒤 재배 베드 연결을 보류하는 중앙 표본 — 출처 대조|part_of,state,other|동시 개입 분리 불가|현장에 남은 자료는 관수 밸브 표본 부족 뒤 재배 베드 연결을 보류하는 중앙 표본 — 출처 대조는 전체 경로 중 일부만 보여 준다. 보이지 않은 단계를 사실처럼 서술하지 않는다. 동시 개입 분리 불가 항목은 확인된 관계만 확정하게 한다.
보이지 않은 환경 제어기와 확인된 양액 탱크의 구분 — 범위 확인|state,boundary,other|후속 검증 누락|관측표에 보이는 구간만으로 보이지 않은 환경 제어기와 확인된 양액 탱크의 구분 — 범위 확인은 확인된 관계를 적는다. 빈 구간을 임의의 연결로 채우지 않는다. 후속 검증 누락 항목은 확인된 관계만 확정하게 한다.
압력 조절기의 일부 기록만으로 작업 기록을 추정하지 않은 경로 — 운영 인계|process,other,role|예외 승인 시각 미상|부분 로그를 읽을 때 압력 조절기의 일부 기록만으로 작업 기록을 추정하지 않은 경로 — 운영 인계는 기록된 사실과 기록되지 않은 가능성을 구분한다. 가능성은 확정 문장으로 바꾸지 않는다. 예외 승인 시각 미상 항목은 확인된 관계만 확정하게 한다.
환기창 관측 공백에서 재배 베드 범위 제한 — 회복 판정|classification,boundary,state||검토표에서 환기창 관측 공백에서 재배 베드 범위 제한 — 회복 판정은 관측 빈칸과 확인값을 나눠 표시한다. 마지막 결과만으로 중간 관계를 복원하지 않는다.
경계 직전에 확인된 작업 기록과 압력 조절기의 부분 경로 — 경로 보존|state,comparison,other|센서 채널 불일치|일부 표본만 남은 상황에서 경계 직전에 확인된 작업 기록과 압력 조절기의 부분 경로 — 경로 보존은 관측된 단계와 추정된 단계를 분리한다. 미확인된 노드는 결론에 넣지 않는다. 센서 채널 불일치 항목은 확인된 관계만 확정하게 한다.
양액 탱크 표본 부족 뒤 함수율 센서 연결을 보류하는 배치 변경 — 결과 검증|process,boundary,attribute||관측 범위가 제한된 보고서에서 양액 탱크 표본 부족 뒤 함수율 센서 연결을 보류하는 배치 변경 — 결과 검증은 보이는 단계만 책임 있게 설명한다. 누락된 단계는 추가 확인 항목으로 넘긴다.
보이지 않은 배수관과 확인된 관수 밸브의 구분 — 영향 검토|part_of,state,other|다음 단계 입력 결측|자료가 서로 다른 시점에 모였다면 보이지 않은 배수관과 확인된 관수 밸브의 구분 — 영향 검토는 확인 시점이 겹치는 구간만 연결한다. 나머지는 보류 상태로 남긴다. 다음 단계 입력 결측 항목은 확인된 관계만 확정하게 한다.
함수율 센서의 일부 기록만으로 기상 예보를 추정하지 않은 경로 — 예외 점검|state,boundary,other|중간 관측 결측|센서 기록이 끊긴 지점 뒤에는 함수율 센서의 일부 기록만으로 기상 예보를 추정하지 않은 경로 — 예외 점검은 가능한 범위를 좁혀 둔다. 추가 측정 전에는 경로를 확정하지 않는다. 중간 관측 결측 항목은 확인된 관계만 확정하게 한다.
```

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v03.source.psv","source_line":2,"primary":"차광 모터 관측 공백에서 재배 베드 범위 제한 — 우선 처리","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-003","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v03.source.psv","source_line":3,"primary":"비상 전환에 확인된 기상 예보와 함수율 센서의 부분 경로 — 연결 확인","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-003","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v03.source.psv","source_line":4,"primary":"관수 밸브 표본 부족 뒤 재배 베드 연결을 보류하는 중앙 표본 — 출처 대조","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-003","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v03.source.psv","source_line":5,"primary":"보이지 않은 환경 제어기와 확인된 양액 탱크의 구분 — 범위 확인","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-003","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v03.source.psv","source_line":6,"primary":"압력 조절기의 일부 기록만으로 작업 기록을 추정하지 않은 경로 — 운영 인계","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-003","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v03.source.psv","source_line":7,"primary":"환기창 관측 공백에서 재배 베드 범위 제한 — 회복 판정","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-003","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v03.source.psv","source_line":8,"primary":"경계 직전에 확인된 작업 기록과 압력 조절기의 부분 경로 — 경로 보존","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-003","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v03.source.psv","source_line":9,"primary":"양액 탱크 표본 부족 뒤 함수율 센서 연결을 보류하는 배치 변경 — 결과 검증","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-003","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v03.source.psv","source_line":10,"primary":"보이지 않은 배수관과 확인된 관수 밸브의 구분 — 영향 검토","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-003","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v03.source.psv","source_line":11,"primary":"함수율 센서의 일부 기록만으로 기상 예보를 추정하지 않은 경로 — 예외 점검","term_kind":"constructed_scenario","definition":"스마트 온실 관수·환경제어에서 부분 관측에서 가능한 관계망 제한을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-003","review_status":"generated_pending_semantic_review"}
```
