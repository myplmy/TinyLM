# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1342141
original SHA-256: E40929F5E3E9EC68FA3DDC3926C43E7010F4FC8949681D620D1F6E9BD4AC7A03
candidate SHA-256: E40929F5E3E9EC68FA3DDC3926C43E7010F4FC8949681D620D1F6E9BD4AC7A03
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342141_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342141_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342141_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342141_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342141_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342141_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342141_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1342247
original SHA-256: 67B8763B4F59E984F8707A343D5B9520DCD357FD4B770EFA25E874001CACD649
candidate SHA-256: 67B8763B4F59E984F8707A343D5B9520DCD357FD4B770EFA25E874001CACD649
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342247_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342247_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342247_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342247_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342247_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342247_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342247_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1342492
original SHA-256: B164095816CF4D5318312F269BA39BC2EB3978BE1DCBA30300BCD97B43938FC6
candidate SHA-256: B164095816CF4D5318312F269BA39BC2EB3978BE1DCBA30300BCD97B43938FC6
원문 frame 패킷: [1, 21]
최종 full_diff 패킷: [41, 41]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 41]
후보 중복만 있는 생략 가능 패킷: [22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342492_0041.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1343050
original SHA-256: DD6EBAC88BBE9645678E55A0BFA61901A64322A50E6F354D11007DB41B1BAC2A
candidate SHA-256: DD6EBAC88BBE9645678E55A0BFA61901A64322A50E6F354D11007DB41B1BAC2A
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343050_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343050_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343050_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343050_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343050_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1343086
original SHA-256: C25EBD7F9990C2BBA783F0AAF08DD1AED373908A8ADB3B6F4AB96AD8C9BB3477
candidate SHA-256: C25EBD7F9990C2BBA783F0AAF08DD1AED373908A8ADB3B6F4AB96AD8C9BB3477
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343086_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343086_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343086_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343086_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343086_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

