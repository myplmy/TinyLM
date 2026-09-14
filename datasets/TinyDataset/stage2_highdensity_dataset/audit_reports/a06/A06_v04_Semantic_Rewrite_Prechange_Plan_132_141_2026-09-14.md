# A06 v04 의미 재서술 사전 변경 계획 — locator 132~141 (2026-09-14)

- family: `S2-A06-T004: 도시 상수도 정수·배수 운영 — 다중 홉 관계 연결과 방향 보존`.
- precondition: source v04 `33FB0F467F8C62EFFED35E245CEA1BA13049A88D8C0E492998D096A8BBD19862`, registry `2ED805F45816830CEF320C5594B3077C829BB072FD562D0A4A370CF5FC5BFCFA`.
- source `concept`·`text`와 같은 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 132 | 임시 차단 뒤 저수조 수위 회복 단계 | process, classification, attribute | 수위·문 위치를 회복 단계로 분류한다. |
| 133 | 누수 복구 뒤 유입 밸브 기능 확인 절차 | process, state, function | 누수 경보 해제 상태에서 밸브 기능을 확인한다. |
| 134 | 배수문 변경 뒤 저수조 수위 조절 기준 | process, role, comparison, other | 조절 범위 자료가 부족하면 담당자가 문 조작을 보류한다. |
| 135 | 수압계와 방류 기록의 응집조 유입 상태 기준 | part_of, state, attribute | 유입관 일부의 수압계와 방류 기록을 대조한다. |
| 136 | 승인 전 여과지와 저수조 조작 점검 절차 | process, role, state | 승인 전 담당자가 여과지·저수조 상태와 조작 순서를 확인한다. |
| 137 | 승인된 방류 기록의 펌프 점검 절차 | part_of, process, role | 방류 경로 기록 승인 뒤 담당자가 펌프 점검을 시작한다. |
| 138 | 교대 당직자의 원수 유입 점검 주기 | process, classification, attribute | 유량·수압을 당직 점검 주기로 분류한다. |
| 139 | 계측값 정상화 뒤 저수조 밸브 상태 확인 | process, state, function | 계측값 정상화 뒤 밸브 상태와 유입 기능을 확인한다. |
| 140 | 새벽 탁도 상승 시 배수문 조절 기준 | process, role, comparison | 당직자가 탁도 상승과 수위를 비교해 문 조작을 정한다. |
| 141 | 야간 방류 수질과 응집조 유입 상태 기준 | part_of, state, attribute | 야간 방류 수질·유입량·펌프 압력으로 상태를 판단한다. |
