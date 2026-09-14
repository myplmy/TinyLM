# A06 v04 의미 재서술 사전 변경 계획 — locator 12~21 (2026-09-14)

- family: `S2-A06-T004: 도시 상수도 정수·배수 운영 — 다중 홉 관계 연결과 방향 보존`.
- precondition: source v04 `C0404F61FE21B7E0286120CCFAD6BDC5610ADB3E9740F5FEFFC9F0ABEC210C60`, registry `B91F74FE97C548BF61DC9A992F6CB4096A54B226F7EC9F0C8C6FB1D13C30140E`.
- source `concept`·`text`와 동일 registry locator의 `primary` 10개만 바꾼다. relations, `other_type`, registry 비-primary field, 행 순서, 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 독립 의미 판단 |
|---|---|---|---|
| 12 | 저수조 수위에 따른 배수문 임시 차단 순서를 분류하는 기준 | process, classification, attribute | 수위값에 따라 배수문 임시 차단 단계를 분류한다. |
| 13 | 누수 경보 뒤 원수 유입을 재개하는 절차 | process, state, function | 누수 경보가 해제된 뒤 원수 유입 기능을 재개한다. |
| 14 | 배수문 판독 뒤 저수조 수위를 조정하는 절차 | process, role, comparison | 배수문·저수조 값을 비교해 당직자가 조작을 선택한다. |
| 15 | 수압 센서와 응집조 유입 상태를 대체 경로에서 구분하는 기준 | part_of, state, attribute, other | 동시 조작이 있으면 센서·유입관의 상태 연결을 보류한다. |
| 16 | 여과지 점검 뒤 염소 주입과 저수조 유입을 조정하는 절차 | process, role, state | 여과지 점검 뒤 담당자가 주입·유입 상태를 조정한다. |
| 17 | 방류 승인 뒤 정수 펌프 점검을 이어 가는 절차 | part_of, process, role | 방류 경로 기록을 확인한 뒤 펌프 점검을 시작한다. |
| 18 | 원수 유입량 변화에 따른 당직 조치 주기를 분류하는 기준 | process, classification, attribute | 유입량과 관찰 주기에 따라 당직 조치를 분류한다. |
| 19 | 수질 판독 뒤 저수조 유입을 재개하는 절차 | process, state, function | 기준값 회복 뒤 저수조 유입 기능을 재개한다. |
| 20 | 새벽 당직표와 원수 유입량을 대조하는 절차 | process, role, comparison | 새벽 교대자가 당직표·유입량을 비교해 조치를 고른다. |
| 21 | 야간 점검에서 펌프·방류·응집조 상태를 대조하는 기준 | part_of, state, attribute | 정수 공정 구성요소의 계측 상태를 대조한다. |

각 새 text에는 구체 대상, 관찰 계기, 판단 주체, 결과 제한을 독립적으로 넣는다. updater는 target 10과 비대상 7,790행 byte 보존을 검증하고, 적용 전 registry 행은 `A06_registry_before_v04_semantic_rewrite_12_21_2026-09-14.jsonl`에 보관한다.
