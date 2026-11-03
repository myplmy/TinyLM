# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1361464
original SHA-256: 957F438C9465313333CCC5DABAC1E34BFAF3F3B2987E3CADE951E714D74A4F33
candidate SHA-256: 957F438C9465313333CCC5DABAC1E34BFAF3F3B2987E3CADE951E714D74A4F33
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 15]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14, 15]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361464_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361464_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361464_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361464_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361464_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361464_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361464_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361464_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361464_0015.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1362824
original SHA-256: 3EEDACA5B9C2A1031C9E5BB6007A5959A7500FCADEFBE835E499BC30AE661879
candidate SHA-256: 3EEDACA5B9C2A1031C9E5BB6007A5959A7500FCADEFBE835E499BC30AE661879
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362824_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362824_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362824_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1362913
original SHA-256: CC75D592952A595212BF2EC0B6429E8F8DC6FD9338A2788D340A3402A77EE019
candidate SHA-256: CC75D592952A595212BF2EC0B6429E8F8DC6FD9338A2788D340A3402A77EE019
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362913_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362913_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362913_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362913_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362913_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1363331
original SHA-256: 55425403DA86D3322833F593171272D8145A7AD6E78BD8254DF30675B62D7B88
candidate SHA-256: 55425403DA86D3322833F593171272D8145A7AD6E78BD8254DF30675B62D7B88
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1363331_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1363331_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1363331_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1363331_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1363382
original SHA-256: 0503D88B485CA753E0621CA8E39CA7C00C61C0925CA8D694ADF9928F14CE1BF1
candidate SHA-256: 0503D88B485CA753E0621CA8E39CA7C00C61C0925CA8D694ADF9928F14CE1BF1
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1363382_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1363382_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1363382_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1363382_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

