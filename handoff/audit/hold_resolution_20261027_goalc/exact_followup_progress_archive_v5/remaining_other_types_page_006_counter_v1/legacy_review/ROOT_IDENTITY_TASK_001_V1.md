# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:59703
original SHA-256: BAEB12271896DF034C37AAB7D82D45CFBDACC2BE158EFFEBA1DA5136DEFD159F
candidate SHA-256: D4A1C33CF74FE1604398730DFA601067B5E959050E2435E02BB882CB446AAA48
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:60267
original SHA-256: 5DB8F6EECD77A981E1363F13DF033ECC03D20B60A2903A70E214F52CC9754DAF
candidate SHA-256: 5DB8F6EECD77A981E1363F13DF033ECC03D20B60A2903A70E214F52CC9754DAF
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60267_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:60385
original SHA-256: 4620446044D0DD185BF9F7FD4247676553B337B0813C65EBA087F3BDEF23D17E
candidate SHA-256: 4620446044D0DD185BF9F7FD4247676553B337B0813C65EBA087F3BDEF23D17E
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60385_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60385_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60385_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60385_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:60417
original SHA-256: F6DF84AF8BECE70F9A9EE6CEB4BC98AA22CA3AABCA7864CA65AEDD22F2E67C2C
candidate SHA-256: 80BCDD27AA380C5BF4F3FF15F7468D7651347D56A63CDE43B724D95085A08ABD
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:60502
original SHA-256: 90A032F8F2AEE5EA88431879A44FB79217182F484B950BCCCC48DD4EF7DF890E
candidate SHA-256: 90A032F8F2AEE5EA88431879A44FB79217182F484B950BCCCC48DD4EF7DF890E
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 14]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60502_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60502_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60502_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60502_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60502_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60502_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60502_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60502_0014.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

