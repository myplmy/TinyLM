# A06 v03 의미 재서술 사전 변경 계획 — locator 142~151 (2026-09-14)

- precondition: source v03 `B6082F1AAC48F910B63EC5F02C3C014FB2AC88C4B30870CD3A3B29D472277647`, registry `94BFA7D87A4E185066475D350167FACF51C42BEB4B34D7232936589CF0EBC9EE`.
- source `concept`·`text`와 동일 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 142 | 배수관 후속 기록이 없을 때 밸브 배관 관계를 보류하는 상태 | part_of, state, other | 후속 유량이 없으면 밸브를 특정 배관의 일부로 확정하지 않는다. |
| 143 | 새벽 기상 예보와 수분값의 상태 연결을 보류하는 기준 | state, boundary, other | 중간 관측이 없으면 새벽 예보·수분값을 같은 상태 변화로 묶지 않는다. |
| 144 | 재배 베드 표본이 부족할 때 작업자 조정을 확인하는 절차 | process, other, role | 베드 표본과 작업 기록이 부족하면 조정 주체를 확인한다. |
| 145 | 순환팬 공백에서 압력 조절기 변화를 독립 상태로 분류하는 기준 | classification, boundary, state | 팬 기록이 없으면 압력 변화를 환기 상태와 구분한다. |
| 146 | 차광 모터 식별 기록이 불일치할 때 베드 상태 비교를 보류하는 기준 | state, comparison, other | 식별 기록이 어긋나면 모터와 베드 상태를 비교하지 않는다. |
| 147 | 기상 관측이 비었을 때 함수율 수치의 원인을 보류하는 절차 | process, boundary, attribute | 기상 관측이 없으면 함수율 하나로 관수 원인을 특정하지 않는다. |
| 148 | 정기 운전 시각만으로 밸브 배수관의 부분 관계를 확정하지 않는 상태 | part_of, state, other | 정기 운전 시각만으로 밸브와 배수관의 부분 관계를 확정하지 않는다. |
| 149 | 제어기 신호가 부족할 때 환기창 위치를 정상 상태로 분류하지 않는 기준 | state, boundary, other | 제어기 신호가 부족하면 창 위치를 정상 자동 제어 상태로 분류하지 않는다. |
| 150 | 압력 조절기 기록 공백에서 작업 인계를 보류하는 절차 | process, other, role | 조절기 기록과 승인 시각이 없으면 교대 인계를 보류한다. |
| 151 | 환기창 기록이 일부일 때 베드 온도 상태를 확정하지 않는 기준 | classification, boundary, state | 일부 창 기록만으로 베드 온도 상태를 환기 결과로 확정하지 않는다. |

각 새 text에는 구체 대상, 결측·상충 계기, 판단 주체, 보류·제한의 결과를 독립적으로 넣는다. updater는 target 10과 비대상 7,790행 byte 보존을 검증하고, 적용 전 registry 행은 `A06_registry_before_v03_semantic_rewrite_142_151_2026-09-14.jsonl`에 보관한다.
