# A06 v04 의미 재서술 사전 변경 계획 — locator 42~51 (2026-09-14)

- family: `S2-A06-T004: 도시 상수도 정수·배수 운영 — 다중 홉 관계 연결과 방향 보존`.
- precondition: source v04 `96CA5EF252C209485044EB174F941B5EA5F87C786168FCC39A5956BFD066B7B1`, registry `5115B8ADBADD58E2CBDEB317DE1AC209052B8DB8FC0094EBEA85729176D9831B`.
- source `concept`·`text`와 동일 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 42 | 원수 유입량에 따른 임시 차단 단계를 분류하는 기준 | process, classification, attribute | 유입량·수압을 기준으로 임시 차단 단계를 분류한다. |
| 43 | 수질 회복 뒤 저수조 유입을 재개하는 절차 | process, state, function | 수질이 회복된 뒤 저수조 유입 기능을 다시 시작한다. |
| 44 | 당직표 확인 뒤 원수 유입 조치를 비교하는 절차 | process, role, comparison | 당직자가 유입량·수압을 비교해 조치를 선택한다. |
| 45 | 정수 펌프와 방류 기록을 응집조 상태와 구분하는 기준 | part_of, state, attribute | 펌프·방류 계측값과 응집조 유입 상태를 구분한다. |
| 46 | 염소 주입 승인 뒤 여과지와 원수 유입을 조정하는 절차 | process, role, state | 승인 뒤 운영자가 주입·여과·유입 상태를 조정한다. |
| 47 | 응집조 점검 승인 뒤 수압 센서 상태를 확인하는 절차 | part_of, process, role | 유입관 일부인 센서 상태를 점검 승인 뒤 확인한다. |
| 48 | 저수조 수위와 배수문 조작 주기를 분류하는 기준 | process, classification, attribute | 수위·배수문 변화를 관찰 주기로 분류한다. |
| 49 | 누수 감시기 식별값 충돌 시 원수 유입을 보류하는 절차 | process, state, function, other | 식별값 상충이면 유입 기능 전환을 보류한다. |
| 50 | 새벽 배수문과 저수조 수위를 비교하는 절차 | process, role, comparison | 새벽 당직자가 배수문·수위값을 비교해 조작을 고른다. |
| 51 | 야간 수압 센서·응집조·방류 기록 상태를 대조하는 기준 | part_of, state, attribute | 야간의 센서·유입·방류 계측값을 대조한다. |

각 새 text에는 구체 대상, 관찰 계기, 판단 주체, 결과 제한을 독립적으로 넣는다. updater는 target 10과 비대상 7,790행 byte 보존을 검증하고, 적용 전 registry 행은 `A06_registry_before_v04_semantic_rewrite_42_51_2026-09-14.jsonl`에 보관한다.
