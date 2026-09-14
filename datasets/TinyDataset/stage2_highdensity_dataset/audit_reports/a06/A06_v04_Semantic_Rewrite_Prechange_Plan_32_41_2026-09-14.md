# A06 v04 의미 재서술 사전 변경 계획 — locator 32~41 (2026-09-14)

- family: `S2-A06-T004: 도시 상수도 정수·배수 운영 — 다중 홉 관계 연결과 방향 보존`.
- precondition: source v04 `81020EEE552B840127F2FCFC8AC509418C0E34A25A52FED33B7F0ECF67DE4C3A`, registry `801AEF058AF44B37782C96341B8088A56CDE6AE8858DCEB8FDD19B387C5BD8C9`.
- source `concept`·`text`와 동일 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 32 | 예방 점검에서 원수 유입량을 비교하는 절차 | process, role, comparison, other | 부분 표본 한계를 남기고 당직자가 유입량·압력을 비교한다. |
| 33 | 정수 펌프와 방류 수질 기록을 대조하는 기준 | part_of, state, attribute | 펌프 압력과 방류 계측값으로 상태를 판단한다. |
| 34 | 염소 주입기 판독 뒤 여과지 우회 운전을 승인하는 절차 | process, role, state | 주입기·여과지 상태를 확인해 운영자가 우회 운전을 결정한다. |
| 35 | 응집조 누수 경보와 수압 센서 점검 순서 | part_of, process, role | 응집조 유입관·수압 센서·누수 감시기를 순서대로 점검한다. |
| 36 | 저수조 수위 변화에 따른 배수문 조작 단계를 분류하는 기준 | process, classification, attribute | 수위값과 배수문 위치를 조작 단계로 분류한다. |
| 37 | 누수 경보 중 원수 유입을 제한하는 절차 | process, state, function | 누수 상태에서는 유입 밸브 기능을 제한한다. |
| 38 | 장기 수위 기록으로 배수문 조작을 비교하는 절차 | process, role, comparison | 장기 수위·개방량을 운영자가 비교해 조작을 고른다. |
| 39 | 수압 센서 변화와 응집조 유입 상태를 대조하는 기준 | part_of, state, attribute | 센서 압력값과 유입량으로 응집조 상태를 판단한다. |
| 40 | 수동 전환 때 여과지와 염소 주입기를 기록하는 절차 | process, role, state | 수동 전환 주체·시각·설비 상태를 기록한다. |
| 41 | 자동 복귀 뒤 방류·펌프·수질 점검 순서를 확인하는 절차 | part_of, process, role | 방류·펌프·계측기의 점검 순서와 담당 조치를 확인한다. |

각 새 text에는 구체 대상, 관찰 계기, 판단 주체, 결과 제한을 독립적으로 넣는다. updater는 target 10과 비대상 7,790행 byte 보존을 검증하고, 적용 전 registry 행은 `A06_registry_before_v04_semantic_rewrite_32_41_2026-09-14.jsonl`에 보관한다.
