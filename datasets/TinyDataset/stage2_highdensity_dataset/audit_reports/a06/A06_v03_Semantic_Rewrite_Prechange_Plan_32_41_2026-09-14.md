# A06 v03 의미 재서술 사전 변경 계획 — locator 32~41 (2026-09-14)

- precondition: source v03 `644865F9FD3A03AB4B2BFBDFC60C1DD1E8BFA2E17CD0A1DB1D6011E50F70574C`, registry `A0F9A903A1EEF8C47872D0C5AFE8E603C5412CEC1814237D0426A7F8F74278E8`.
- 허용 변경은 v03 line 32~41의 source `concept`·`text`와 같은 registry locator `primary` 10개뿐이다. relations, `other_type`, registry 비-primary field·행 순서·비대상 바이트는 그대로다.

| locator | 새 concept | relations | 의미 판단 |
|---|---|---|---|
| 32 | 작업 기록이 없을 때 압력 조절 범위를 비교하는 기준 | state, comparison, other | 작업자 기록 없이 바뀐 압력값은 이전 조정과 같은 상태로 비교하지 않는다. |
| 33 | 비상 전환 중 양액 탱크와 제어기 연결의 해석 범위 | process, boundary, attribute, other | 비상 전원 뒤 한 차례만 들어온 수위·명령 표본의 해석 경계를 쓴다. |
| 34 | 배수관 표본이 부족할 때 압력 조절 연결을 보류하는 기준 | part_of, state, other | 유량 표본 부재에서 압력 조절기를 배수 경로의 일부로 확정하지 않는다. |
| 35 | 수분 센서 기록이 없는 구역의 기상 예보 연결 상태 | state, boundary, other | 중간 수분 관측이 없으면 예보를 구역 상태의 원인으로 연결하지 않는다. |
| 36 | 베드 기록으로 차광 모터 원인을 추정하지 않는 절차 | process, other, role | 베드 기록만으로 차광 작동의 출처를 정하지 않고 운영자가 원인을 확인한다. |
| 37 | 순환팬 기록 공백에서 압력 조절 상태를 분류하는 기준 | classification, boundary, state | 순환팬 기록 공백의 압력 변화를 자동 환기 상태로 분류하지 않는다. |
| 38 | 차광 모터와 베드 기록이 엇갈릴 때의 비교 기준 | state, comparison, other | 장치·베드 식별값이 엇갈릴 때 같은 제어 상태로 비교하지 않는다. |
| 39 | 기상 예보 표본이 부족할 때 제어기 연결을 보류하는 절차 | process, boundary, attribute | 예보 표본만으로 제어기 명령의 원인을 단정하지 않는다. |
| 40 | 관수 밸브 기록이 없을 때 배수관 부분 관계를 보류하는 기준 | part_of, state, other | 밸브 기록이 없는 유량 변화를 특정 관수 경로의 일부로 확정하지 않는다. |
| 41 | 제어기 기록만 있을 때 탱크 상태를 확정하지 않는 기준 | state, boundary, other | 제어기 로그만으로 탱크의 회복 상태를 확정하지 않는다. |

새 text는 모두 관찰 결측, 판단 주체, 보류·분리 조치, 오판 방지 결과를 독립적으로 포함한다. 반영 시 registry backup `A06_registry_before_v03_semantic_rewrite_32_41_2026-09-14.jsonl`과 candidate의 target 10·비대상 7,790행 byte 보존을 확인한다.
