# A06 v03 의미 재서술 사전 변경 계획 — locator 122~131 (2026-09-14)

- precondition: source v03 `2C5589166084D3E4A7E9354650F2159A8F882B63F4CC320B344F7F3895BA7383`, registry `9B8D734AA525FCFAC0F9BF5CA26EE5EC0DE1DA62F8391D1FC2225A099F295274`.
- source `concept`·`text`와 동일 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 122 | 차광 모터 식별값과 베드 번호가 맞지 않을 때 비교를 보류하는 기준 | state, comparison, other | 모터·베드 식별값이 충돌하면 같은 구역 상태로 비교하지 않는다. |
| 123 | 비상 전환 뒤 기상 예보와 함수율 값을 대조하는 절차 | process, boundary, attribute | 비상 전환 뒤 시각이 다른 예보·수분값을 관수 원인으로 묶지 않는다. |
| 124 | 관수 밸브 표본이 부족할 때 재배 베드 배관 연결을 보류하는 상태 | part_of, state, other | 밸브 표본이 부족하면 베드와 배관의 부분 관계를 확정하지 않는다. |
| 125 | 환경 제어기 신호가 없는 양액 탱크 수위의 판단 기준 | state, boundary, other | 제어기 신호 없이 바뀐 수위를 보충 완료 상태로 분류하지 않는다. |
| 126 | 압력 조절기 부분 기록에서 교대 책임을 확인하는 절차 | process, other, role | 부분 조절기 기록과 승인 시각만으로 작업 인계를 확정하지 않는다. |
| 127 | 환기창 위치가 비었을 때 베드 온도 상태를 별도로 분류하는 기준 | classification, boundary, state | 창 위치 기록이 없으면 베드 온도 상태와 환기 상태를 구분한다. |
| 128 | 작업 기록과 압력값이 다른 채널일 때 상태 비교를 보류하는 기준 | state, comparison, other | 기록 시각·채널이 다르면 같은 압력 상태로 비교하지 않는다. |
| 129 | 양액 수위 표본이 적을 때 수분 저하 원인을 보류하는 절차 | process, boundary, attribute | 적은 수위 표본과 함수율 저하를 같은 보충 원인으로 연결하지 않는다. |
| 130 | 배수관의 후속 유량이 없을 때 밸브 위치를 확정하지 않는 상태 | part_of, state, other | 후속 유량이 없으면 밸브를 특정 배관 구간의 일부로 확정하지 않는다. |
| 131 | 함수율 일부 기록만으로 기상 예보 영향을 확정하지 않는 기준 | state, boundary, other | 중간 함수율 기록이 없으면 예보가 수분 변화 원인이라고 연결하지 않는다. |

각 새 text에는 구체 대상, 결측·상충 계기, 판단 주체, 보류·제한의 결과를 독립적으로 넣는다. updater는 target 10과 비대상 7,790행 byte 보존을 검증하고, 적용 전 registry 행은 `A06_registry_before_v03_semantic_rewrite_122_131_2026-09-14.jsonl`에 보관한다.
