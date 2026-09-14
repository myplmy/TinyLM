# A06 v04 의미 재서술 사전 변경 계획 — locator 142~151 (2026-09-14)

- family: `S2-A06-T004: 도시 상수도 정수·배수 운영 — 다중 홉 관계 연결과 방향 보존`.
- precondition: source v04 `24ADD8425CD82392523A30606BB2BE48651E1C8EAF794B4CD3911375CBB074A6`, registry `CA04238AC35DAC01A7E08A0C52F52B0F78E1DA9F155EEF5B830607875F08E6E8`.
- source `concept`·`text`와 같은 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 142 | 우천 뒤 염소 주입과 여과지 조작 순서 | process, role, state | 우천 탁도 변화 뒤 운영자가 주입·여과지 상태에 따른 조작 순서를 정한다. |
| 143 | 교대 전 응집조 수압계 인계 절차 | part_of, process, role | 유입관 일부인 수압계를 교대 담당자가 확인한다. |
| 144 | 저부하 때 저수조 수위에 따른 배수문 단계 | process, classification, attribute | 낮은 유량·수위·문 위치를 조작 단계로 분류한다. |
| 145 | 정기 누수 점검 뒤 원수 유입 재개 절차 | process, state, function | 점검에서 누수 상태가 해제된 뒤 유입 기능을 재개한다. |
| 146 | 저부하 수위 변화에 따른 배수문·염소 주입 조절 절차 | process, role, comparison | 담당자가 전후 수위·탁도를 비교해 두 설비의 조절 순서를 정한다. |
| 147 | 고부하 응집조 유입관 수압 상태 기준 | part_of, state, attribute | 유입관 일부인 수압계·유입량으로 고부하 상태를 판단한다. |
| 148 | 원격 계측값에 따른 여과지 교대 인계 절차 | process, role, state | 원격값과 현장 상태를 교대 담당자가 확인한다. |
| 149 | 방류 경보 뒤 정수 펌프 점검 절차 | part_of, process, role | 방류 경로 경보 뒤 담당자가 펌프 점검을 시작한다. |
| 150 | 비상 유입 제한 단계 분류 | process, classification, attribute | 유량·수압·배수문 위치를 비상 제한 단계로 분류한다. |
| 151 | 센서 불일치 때 정수 공정 재가동 보류 절차 | process, state, function, other | 수질·수위·펌프 센서가 다르면 재가동 기능을 보류한다. |
