# A06 v04 의미 재서술 사전 변경 계획 — locator 122~131 (2026-09-14)

- family: `S2-A06-T004: 도시 상수도 정수·배수 운영 — 다중 홉 관계 연결과 방향 보존`.
- precondition: source v04 `624466A15ECB72DE0F721C567F385510EC4320E7B6E1A322751878ED9B817046`, registry `CAAD1045920530DD48924FB83EF933CE3AE9778FE55D401700CE5212BA36012C`.
- source `concept`·`text`와 같은 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 122 | 예방 점검 때 배수문과 저수조 수위를 비교하는 절차 | process, role, comparison | 담당자가 배수문 위치와 수위의 전후 변화를 비교한다. |
| 123 | 응집조 유입관 수압 상태 기준 | part_of, state, attribute | 유입관 일부인 수압계와 유입량으로 상태를 판단한다. |
| 124 | 여과지 압력 변화 뒤 염소 주입 점검 절차 | process, role, state | 압력차 변화 뒤 운영자가 주입기 상태와 조작을 확인한다. |
| 125 | 방류 수질 이상 때 정수 펌프 점검 절차 | part_of, process, role | 방류 경로 수질 기록 이상 뒤 담당자가 펌프를 점검한다. |
| 126 | 배수문 전환 때 원수 유입 인계 분류 | process, classification, attribute | 유입량·문 위치를 인계 단계로 분류한다. |
| 127 | 수질 경보 때 저수조 유입 제한 절차 | process, state, function | 수질 경보 상태에서 밸브의 유입 기능을 제한한다. |
| 128 | 장기 유입량 추이에 따른 당직 점검 절차 | process, role, comparison | 당직자가 장기 유입량을 기준값과 비교해 점검 주기를 정한다. |
| 129 | 펌프 압력과 방류 수질을 대조하는 기준 | part_of, state, attribute | 공정 일부인 펌프의 압력과 방류 수질로 상태를 판단한다. |
| 130 | 수동 전환 뒤 여과지 압력차 확인 절차 | process, role, state | 수동 전환 상태 뒤 담당자가 압력차를 확인한다. |
| 131 | 자동 복귀 뒤 누수 감시기와 수압계 점검 절차 | part_of, process, role | 자동 복귀 뒤 유입관 일부인 수압계와 누수 감시기를 점검한다. |
