# A06 v03 의미 재서술 사전 변경 계획 — locator 42~51 (2026-09-14)

- precondition: source v03 `F896BE8075ABABA0D036D8A3F231EE9CA3A3BB719476459C5910151D7E14F1A5`, registry `375C2765136DDEE41CBDEB4F40DB6AF4978EAD71EEBF64932868F4B219DF1D9C`.
- 대상: source physical line 42~51의 `concept`·`text`, 같은 locator registry `primary` 10개. relations·`other_type`·registry 비-primary field·행 순서·비대상 바이트 보존.

| locator | 새 concept | relations | 판단 |
|---|---|---|---|
| 42 | 압력 조절기 공백에서 작업 인계 범위를 정하는 절차 | process, other, role | 승인 시각이 없는 압력 조정을 인계 기록의 범위 밖으로 둔다. |
| 43 | 수동 환기 후 베드 상태를 분류하는 기준 | classification, boundary, state | 수동 환기와 베드 온도만으로 자동 회복 상태를 분류하지 않는다. |
| 44 | 작업 기록 표본이 부족할 때 밸브 연결을 비교하는 기준 | state, comparison, other | 작업표·센서 시차가 다를 때 밸브 연결의 비교 범위를 제한한다. |
| 45 | 탱크 측정이 없는 제어기 명령의 해석 경계 | process, boundary, attribute | 탱크 수위·농도 없이 명령을 보충 결과로 해석하지 않는다. |
| 46 | 배수관 기록만 있을 때 관수 밸브 관계를 보류하는 기준 | part_of, state, other | 배수 기록만으로 특정 밸브의 부분 관계를 확정하지 않는다. |
| 47 | 수분 센서 공백에서 기상 예보 연결을 미확인으로 두는 상태 | state, boundary, other | 수분 관측 공백과 예보를 연결하지 않고 미확인 상태로 둔다. |
| 48 | 우회 배관에서 베드와 차광 모터 출처를 분리하는 절차 | process, other, role | 우회 운전 중 베드 기록과 모터 조작의 출처를 분리한다. |
| 49 | 순환팬 표본 부족 시 기상 예보 연결을 분류하지 않는 기준 | classification, boundary, state | 팬 표본과 예보를 한 운전 분류로 묶지 않는다. |
| 50 | 차광 모터 기록이 없는 베드 상태의 비교 범위 | state, comparison, other | 모터 기록 부재의 베드 상태를 같은 차광 상태로 비교하지 않는다. |
| 51 | 기상 예보 기록만 있을 때 함수율 변화를 해석하는 경계 | process, boundary, attribute | 예보 기록만으로 함수율 변화의 원인을 확정하지 않는다. |

각 새 text에는 대상 둘 이상, 구체적 관측·결측, 담당자의 결정, 잘못된 제어·점검·경보 방지 결과를 포함한다. updater는 old primary와 registry locator 10개, candidate의 비대상 7,790행 byte 보존을 확인하며 backup은 `A06_registry_before_v03_semantic_rewrite_42_51_2026-09-14.jsonl`이다.
