# A06 v04 의미 재서술 사전 변경 계획 — locator 52~61 (2026-09-14)

- family: `S2-A06-T004: 도시 상수도 정수·배수 운영 — 다중 홉 관계 연결과 방향 보존`.
- precondition: source v04 `B53B53E5E032778669A07A373FAE9B7D5972CE1725D643D934F812C58581DA3D`, registry `2F50E247C934074AC2CFB1A08323AC3EFAF736C3E57640F139AD6B03C9E4CB02`.
- source `concept`·`text`와 동일 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 52 | 우천 뒤 여과지와 염소 주입기 상태를 확인하는 절차 | process, role, state | 우천 뒤 탁도·주입 상태를 운영자가 확인한다. |
| 53 | 방류 기록 뒤 정수 펌프 점검을 인계하는 절차 | part_of, process, role | 방류 경로의 기록을 확인한 뒤 펌프 점검을 인계한다. |
| 54 | 원수 유입 변화에 따른 당직 점검 단계를 분류하는 기준 | process, classification, attribute | 유입량·수압에 따라 당직 점검 단계를 분류한다. |
| 55 | 수질 측정 뒤 저수조 유입을 정기 운전으로 재개하는 절차 | process, state, function | 기준 수질이 확인되면 유입 기능을 재개한다. |
| 56 | 저부하 때 당직표·유입량·여과지 판독을 비교하는 절차 | process, role, comparison | 낮은 유입량과 탁도·당직표를 비교해 순서를 정한다. |
| 57 | 고부하에서 정수 펌프와 방류 상태를 대조하는 기준 | part_of, state, attribute | 펌프 압력·방류 수질로 고부하 상태를 판단한다. |
| 58 | 원격 판독으로 염소 주입기와 여과지 상태를 확인하는 절차 | process, role, state | 원격 기록의 두 설비 상태를 담당자가 확인한다. |
| 59 | 응집조 판독 뒤 수압 센서 점검을 인계하는 절차 | part_of, process, role | 유입관 일부인 센서 점검을 교대 담당자에게 잇는다. |
| 60 | 비상 전환 중 저수조 수위와 배수문 조작을 분류하는 기준 | process, classification, attribute | 전환 시 수위·배수문 위치를 단계별로 분류한다. |
| 61 | 복구 뒤 누수 감시기와 원수 유입 상태를 확인하는 절차 | process, state, function | 복구 후 누수·유입 상태를 확인해 유입 기능을 재개한다. |

각 새 text에는 구체 대상, 관찰 계기, 판단 주체, 결과 제한을 독립적으로 넣는다. updater는 target 10과 비대상 7,790행 byte 보존을 검증하고, 적용 전 registry 행은 `A06_registry_before_v04_semantic_rewrite_52_61_2026-09-14.jsonl`에 보관한다.
