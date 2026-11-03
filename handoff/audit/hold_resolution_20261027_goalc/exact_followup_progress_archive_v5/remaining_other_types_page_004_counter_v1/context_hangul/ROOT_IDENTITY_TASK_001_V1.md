# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:39331
original SHA-256: F27AC39ED87D24CF5CE51C2F7EF8846D177BED5AFE2BD4A48BE088C073B2BE85
candidate SHA-256: F27AC39ED87D24CF5CE51C2F7EF8846D177BED5AFE2BD4A48BE088C073B2BE85
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39331_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39331_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39331_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39331_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39331_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39331_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39331_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39331_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:39410
original SHA-256: DE31FC1CED8F53F3E2B52B2719B77BC0DD66356735FC8BA0DFCE966057CCC7D4
candidate SHA-256: DE31FC1CED8F53F3E2B52B2719B77BC0DD66356735FC8BA0DFCE966057CCC7D4
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39410_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39410_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39410_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39410_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39410_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39410_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39410_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:39659
original SHA-256: D766D753D2A01D5961A3D148993B1DCC415C3DAAA3BC6360B728D409DD163A64
candidate SHA-256: D766D753D2A01D5961A3D148993B1DCC415C3DAAA3BC6360B728D409DD163A64
원문 frame 패킷: [1, 16]
최종 full_diff 패킷: [31, 31]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 31]
후보 중복만 있는 생략 가능 패킷: [17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39659_0031.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:39797
original SHA-256: 9D6502511D95BF583696A71ED5ACF118A61E315E153AE90010F7C77030DFFF7A
candidate SHA-256: 9D6502511D95BF583696A71ED5ACF118A61E315E153AE90010F7C77030DFFF7A
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39797_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39797_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39797_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39797_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39797_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:39833
original SHA-256: 49361461AE1DF973D85BA65FE31FD36482C796A305F08F7D41ED4CC572EEE704
candidate SHA-256: 49361461AE1DF973D85BA65FE31FD36482C796A305F08F7D41ED4CC572EEE704
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39833_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39833_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39833_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39833_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39833_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

