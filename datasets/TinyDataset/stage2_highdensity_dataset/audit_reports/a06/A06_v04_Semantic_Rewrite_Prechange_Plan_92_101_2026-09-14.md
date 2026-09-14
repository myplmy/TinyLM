# A06 v04 의미 재서술 사전 변경 계획 — locator 92~101 (2026-09-14)

- family: `S2-A06-T004: 도시 상수도 정수·배수 운영 — 다중 홉 관계 연결과 방향 보존`.
- precondition: source v04 `BDBE7A7400A343B5B321F371BE9E8BFDE0D27958ACCD3299AE5DED3FF790CFCC`, registry `2C3787BB16DB3C5A1471C2DEF2A54309F735A875AE72C6C548961F12CBFEFBFE`.
- source `concept`·`text`와 같은 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 92 | 예방 점검 때 원수 유입량을 비교하는 기준 | process, role, comparison | 당직자가 전후 유입량을 비교해 점검 간격을 정한다. |
| 93 | 방류 기록을 반영한 정수 펌프 상태 기준 | part_of, state, attribute | 방류 기록과 펌프 압력값으로 펌프 상태를 판단한다. |
| 94 | 염소 주입 변화 뒤 여과지 점검 절차 | process, role, state | 주입량 변화 후 담당자가 여과지 상태를 확인한다. |
| 95 | 누수 경보 뒤 응집조 수압 점검 절차 | part_of, process, role | 누수 경보와 수압 변화를 연결해 담당자가 유입 점검을 고른다. |
| 96 | 저수조 수위에 따른 배수문 인계 분류 | process, classification, attribute | 수위와 문 위치를 인계 수준으로 분류한다. |
| 97 | 누수 경보 해제 뒤 유입 밸브 인계 절차 | process, state, function | 경보 해제 상태에서 밸브 기능을 인계한다. |
| 98 | 장기 수위 추이에 따른 배수문 조절 절차 | process, role, comparison | 운영자가 장기 수위와 기준 수위를 비교해 배수문을 조절한다. |
| 99 | 수압 회복 뒤 응집조 유입 상태 기준 | part_of, state, attribute | 유입관 수압계가 회복된 상태에서 응집조 유입 상태를 판단한다. |
| 100 | 수동 전환 때 여과지와 염소 주입기 점검 | process, role, state, other | 수동 전환 상태에서 담당자가 설비 상태를 확인하고 후속 검증 누락을 남긴다. |
| 101 | 자동 복귀 뒤 정수 펌프 점검 절차 | part_of, process, role | 자동 복귀가 방류 기록과 펌프 점검 순서에 미치는 범위를 판단한다. |
