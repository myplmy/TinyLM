# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1070984
original SHA-256: 2B14C3AFC68C41758FAD6D7F039D18ECCD24C14CCBF2BCCF18D21304F32B57A4
candidate SHA-256: 2B14C3AFC68C41758FAD6D7F039D18ECCD24C14CCBF2BCCF18D21304F32B57A4
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1070984_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1070984_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1070984_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1070984_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1071205
original SHA-256: AD0F9B264B5B662EDD1FDE9D55B636F19B295F57E8EDDB0AF793F88C8B1B4646
candidate SHA-256: AD0F9B264B5B662EDD1FDE9D55B636F19B295F57E8EDDB0AF793F88C8B1B4646
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071205_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071205_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071205_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1071223
original SHA-256: 833C0A0F3C33890D67A608405C9BFCEC26BF2E85C9FD12E0B708B886164CC16C
candidate SHA-256: 833C0A0F3C33890D67A608405C9BFCEC26BF2E85C9FD12E0B708B886164CC16C
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [23, 23]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 23]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071223_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071223_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071223_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071223_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071223_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071223_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071223_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071223_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071223_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071223_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071223_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071223_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071223_0023.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1071407
original SHA-256: 99EDC8919D4F4E2EB771097DDF848B10F48F9A3E7EF573040FA091F22A8AF50B
candidate SHA-256: 99EDC8919D4F4E2EB771097DDF848B10F48F9A3E7EF573040FA091F22A8AF50B
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071407_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071407_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071407_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071407_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071407_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1071409
original SHA-256: BAAA40BB3DE2239C5467DFFC1963C35AA5F0F6EC6648500B41165010CF848C18
candidate SHA-256: BAAA40BB3DE2239C5467DFFC1963C35AA5F0F6EC6648500B41165010CF848C18
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071409_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071409_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071409_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

