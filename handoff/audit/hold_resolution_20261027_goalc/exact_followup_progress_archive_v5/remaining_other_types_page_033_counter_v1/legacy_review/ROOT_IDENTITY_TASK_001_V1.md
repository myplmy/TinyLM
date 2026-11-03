# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:387070
original SHA-256: 1FEA1E6073D26E4D3E7F8AF9A00693C9E446084E51C614F1916C75A0D54DFE2E
candidate SHA-256: 1FEA1E6073D26E4D3E7F8AF9A00693C9E446084E51C614F1916C75A0D54DFE2E
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387070_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387070_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387070_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387070_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387070_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387070_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387070_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387070_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:387214
original SHA-256: 27D164AEB762C1CB4E3224F5746F6C41D4B834F05B46676EA7A45984019F4386
candidate SHA-256: 27D164AEB762C1CB4E3224F5746F6C41D4B834F05B46676EA7A45984019F4386
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387214_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387214_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387214_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387214_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387214_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387214_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:387389
original SHA-256: 1079D5AECF686EAE78228BD1A6A2544111735E229256A9B15CAA105CC9E3520D
candidate SHA-256: 1079D5AECF686EAE78228BD1A6A2544111735E229256A9B15CAA105CC9E3520D
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387389_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387389_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387389_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:387567
original SHA-256: 0BB4AA7D8CD67C233D17851EDAB736CEBA2D7ABF7D4EC2283EF2A4A5AEEF552A
candidate SHA-256: 0BB4AA7D8CD67C233D17851EDAB736CEBA2D7ABF7D4EC2283EF2A4A5AEEF552A
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387567_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387567_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387567_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387567_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387567_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:387699
original SHA-256: A6A65650BB65A4822C425E9A01545B0823D7FDF2B9EF7FDD60910FF4C6556E51
candidate SHA-256: 0A31FFC39C6A0127E15CBE81E83D5C86A08E725791077704241D716C293052EE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

