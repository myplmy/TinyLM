# A06 v04 의미 재서술 사전 변경 계획 — locator 72~81 (2026-09-14)

- family: `S2-A06-T004: 도시 상수도 정수·배수 운영 — 다중 홉 관계 연결과 방향 보존`.
- precondition: source v04 `F1AF78C6F813CD84A72FCC1E4D9A2E2C188643403FBEF1E44984A06B3D9FF2E3`, registry `606E10F2E441630BEDD7B95D26E0EBE1B4ED9D20CCE9EEBD33C6121000DB7FDD`.
- source `concept`·`text`와 동일 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 72 | 저수조 수위 경보에서 배수문 차단 단계를 고르는 기준 | process, classification, attribute | 수위 경보·문 위치로 관찰·제한·차단 단계를 고른다. |
| 73 | 누수 복구 뒤 원수 유입을 단계적으로 재개하는 절차 | process, state, function | 누수 상태가 해제된 뒤 유입 기능을 단계적으로 재개한다. |
| 74 | 배수문 우회 조정과 저수조 수위를 비교하는 절차 | process, role, comparison | 우회 조정의 문 위치·수위를 운영자가 비교한다. |
| 75 | 수압 센서와 방류 기록이 어긋날 때 응집조 유입 상태를 보류하는 기준 | part_of, state, attribute | 센서·방류 기록이 다르면 응집조 유입 상태 판단을 보류한다. |
| 76 | 승인 전 여과지·염소 주입·저수조 상태를 확인하는 절차 | process, role, state | 승인 전 세 설비 상태와 조작 책임을 확인한다. |
| 77 | 방류 승인 뒤 정수 펌프 점검을 시작하는 절차 | part_of, process, role | 방류 경로 기록이 승인된 뒤 펌프 점검을 시작한다. |
| 78 | 원수 유입량에 따른 당직 점검 주기를 분류하는 기준 | process, classification, attribute | 유입량·수압을 관찰 주기로 분류한다. |
| 79 | 수질 장기 추이를 확인한 뒤 저수조 유입을 조절하는 절차 | process, state, function | 장기 수질 추이 후 유입 밸브 기능을 조절한다. |
| 80 | 새벽 원수 유입량과 여과지 탁도를 비교하는 절차 | process, role, comparison | 새벽 당직자가 유입량·탁도를 비교해 점검 순서를 정한다. |
| 81 | 야간 정수 펌프·방류 기록·응집조 상태를 대조하는 기준 | part_of, state, attribute | 야간 공정의 펌프·방류·유입 계측값을 대조한다. |

각 새 text에는 구체 대상, 관찰 계기, 판단 주체, 결과 제한을 독립적으로 넣는다. updater는 target 10과 비대상 7,790행 byte 보존을 검증하고, 적용 전 registry 행은 `A06_registry_before_v04_semantic_rewrite_72_81_2026-09-14.jsonl`에 보관한다.
