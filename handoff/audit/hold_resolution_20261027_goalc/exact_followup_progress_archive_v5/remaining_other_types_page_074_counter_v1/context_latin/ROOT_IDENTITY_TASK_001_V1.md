# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1009997
original SHA-256: 8F0F9B90803F44EB856A4A1BA2D4438BE14C36CA8F30081BB7989B8F17142DE6
candidate SHA-256: 8F0F9B90803F44EB856A4A1BA2D4438BE14C36CA8F30081BB7989B8F17142DE6
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 14]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1009997_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1009997_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1009997_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1009997_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1009997_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1009997_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1009997_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1009997_0014.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1010087
original SHA-256: EA9DE9AF931C8EEF589F11F50909D4EA293CC17BA5779AA3FA26112AB8CF67FE
candidate SHA-256: EA9DE9AF931C8EEF589F11F50909D4EA293CC17BA5779AA3FA26112AB8CF67FE
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010087_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010087_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010087_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010087_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1011444
original SHA-256: 9DC6B99C1CEA4F21A3E585F7EC55C5757AD31B3E221A7A3C35A91DEF09A4753A
candidate SHA-256: CC306E50A73A19A3457B784FD984E210D4CF0878E35145A8B3AF5570FAA43DD0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1011760
original SHA-256: DADBED7FB9E124831666FCC70FABD894479610DB49A45C05147E8C2F4E45EC17
candidate SHA-256: DADBED7FB9E124831666FCC70FABD894479610DB49A45C05147E8C2F4E45EC17
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011760_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011760_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011760_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011760_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1011801
original SHA-256: B52E99F729DE7B76BB49AA922B8331141AC7607CC4D9083BF077DC6FB6B9938A
candidate SHA-256: B52E99F729DE7B76BB49AA922B8331141AC7607CC4D9083BF077DC6FB6B9938A
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011801_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011801_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011801_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011801_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011801_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011801_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

