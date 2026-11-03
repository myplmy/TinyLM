# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:561078
original SHA-256: 0D095E0ADBDC8595173BBC3CF8D617D005AB1DDBBA735ECB0C35A6D7182D84FF
candidate SHA-256: 0D095E0ADBDC8595173BBC3CF8D617D005AB1DDBBA735ECB0C35A6D7182D84FF
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561078_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561078_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561078_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:561154
original SHA-256: A48941314B9A6ADF4970F8129985ED141AD2B4731F7DBFDD30B8F1732CB520A8
candidate SHA-256: A48941314B9A6ADF4970F8129985ED141AD2B4731F7DBFDD30B8F1732CB520A8
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561154_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561154_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561154_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561154_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561154_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561154_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561154_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:561209
original SHA-256: 61F4205C6349D0415ED20CC48E25E999444A1BF37742829E423DBF0384136E6C
candidate SHA-256: DED1CFF7A14681C5F36FBCDA92010DB844DD26FBFF4F3CACF066C8205D1F2903
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:561243
original SHA-256: B56B65AC3501AFE8CAFFC07645B7585A30E32746AA30329B7A2035A87200EBF1
candidate SHA-256: B56B65AC3501AFE8CAFFC07645B7585A30E32746AA30329B7A2035A87200EBF1
원문 frame 패킷: [1, 29]
최종 full_diff 패킷: [57, 57]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 57]
후보 중복만 있는 생략 가능 패킷: [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561243_0057.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:561293
original SHA-256: E687D18B3ECD060E90E41ADEDD5D3742A8819A1301C2034FBC570B3B0FDEC806
candidate SHA-256: E687D18B3ECD060E90E41ADEDD5D3742A8819A1301C2034FBC570B3B0FDEC806
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561293_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561293_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561293_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561293_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

