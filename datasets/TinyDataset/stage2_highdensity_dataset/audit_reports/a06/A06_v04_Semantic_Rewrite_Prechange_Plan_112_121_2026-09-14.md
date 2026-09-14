# A06 v04 의미 재서술 사전 변경 계획 — locator 112~121 (2026-09-14)

- family: `S2-A06-T004: 도시 상수도 정수·배수 운영 — 다중 홉 관계 연결과 방향 보존`.
- precondition: source v04 `7F973FE22EB12CBFB8976D29F341A14E5833156D6E8FCF5BA5C8F2C3601CDC8D`, registry `42361B143BDBA848900453A96146F298E18F0C856682C9EDFF3EBB798B047F6A`.
- source `concept`·`text`와 같은 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 112 | 우천 때 여과지와 염소 주입기 점검 절차 | process, role, state | 운영자가 우천 탁도 변화 뒤 설비 상태와 조작 순서를 정한다. |
| 113 | 교대 전 방류 기록과 정수 펌프 인계 절차 | part_of, process, role | 방류 경로 기록과 펌프 값을 교대 담당자가 함께 확인한다. |
| 114 | 우회 배수 시 원수 유입 인계 분류 | process, classification, attribute | 유입량·수압을 인계 단계로 분류한다. |
| 115 | 수질 회복 뒤 저수조 유입 재개 절차 | process, state, function | 수질 상태가 회복된 뒤 밸브 기능을 단계적으로 재개한다. |
| 116 | 저부하 때 원수 유입과 여과지 점검 순서 | process, role, comparison | 당직자가 낮은 유량·탁도를 비교해 점검 순서를 선택한다. |
| 117 | 고부하 정수 펌프의 방류 상태 기준 | part_of, state, attribute, other | 방류 유량이 빠진 때에는 공정 일부인 펌프·방류 상태를 확정하지 않는다. |
| 118 | 원격 여과지와 염소 주입기 상태 점검 | process, role, state | 원격 계측값이 어긋나면 운영자가 현장 점검 여부를 고른다. |
| 119 | 장기 수압 추이에 따른 응집조 점검 절차 | part_of, process, role | 유입관 일부인 수압계의 장기 추이로 담당자가 점검 시점을 고른다. |
| 120 | 비상 배수문 전환 시 저수조 인계 기준 | process, classification, attribute | 수위·문 위치를 비상 인계 단계로 분류한다. |
| 121 | 복구 뒤 누수 경보와 원수 유입 재개 절차 | process, state, function | 경보 해제와 수압 회복 뒤 유입 기능을 재개한다. |
