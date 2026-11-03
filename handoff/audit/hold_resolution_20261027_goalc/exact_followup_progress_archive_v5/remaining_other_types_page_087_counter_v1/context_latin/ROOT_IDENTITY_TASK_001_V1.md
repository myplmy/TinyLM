# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1219387
original SHA-256: 3A705208B8B1B7AA7F022C39BF66F6CB7A7105BC3733FE690961806F5057B1AC
candidate SHA-256: 3A705208B8B1B7AA7F022C39BF66F6CB7A7105BC3733FE690961806F5057B1AC
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [17, 17]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 17]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219387_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219387_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219387_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219387_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219387_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219387_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219387_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219387_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219387_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219387_0017.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1219826
original SHA-256: 9FD8FD69B3DEAEFEE37E2C3D197F0B2527F318A92DCC5BDA0BF5A21BE6BF3666
candidate SHA-256: 9FD8FD69B3DEAEFEE37E2C3D197F0B2527F318A92DCC5BDA0BF5A21BE6BF3666
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219826_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219826_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219826_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219826_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219826_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219826_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1220259
original SHA-256: 55150BE5F00C3CAC8D067F5748464FDD5E243B7A0B21E5427F15769ED197FB29
candidate SHA-256: 55150BE5F00C3CAC8D067F5748464FDD5E243B7A0B21E5427F15769ED197FB29
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220259_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220259_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220259_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220259_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220259_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220259_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220259_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220259_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1220749
original SHA-256: 359C7CD324CD13960FB387F6A01ED39A529087D57BD68B5102FDEE41F68F589E
candidate SHA-256: C3AA15F4C557CB3152E66509E94CBD42CF8A657EF02112FFA132F8C096DEDCCF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1221301
original SHA-256: B5AA2DED8D85051720C5A8F4FCEE66509C9F0E9FEC555F8E5FC56E1F9860AB74
candidate SHA-256: B5AA2DED8D85051720C5A8F4FCEE66509C9F0E9FEC555F8E5FC56E1F9860AB74
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [17, 17]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 17]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1221301_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1221301_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1221301_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1221301_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1221301_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1221301_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1221301_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1221301_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1221301_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1221301_0017.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

