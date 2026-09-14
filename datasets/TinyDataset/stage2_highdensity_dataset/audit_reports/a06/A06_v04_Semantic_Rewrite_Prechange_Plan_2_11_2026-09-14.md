# A06 v04 의미 재서술 사전 변경 계획 — locator 2~11 (2026-09-14)

- family: `S2-A06-T004: 도시 상수도 정수·배수 운영 — 다중 홉 관계 연결과 방향 보존`.
- precondition: source v04 `DCDE1ADF571063CC0FFB6DC3C545C44796D74557D9A4BC024CA7468D20BAE952`, registry `5122B1DD24977FC13B2F9C00198C24F8D40F6611F8BA9EE5284EDFDBC6862422`.
- source `concept`·`text`와 동일 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 2 | 배수문 점검 결과를 저수조 운영에 반영하는 절차 | process, role, comparison | 배수문 개방량과 저수조 수위를 비교해 당직자가 조작을 결정한다. |
| 3 | 수압 센서 값으로 응집조 유입 상태를 확인하는 기준 | part_of, state, attribute | 응집조 유입관의 계측값으로 유입 상태를 판단한다. |
| 4 | 여과지 판독 뒤 염소 주입량을 조정하는 절차 | process, role, state | 여과지 탁도 판독 뒤 담당자가 염소 주입 상태를 조정한다. |
| 5 | 방류 수질 기록을 정수 펌프 점검에 연결하는 절차 | part_of, process, role | 방류 경로의 수질 기록을 펌프 점검 순서와 연결한다. |
| 6 | 원수 유입 변화에 따른 배수문 조작 순서를 분류하는 기준 | process, classification, attribute | 원수 유입량 변화에 따라 배수문 조작 단계를 분류한다. |
| 7 | 수질 측정 뒤 저수조 유입을 조절하는 절차 | process, state, function | 수질 기준을 넘으면 저수조 유입을 조절한다. |
| 8 | 당직 교대 때 원수 유입 변화를 비교하는 절차 | process, role, comparison | 교대 전후 유입량을 비교해 다음 조치를 정한다. |
| 9 | 정수 펌프 수치와 방류 기록을 대조하는 기준 | part_of, state, attribute | 펌프 계측값과 방류 기록을 대조해 운전 상태를 판단한다. |
| 10 | 염소 주입기와 여과지 사이의 수동 전환을 기록하는 절차 | process, role, state | 수동 전환의 주체·시각·두 설비 상태를 기록한다. |
| 11 | 응집조·수압 센서·누수 감시기의 처리 순서를 확인하는 절차 | part_of, process, role | 세 장비의 연결 순서와 담당 조치를 확인한다. |

각 새 text에는 구체 대상, 관찰 계기, 판단 주체, 결과 제한을 독립적으로 넣는다. updater는 target 10과 비대상 7,790행 byte 보존을 검증하고, 적용 전 registry 행은 `A06_registry_before_v04_semantic_rewrite_2_11_2026-09-14.jsonl`에 보관한다.
