# A06 v04 의미 재서술 사전 변경 계획 — locator 22~31 (2026-09-14)

- family: `S2-A06-T004: 도시 상수도 정수·배수 운영 — 다중 홉 관계 연결과 방향 보존`.
- precondition: source v04 `3762C5AC0C9CBB33FB66B030ECCD0AC4D5416071140FD3C9DA8E34DA8BF8B9D7`, registry `22EF52A79CCA2B723C30254BF11B24DC9F0E7772594A65DE795B4B76289BAA2B`.
- source `concept`·`text`와 동일 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 22 | 우천 뒤 염소 주입기와 여과지 상태를 확인하는 절차 | process, role, state | 우천 뒤 여과지 탁도와 염소 주입 상태를 운영자가 확인한다. |
| 23 | 응집조 유입관과 수압 센서의 교대 점검 순서 | part_of, process, role | 교대 때 유입관의 일부인 센서부터 확인하고 응집조 조치를 잇는다. |
| 24 | 저수조 수위에 따른 배수문 저부하 운전 분류 기준 | process, classification, attribute | 수위값으로 저부하 운전 단계를 분류한다. |
| 25 | 누수 경보 뒤 원수 유입을 유지할지 결정하는 절차 | process, state, function | 누수 경보 뒤 감시기·수압값을 확인해 유입 기능을 유지하거나 줄인다. |
| 26 | 저부하 운전에서 배수문·저수조·염소 주입을 조정하는 절차 | process, role, comparison | 낮아진 수위와 주입량을 비교해 운영자가 조작 순서를 고른다. |
| 27 | 고부하 때 수압 센서와 응집조 유입 상태를 대조하는 기준 | part_of, state, attribute | 유입관 일부인 센서의 압력·유입량으로 고부하 상태를 판단한다. |
| 28 | 원격 판독으로 여과지와 염소 주입기를 점검하는 절차 | process, role, state | 원격 기록의 여과지·주입기 상태를 담당자가 확인한다. |
| 29 | 방류 경보 뒤 정수 펌프 점검을 인계하는 절차 | part_of, process, role | 방류 경로 기록을 확인한 뒤 펌프 점검 책임을 인계한다. |
| 30 | 비상 전환 중 원수 유입과 배수문 조작을 분류하는 기준 | process, classification, attribute | 비상 전환에서 유입량·배수문 위치를 단계별로 분류한다. |
| 31 | 복구 뒤 수질 측정과 저수조 유입을 이어 가는 절차 | process, state, function | 수질 상태가 회복된 뒤 유입 기능을 다시 시작한다. |

각 새 text에는 구체 대상, 관찰 계기, 판단 주체, 결과 제한을 독립적으로 넣는다. updater는 target 10과 비대상 7,790행 byte 보존을 검증하고, 적용 전 registry 행은 `A06_registry_before_v04_semantic_rewrite_22_31_2026-09-14.jsonl`에 보관한다.
