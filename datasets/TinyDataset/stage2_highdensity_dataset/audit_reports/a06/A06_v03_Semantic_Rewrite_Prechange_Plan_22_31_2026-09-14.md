# A06 v03 의미 재서술 사전 변경 계획 — locator 22~31 (2026-09-14)

- precondition: source v03 `A2580C3D3E922C181CB87BABF4777AF630DB6EDF3BCBD0C1233755F28806C2F8`, registry `1906FF38D8777E21C9D01CCE7B7EEF4291BB3B4DF9D9AEB1309698BC29067840`.
- 대상: v03 physical line 22~31 source `concept`·`text`, 같은 locator registry `primary` 10개. relations·`other_type`·registry 비-primary field·행 순서·비대상 바이트는 보존한다.
- 제외: v01, v02 잔여 행, 다른 영역, package `train/val`, manifest, 중앙 원장, checkpoint, 공용 감사기.

| locator | 새 concept | 보존 relations | 핵심 상황 |
|---|---|---|---|
| 22 | 배수관 입력이 끊겼을 때 관수 밸브 관계를 제한하는 기준 | part_of, state, other | 유량값 부재와 밸브 시각만으로 배수 흐름의 부분 관계를 확정하지 않는다. |
| 23 | 새벽 수분 기록과 기상 예보의 연결을 보류하는 상태 | state, boundary, other | 새벽 판독과 강수 알림 사이 중간 측정이 없을 때 원인 연결을 보류한다. |
| 24 | 베드 표본이 부족할 때 작업 기록 출처를 확인하는 절차 | process, other, role | 베드 경보와 작업 기록의 출처를 운영자가 분리해 확인한다. |
| 25 | 순환팬 기록이 없는 압력 조절기의 상태 분류 | classification, boundary, state | 팬 기록 부재의 압력 변화를 환기 상태로 분류하지 않는다. |
| 26 | 차광 모터 기록만 있을 때 베드 상태 비교를 보류하는 기준 | state, comparison, other | 모터 기록만으로 베드 온도 변화를 같은 상태로 비교하지 않는다. |
| 27 | 기상 예보 공백에서 함수율 값을 해석하는 경계 | process, boundary, attribute | 예보 공백의 함수율을 외부 기상 원인으로 연결하지 않는다. |
| 28 | 정기 운전 중 밸브와 배수관의 부분 관계 보류 | part_of, state, other | 정기 운전의 동시 개입을 분리할 수 없을 때 배관 부분 관계를 보류한다. |
| 29 | 제어기 표본 부족 시 환기창 연결을 미확인 상태로 두는 기준 | state, boundary, other | 제어기와 환기창의 연결을 검증 전까지 미확인 상태로 둔다. |
| 30 | 압력 조절기 기록이 없을 때 작업 승인 출처를 보류하는 절차 | process, other, role | 조절기 기록 부재에서 작업 승인 출처를 단정하지 않는다. |
| 31 | 환기창 기록만 있을 때 베드 상태를 분류하지 않는 기준 | classification, boundary, state | 환기창 기록만으로 베드의 회복·비회복 상태를 분류하지 않는다. |

모든 새 text는 최소 두 대상, 구체적 결측·관측 계기, 운영자·담당자의 판단, 잘못된 제어·경보·점검을 막는 결과를 직접 쓴다. registry backup은 반영 시 `A06_registry_before_v03_semantic_rewrite_22_31_2026-09-14.jsonl`에 저장하며 updater가 old primary·10 target·비대상 7,790행 byte 보존을 검증한다.
