# A06 v03 의미 재서술 사전 변경 계획 — locator 62~71 (2026-09-14)

- precondition: source v03 `ADB80CEF8E3472D866C9337AD311883005207FA8A9BFC35F2D773613C849C138`, registry `124A58345FF09624697BD8FE4AF60D047DD9FEAEC6C2641FB1FAE8F6E9FBFF19`.
- source `concept`·`text`와 동일 registry locator `primary` 10개만 바꾸며 relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 판단 |
|---|---|---|---|
| 62 | 식별값이 엇갈린 차광 모터와 베드의 비교 기준 | state, comparison, other | 장치·베드 식별값이 엇갈리면 상태 비교에서 제외한다. |
| 63 | 비상 전원 전환 후 기상 예보와 수분값의 연결 경계 | process, boundary, attribute | 단일 예보·수분값을 관수 전환의 원인으로 묶지 않는다. |
| 64 | 관수 밸브 표본 부족 시 베드 배관 연결의 보류 | part_of, state, other | 밸브 표본이 부족하면 베드 배관의 부분 관계를 보류한다. |
| 65 | 제어기 기록이 없는 양액 탱크 상태의 구분 | state, boundary, other | 제어기 기록 없이 변한 수위를 보충 완료 상태와 구분한다. |
| 66 | 압력 조절기 기록만 있을 때 작업 인계를 보류하는 절차 | process, other, role | 조절기 로그만으로 작업자 인계를 확정하지 않는다. |
| 67 | 환기창 기록 공백에서 베드 분류를 보류하는 기준 | classification, boundary, state, other | 대체 경로의 창 기록이 없으면 베드 분류를 보류한다. |
| 68 | 작업 기록과 압력값의 시차를 비교하는 기준 | state, comparison, other | 시차가 있는 작업·압력 기록을 같은 상태로 비교하지 않는다. |
| 69 | 양액 표본 부족 시 함수율 연결을 보류하는 절차 | process, boundary, attribute | 수위·함수율의 단일 표본을 같은 보충 원인으로 묶지 않는다. |
| 70 | 배수관 입력이 없는 밸브 배관 관계의 보류 | part_of, state, other | 배수관 입력 부재의 밸브를 배관 경로 일부로 확정하지 않는다. |
| 71 | 수분 기록만 있을 때 기상 예보 연결을 보류하는 기준 | state, boundary, other | 수분 기록 하나만으로 기상 예보의 원인 연결을 보류한다. |

new text는 각각 구체 대상·결측·판단 주체·안전 결과를 독립적으로 포함한다. updater는 target 10과 비대상 7,790행 byte 보존을 검증하고 backup은 `A06_registry_before_v03_semantic_rewrite_62_71_2026-09-14.jsonl`이다.
