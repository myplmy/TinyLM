# A06 v04 의미 재서술 사전 변경 계획 — locator 102, 104~111 (2026-09-14)

- family: `S2-A06-T004: 도시 상수도 정수·배수 운영 — 다중 홉 관계 연결과 방향 보존`.
- precondition: source v04 `BD8E611CC8D654ED116CDB96CFEEDB532EA105485F6523D83C215423AA6CC411`, registry `43C3434AAC9E2BD16368E1E233CF969780EF1E2C905D1DBACE4CEFCCB2FF0388`.
- locator 103은 기존 text가 구체 계측값·상태·기능·제한을 이미 독립적으로 설명하고 audit queue에 없으므로 보존한다. 나머지 source `concept`·`text`와 같은 registry locator의 `primary` 9개만 바꾼다.
- relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 102 | 임시 차단 시 원수 유입 인계 기준 | process, classification, attribute | 유입량·수압을 인계 분류해 차단 해제 조건을 정한다. |
| 104 | 저부하 원수 유입 조절 절차 | process, role, comparison | 담당자가 유량·탁도 비교로 저부하 조작을 고른다. |
| 105 | 정수 펌프와 응집조 상태를 대조하는 기준 | part_of, state, attribute | 공정 일부인 펌프와 응집조의 계측값을 대조한다. |
| 106 | 승인 전 염소 주입과 원수 유입 점검 절차 | process, role, state | 승인 전 담당자가 설비 상태와 조작 순서를 확인한다. |
| 107 | 응집조 유입관 수압계의 승인 후 점검 절차 | part_of, process, role | 승인 뒤 유입관 일부인 수압계를 담당자가 점검한다. |
| 108 | 저수조 수위에 따른 배수문 점검 주기 | process, classification, attribute | 수위·문 위치를 짧은·긴 점검 주기로 분류한다. |
| 109 | 누수 경보 뒤 원수 유입 제한 절차 | process, state, function | 누수 경보 상태에서 유입 밸브 기능을 제한한다. |
| 110 | 새벽 배수문 조절과 염소 주입 비교 | process, role, comparison | 당직자가 새벽 수위·탁도와 조작량을 비교한다. |
| 111 | 야간 응집조 유입 상태 점검 기준 | part_of, state, attribute | 야간에 유입관 일부의 계측값으로 응집조 상태를 판단한다. |
