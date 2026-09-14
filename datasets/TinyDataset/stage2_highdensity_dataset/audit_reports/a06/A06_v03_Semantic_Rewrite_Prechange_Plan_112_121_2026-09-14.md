# A06 v03 의미 재서술 사전 변경 계획 — locator 112~121 (2026-09-14)

- precondition: source v03 `FDFAD41631CC048EDA7367DA9AB2050F7D56A6C5786D5C948CADE93D3D56EDFA`, registry `661C115AC42D6382B801DF68DAFC0D8AB5AA149741FE89B9AEC9EA1CCB7E40C1`.
- source `concept`·`text`와 동일 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 112 | 관수 밸브 기록이 없을 때 배수관 구간을 확정하지 않는 상태 | part_of, state, other | 밸브 기록이 없으면 배수관 유량만으로 부분 구간을 확정하지 않는다. |
| 113 | 새벽 제어기 명령만으로 양액 탱크 보충을 확정하지 않는 기준 | state, boundary, other | 새벽 명령 하나와 부족한 검증으로 보충 완료 상태를 확정하지 않는다. |
| 114 | 압력 조절기 표본이 부족할 때 차광 모터 조정을 보류하는 절차 | process, other, role | 승인 시각이 없으면 압력 변화와 차광 조정을 연결하지 않는다. |
| 115 | 환기창 기록이 없을 때 재배 베드 상태를 따로 분류하는 기준 | classification, boundary, state | 창 기록이 없으면 베드 온도 변화를 환기 상태로 묶지 않는다. |
| 116 | 작업 기록 일부로 압력 조절기 상태를 비교하지 않는 기준 | state, comparison, other | 작업표와 채널별 값이 맞지 않으면 압력 상태 비교를 보류한다. |
| 117 | 양액 탱크 기록 공백에서 제어기 명령을 보류하는 절차 | process, boundary, attribute | 수위·농도 기록이 비면 명령과 탱크 변화를 연결하지 않는다. |
| 118 | 정기 운전 기록만으로 배수관과 밸브 연결을 확정하지 않는 상태 | part_of, state, other | 정기 운전 시각만으로 밸브를 특정 배관 부분에 연결하지 않는다. |
| 119 | 함수율 표본이 부족할 때 순환팬 연결을 보류하는 기준 | state, boundary, other | 수분 표본이 부족하면 팬 운전과 베드 상태의 연결을 보류한다. |
| 120 | 재배 베드 기록이 없을 때 차광 모터 조정을 확인하는 절차 | process, other, role | 베드 기록과 조정 주체가 불명확하면 모터 조정을 확인한다. |
| 121 | 순환팬 기록 일부로 압력 조절기 상태를 분류하지 않는 기준 | classification, boundary, state | 팬 일부 기록만으로 압력 조정 상태를 분류하지 않는다. |

각 새 text에는 구체 대상, 결측·상충 계기, 판단 주체, 보류·제한의 결과를 독립적으로 넣는다. updater는 target 10과 비대상 7,790행 byte 보존을 검증하고, 적용 전 registry 행은 `A06_registry_before_v03_semantic_rewrite_112_121_2026-09-14.jsonl`에 보관한다.
