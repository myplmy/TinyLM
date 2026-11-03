# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:270388
original SHA-256: 23985CA678C0402AFA0DF2C6C73B4759A30A0EE409E08304451EC9B518E10D44
candidate SHA-256: A3362DFB6CF7D18950441F1AC37FF85FEEDCFAFC787C3AB7EF341B47AEFCE0AF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:270533
original SHA-256: F9FA8BE6DE0CE8735A7CDEC732A6ED059391F9BE9FC22C3A47661DE371065BBE
candidate SHA-256: F9FA8BE6DE0CE8735A7CDEC732A6ED059391F9BE9FC22C3A47661DE371065BBE
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [20, 20]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18, 19]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270533_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270533_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270533_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270533_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270533_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270533_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270533_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270533_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270533_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270533_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270533_0020.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:270598
original SHA-256: 822E1A612A46EDEE732E5788FEC9DEEDB0F0864292F70299B8332BEA709D1BD7
candidate SHA-256: 822E1A612A46EDEE732E5788FEC9DEEDB0F0864292F70299B8332BEA709D1BD7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270598_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:270656
original SHA-256: 4F5C58855A03323CD5961009656581B28A75AC7AB205D540CB6FF64BEBE77B8F
candidate SHA-256: 4F5C58855A03323CD5961009656581B28A75AC7AB205D540CB6FF64BEBE77B8F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270656_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:270694
original SHA-256: 9204AFA489D262F57E008FEB3637B01C9A7738DE15D022732BCACE51C63C2B28
candidate SHA-256: 9204AFA489D262F57E008FEB3637B01C9A7738DE15D022732BCACE51C63C2B28
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270694_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270694_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270694_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270694_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

