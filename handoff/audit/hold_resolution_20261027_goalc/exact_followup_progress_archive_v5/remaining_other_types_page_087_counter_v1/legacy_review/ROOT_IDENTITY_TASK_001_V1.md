# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1219625
original SHA-256: 82D153F48A6F0A0C911F6A089B50EC84319A35EB84361D938C8AF3F66DFF6632
candidate SHA-256: 82D153F48A6F0A0C911F6A089B50EC84319A35EB84361D938C8AF3F66DFF6632
원문 frame 패킷: [1, 22]
최종 full_diff 패킷: [44, 44]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 44]
후보 중복만 있는 생략 가능 패킷: [23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219625_0044.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1219743
original SHA-256: 7569B57FAAED257EB3CB8BEE48E62FFFB62E1DA865A9AEF4A45AC5B902C1B552
candidate SHA-256: E08FB85FA0D22AC2CE2AF1AD6BEE8B45E2777995FC4279FFAA6FC648F14BBDA5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1220016
original SHA-256: 7E03EE4AE7A7997D0A5C2B85B3017E29E2841AAF1F519AC8B2CA419DA5E0A54D
candidate SHA-256: CADFC1CE3218DDBE1D5FD6B6FB4664FCCC5593A9A9C081C8C4295D201A737EF6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1220027
original SHA-256: 54D862CFA58E11F64128E334CCD3A32F6B64CFDCEDA3D67A60742A5E8E8F9678
candidate SHA-256: 54D862CFA58E11F64128E334CCD3A32F6B64CFDCEDA3D67A60742A5E8E8F9678
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220027_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220027_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220027_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1220084
original SHA-256: C2A63C32802F7AC8383F43ABF3A0B16669E0B12B5F6E84CB7B5F5549D953818C
candidate SHA-256: C2A63C32802F7AC8383F43ABF3A0B16669E0B12B5F6E84CB7B5F5549D953818C
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220084_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220084_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220084_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

