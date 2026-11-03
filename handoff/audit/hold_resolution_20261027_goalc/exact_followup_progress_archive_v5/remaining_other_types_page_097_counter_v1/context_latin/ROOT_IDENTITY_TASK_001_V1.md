# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1402749
original SHA-256: 6C50F7A346246141E71E2802563C4E4B1C7FC91AC4C974D1FCA010B332BAC3C2
candidate SHA-256: 6C50F7A346246141E71E2802563C4E4B1C7FC91AC4C974D1FCA010B332BAC3C2
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402749_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402749_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402749_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1403298
original SHA-256: 86139E1698D148B80DAEB82B48DCBA721C270433151F6FE9C337799D7DFFC90E
candidate SHA-256: 86139E1698D148B80DAEB82B48DCBA721C270433151F6FE9C337799D7DFFC90E
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403298_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403298_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403298_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403298_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403298_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1403352
original SHA-256: ACFF802922CBBA4749F537CEF2FA8AF775A2EEB4B8C493DE92CA01DE32269209
candidate SHA-256: ACFF802922CBBA4749F537CEF2FA8AF775A2EEB4B8C493DE92CA01DE32269209
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403352_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403352_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403352_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1403459
original SHA-256: 294D60E5BBE5FD641DF15B0D9CC2849A37F0E3E7235DE210FD16C04B78AA82B9
candidate SHA-256: 294D60E5BBE5FD641DF15B0D9CC2849A37F0E3E7235DE210FD16C04B78AA82B9
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403459_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403459_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403459_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403459_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403459_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403459_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403459_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1403477
original SHA-256: AE9AEB2D6940CDCCDE950EEE0766C984E0CC3E3D7217C4FD2EA172D51F0C57D2
candidate SHA-256: AE9AEB2D6940CDCCDE950EEE0766C984E0CC3E3D7217C4FD2EA172D51F0C57D2
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403477_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403477_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403477_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1403477_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

