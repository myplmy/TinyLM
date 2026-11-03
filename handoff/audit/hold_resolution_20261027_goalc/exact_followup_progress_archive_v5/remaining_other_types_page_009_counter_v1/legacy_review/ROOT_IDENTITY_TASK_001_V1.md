# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:84608
original SHA-256: 2C2B92F1B7D1E8B2FA330626853E8A8F645299F316808F34D5C21E82E3BFDEC3
candidate SHA-256: 37A38FCBC12FF37FBDABAB7A02DE8ED885082433705623EB04F3250FBFA54F59
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:84727
original SHA-256: C9D2156B795B74C986CC2429D5A009ABBB4C841DE2E205D95FCE99D6321774E1
candidate SHA-256: 5C64566614BB1A9C46A3A1CB9D041497C1D4E8123CBACB53560520C4B2132538
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:84793
original SHA-256: B7D69F51E4C5995C1D6EC4EF26CFF08136AC5E7A6D69503C6684074DD484F873
candidate SHA-256: B7D69F51E4C5995C1D6EC4EF26CFF08136AC5E7A6D69503C6684074DD484F873
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84793_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84793_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84793_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84793_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:84801
original SHA-256: CC6EE7DE41E5DBA654089615145C0B88334E377CF6687552CCE8C9BB09603C13
candidate SHA-256: 42C7D5ED055C9249610657B10D68EDAA2B7A1E1A0CB5FAD109A96F298E84B975
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:84890
original SHA-256: 677A128D252BC306E0E77396521F308DA474BA5E178FE5F661CBFF0EE7100A04
candidate SHA-256: 677A128D252BC306E0E77396521F308DA474BA5E178FE5F661CBFF0EE7100A04
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84890_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84890_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84890_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84890_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

