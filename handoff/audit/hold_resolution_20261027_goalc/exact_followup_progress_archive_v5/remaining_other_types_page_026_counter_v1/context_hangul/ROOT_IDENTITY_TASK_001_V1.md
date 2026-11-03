# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:294691
original SHA-256: 3729F5D073C371307AB5AC5A58487B07AE71EF82E0E3C7521825CE95905E9416
candidate SHA-256: 3729F5D073C371307AB5AC5A58487B07AE71EF82E0E3C7521825CE95905E9416
원문 frame 패킷: [1, 11]
최종 full_diff 패킷: [21, 21]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 21]
후보 중복만 있는 생략 가능 패킷: [12, 13, 14, 15, 16, 17, 18, 19, 20]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294691_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294691_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294691_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294691_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294691_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294691_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294691_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294691_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294691_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294691_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294691_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294691_0021.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:294700
original SHA-256: E1EC5852207805786C1970F4222C3670BBEB0928B7576A1534501E7F23B4DC66
candidate SHA-256: E1EC5852207805786C1970F4222C3670BBEB0928B7576A1534501E7F23B4DC66
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294700_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:294703
original SHA-256: A991FCD4B0F3ACA0026B38854FEAF99B6D84CA1F565F146DC328D81711CCF6E1
candidate SHA-256: A991FCD4B0F3ACA0026B38854FEAF99B6D84CA1F565F146DC328D81711CCF6E1
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294703_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294703_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294703_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294703_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:294756
original SHA-256: F896C18E29EC981B407527860DAA51C272B1AABCBDA4812453FAFDA0AB6F3518
candidate SHA-256: CA9343F2A6A49A6971CEC41B308DF6DF84EBF2147005B1A68B53AA0D86408527
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:294858
original SHA-256: 769CD22D56780B6489809D2A799F3486C7A36029E9FB4D0F6F94F5866BE8AE37
candidate SHA-256: 769CD22D56780B6489809D2A799F3486C7A36029E9FB4D0F6F94F5866BE8AE37
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294858_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

