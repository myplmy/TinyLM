# A06 v04 의미 재서술 사전 변경 계획 — locator 62~71 (2026-09-14)

- family: `S2-A06-T004: 도시 상수도 정수·배수 운영 — 다중 홉 관계 연결과 방향 보존`.
- precondition: source v04 `CB52DD07CBB2B12F44B237225062BEC446909B9A11E347A4BEDF4A454A7CC7B5`, registry `052846F5D7CA0BC6DEF8EEBD9A9837E9366E2B81684530E2FCED0AF01B02C167`.
- source `concept`·`text`와 동일 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 62 | 배수문 점검 결과와 저수조 수위를 비교하는 절차 | process, role, comparison | 당직자가 배수문·수위 기록을 비교해 조작을 고른다. |
| 63 | 교대 시 수압 센서와 응집조 유입 상태를 인계하는 기준 | part_of, state, attribute | 유입관 일부인 센서값과 응집조 상태를 교대 때 확인한다. |
| 64 | 여과지 판독 뒤 저부하 염소 주입을 조정하는 절차 | process, role, state | 저부하 상태에서 여과지·주입기 상태를 조정한다. |
| 65 | 방류 수질 경보 뒤 정수 펌프 점검 순서를 확인하는 절차 | part_of, process, role | 방류 경보와 펌프 계측값을 잇는 점검 순서를 확인한다. |
| 66 | 대체 배수 경로 기록이 없을 때 유입과 배수문 순서를 보류하는 기준 | process, classification, attribute, other | 대체 경로 기록 결측이면 조작 단계를 확정하지 않는다. |
| 67 | 수질 기준 이탈 때 저수조 유입을 제한하는 절차 | process, state, function | 수질 상태가 기준 밖이면 유입 밸브 기능을 제한한다. |
| 68 | 장기 원수 유입 기록으로 당직 조치를 비교하는 절차 | process, role, comparison | 장기 유입량·압력값을 비교해 당직 조치를 고른다. |
| 69 | 펌프 경보와 방류 수질 상태를 대조하는 기준 | part_of, state, attribute | 펌프 압력 경보와 방류 수질 상태를 대조한다. |
| 70 | 수동 전환 때 염소 주입기와 여과지 상태를 인계하는 절차 | process, role, state | 수동 전환의 설비 상태와 책임을 인계한다. |
| 71 | 자동 복귀 뒤 응집조·수압 센서·누수 감시기 점검 순서 | part_of, process, role | 자동 복귀 뒤 세 장비의 확인 순서를 유지한다. |

각 새 text에는 구체 대상, 관찰 계기, 판단 주체, 결과 제한을 독립적으로 넣는다. updater는 target 10과 비대상 7,790행 byte 보존을 검증하고, 적용 전 registry 행은 `A06_registry_before_v04_semantic_rewrite_62_71_2026-09-14.jsonl`에 보관한다.
