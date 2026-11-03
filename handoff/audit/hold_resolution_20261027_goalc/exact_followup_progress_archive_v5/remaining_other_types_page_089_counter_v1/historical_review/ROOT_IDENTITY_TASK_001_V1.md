# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1252861
original SHA-256: 561A7B0C651CA95124BD85625E92C22916A4B6575843D1434F7285E0137FB744
candidate SHA-256: 561A7B0C651CA95124BD85625E92C22916A4B6575843D1434F7285E0137FB744
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8, 9]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252861_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252861_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252861_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252861_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252861_0008.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252861_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1252895
original SHA-256: 16D9E4045372809FBC3AC5F9EE09A29B1E104624FD415572FD931AD13E12B5F7
candidate SHA-256: 23D4B8A902F3185F022DB7A949BA01334132B3D1C2554D8E2CAE2024E55B4D67
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1252971
original SHA-256: A47D9CDC5BC81C5270DDC9DF532ECEEBF47C61581024B5FDC415D3295019EB2D
candidate SHA-256: A47D9CDC5BC81C5270DDC9DF532ECEEBF47C61581024B5FDC415D3295019EB2D
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252971_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1253130
original SHA-256: 613B331CF3DC473B36E19CE590A83926EF4824BB24A6010E66293EF19B899373
candidate SHA-256: 613B331CF3DC473B36E19CE590A83926EF4824BB24A6010E66293EF19B899373
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253130_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253130_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253130_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253130_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1253191
original SHA-256: 10319D1099A2F187886BADB7C84090C8993F98F9E1D1F7E56BF808F66F7D3B78
candidate SHA-256: 7CA6108E4FCFF4258E28066FA3C553C52BD51A1BA0D9B583603410B3B99B697A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

