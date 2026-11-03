# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:747823
original SHA-256: 53C48EFF9A1AD5F8D55688C5120D2FC9E534F21E1A80A68A1A6392A6B91AB411
candidate SHA-256: 53C48EFF9A1AD5F8D55688C5120D2FC9E534F21E1A80A68A1A6392A6B91AB411
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_747823_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_747823_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_747823_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_747823_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_747823_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:747974
original SHA-256: A9FC3AE0A265941F821E3BB3CE5622704268979F6600A4768DD4C030DE812595
candidate SHA-256: A9FC3AE0A265941F821E3BB3CE5622704268979F6600A4768DD4C030DE812595
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_747974_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_747974_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_747974_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:748238
original SHA-256: 1633EA80138EB8EE009C36E64E4F72F59F0D2B0EFD1877475DFA03311CE0CB0B
candidate SHA-256: 1633EA80138EB8EE009C36E64E4F72F59F0D2B0EFD1877475DFA03311CE0CB0B
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748238_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748238_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748238_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748238_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:748535
original SHA-256: 30B6AD011A64F405D5113203F4DD706F65F9DEF6C7C4FB88BDA5C2F5A29CAB35
candidate SHA-256: 30B6AD011A64F405D5113203F4DD706F65F9DEF6C7C4FB88BDA5C2F5A29CAB35
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748535_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748535_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748535_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:748689
original SHA-256: 1BD2198C08BF187928CDCA6162D8A9A987B3E1AC6FD270107D9A1B0360D477C2
candidate SHA-256: 1BD2198C08BF187928CDCA6162D8A9A987B3E1AC6FD270107D9A1B0360D477C2
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [17, 17]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 17]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748689_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748689_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748689_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748689_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748689_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748689_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748689_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748689_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748689_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748689_0017.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

