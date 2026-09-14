# A06 v05 의미 재서술 사전 변경 계획 — locator 2~11 (2026-09-14)

- family: `S2-A06-T005: 도시 상수도 정수·배수 운영 — 관계 충돌·우선순위·예외 통합`.
- precondition: source v05 `9225B988CBD630AE57691826C2A357D62741429213C2B439A796B44C1BFCEA9F`, registry `C3DC53094E6288C8C89A142CA1C789AE5341134273F6AB5BDA36891E34359363`.
- source `concept`·`text`와 같은 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 2 | 수질 계측값과 방류 기록이 다른 때의 판단 기준 | boundary, role, attribute | 두 기록은 같은 측정값이 아니며 담당자가 시각·수치를 나누어 판단한다. |
| 3 | 승인 전 여과지 우회 운전 기준 | boundary, comparison, state | 통상 운전과 우회 운전을 구분하고 승인 상태에 따라 우선순위를 정한다. |
| 4 | 방류 기록으로 정수 펌프 경보를 구분하는 절차 | process, boundary, role | 펌프 경보와 수압 센서 이상을 방류 기록·시각으로 구분한다. |
| 5 | 염소 주입과 배수문 조작의 교대 우선순위 | state, contrast, comparison | 엇갈린 두 조작 상태를 대비하고 어느 조작이 우선인지 정한다. |
| 6 | 누수 경보 때 수질 계측 보류 기준 | classification, boundary, function | 누수 대응·수질 확인을 분류하고 계측 기능의 보류 경계를 정한다. |
| 7 | 수동 전환 때 저수조·방류 기록의 우선순위 | process, state, contrast | 수동 전환 상태의 두 기록을 대비해 처리 순서를 정한다. |
| 8 | 누수 경보와 응집조 유입량의 통신 확인 절차 | boundary, role, attribute | 경보와 유입량을 같은 원인으로 합치지 않고 담당자가 통신 시각을 확인한다. |
| 9 | 임시 차단 중 배수문·염소 주입 분리 기준 | boundary, comparison, state | 차단 상태에서 두 조작의 적용 범위와 우선순위를 분리한다. |
| 10 | 교대 때 수압 기록과 펌프 지시를 구분하는 절차 | process, boundary, role | 교대 담당자가 수압 기록과 지시를 구분해 조작을 정한다. |
| 11 | 여과지 경보와 당직 지시의 유입 보류 기준 | state, contrast, comparison | 경보 상태와 당직 지시가 엇갈릴 때 유입 보류의 우선순위를 정한다. |
