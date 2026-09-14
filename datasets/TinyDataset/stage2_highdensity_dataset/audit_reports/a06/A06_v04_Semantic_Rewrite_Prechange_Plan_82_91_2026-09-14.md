# A06 v04 의미 재서술 사전 변경 계획 — locator 82~91 (2026-09-14)

- family: `S2-A06-T004: 도시 상수도 정수·배수 운영 — 다중 홉 관계 연결과 방향 보존`.
- precondition: source v04 `3FECE1522628A24C95E3ABDE58E852D1B0030213416AED14478C02EDB874C6B5`, registry `7AF25355D769D7D42A7480F4C91E8032A5DBA40B303708FEAB48C47560EDF540`.
- source `concept`·`text`와 같은 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 82 | 우천 뒤 염소 주입과 여과지 점검 순서 | process, role, state | 우천 탁도 변화 뒤 담당자가 염소 주입과 여과지 상태의 점검 순서를 정한다. |
| 83 | 교대 전 응집조 수압 점검 절차 | part_of, process, role, other | 유입관 수압계 기록의 출처가 불분명하면 교대 담당자가 인계를 보류한다. |
| 84 | 저수조 수위에 따른 배수문 경보 단계 | process, classification, attribute | 수위와 문 위치를 경보 단계로 분류해 조작 제한을 정한다. |
| 85 | 누수 복구 뒤 원수 유입 점검 절차 | process, state, function | 누수 경보가 해제된 뒤 유입 밸브 기능을 단계적으로 재개한다. |
| 86 | 저부하 때 배수문과 염소 주입 순서 | process, role, comparison | 담당자가 낮은 유량과 탁도를 비교해 조작 순서를 고른다. |
| 87 | 고부하 때 응집조 유입 상태 판단 | part_of, state, attribute | 유입관 수압계와 유입량이 높을 때 담당자가 응집조 상태를 판단한다. |
| 88 | 여과지와 염소 주입기의 원격 점검 절차 | process, role, state | 원격 감시값이 다르면 운영자가 설비 상태를 확인한 뒤 조작을 보류한다. |
| 89 | 방류 기록에 따른 정수 펌프 점검 절차 | part_of, process, role | 방류 경로 기록이 펌프 점검의 선행 조건인지 담당자가 판정한다. |
| 90 | 비상 유입 제한 시 당직 점검 기준 | process, classification, attribute | 유입량·수압을 점검 주기로 분류해 비상 인계 범위를 정한다. |
| 91 | 복구 뒤 정수 공정 재가동 절차 | process, state, function | 수질·저수조·펌프 상태가 맞을 때 담당자가 재가동 기능을 허용한다. |
