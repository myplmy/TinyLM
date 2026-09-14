# A06 v03 의미 재서술 사전 변경 계획 — locator 132~141 (2026-09-14)

- precondition: source v03 `B1AA0233131301F717A906A407B3010CAEDCAB568F929B1C1FEDD6CC738D04BB`, registry `406891CD14978219745EFFF43D31CA2727F0B749CF3BCD6F80DBDB696494178B`.
- source `concept`·`text`와 동일 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 132 | 베드 온도 기록이 비었을 때 차광 모터의 조정 주체를 확인하는 절차 | process, other, role | 베드 기록과 작업자 출처가 없으면 모터 조정의 원인을 확인한다. |
| 133 | 수동 전환 뒤 순환팬과 압력 조절기 상태를 구분하는 기준 | classification, boundary, state | 수동 팬 전환과 압력 조절을 같은 고장 상태로 묶지 않는다. |
| 134 | 차광 모터 표본이 부족할 때 배수관 연결 비교를 보류하는 기준 | state, comparison, other | 모터 표본·식별값이 부족하면 배수관 연결 비교를 보류한다. |
| 135 | 기상 예보가 누락된 구간의 함수율 변화를 해석하는 절차 | process, boundary, attribute, other | 기상 자료 범위가 부족하면 수분 변화 원인을 제한해 해석한다. |
| 136 | 관수 밸브 일부 기록으로 배수관 구간을 확정하지 않는 상태 | part_of, state, other | 일부 밸브 기록만으로 배수관 부분 구간을 확정하지 않는다. |
| 137 | 환경 제어기 기록 공백에서 양액 탱크 수위를 미확정으로 두는 기준 | state, boundary, other | 제어기 명령·후속 검증이 없으면 수위 상승을 보충 완료와 구분한다. |
| 138 | 대체 압력 경로 사용 뒤 작업 인계를 확인하는 절차 | process, other, role | 우회 경로 승인 시각이 없으면 교대 책임 인계를 확인한다. |
| 139 | 환기창 표본이 부족할 때 양액 탱크 경보를 분류하지 않는 기준 | classification, boundary, state | 창 표본이 부족하면 수위 변화의 경보 상태를 성급히 분류하지 않는다. |
| 140 | 작업 기록 공백의 압력 조절기 경보 판단 기준 | state, comparison, other | 작업 기록과 채널별 압력값이 없거나 다르면 경보 해제를 보류한다. |
| 141 | 양액 탱크 일부 기록으로 제어기 보충 명령을 추정하지 않는 절차 | process, boundary, attribute | 일부 탱크 기록만으로 제어기 명령과 수위 변화를 연결하지 않는다. |

각 새 text에는 구체 대상, 결측·상충 계기, 판단 주체, 보류·제한의 결과를 독립적으로 넣는다. updater는 target 10과 비대상 7,790행 byte 보존을 검증하고, 적용 전 registry 행은 `A06_registry_before_v03_semantic_rewrite_132_141_2026-09-14.jsonl`에 보관한다.
