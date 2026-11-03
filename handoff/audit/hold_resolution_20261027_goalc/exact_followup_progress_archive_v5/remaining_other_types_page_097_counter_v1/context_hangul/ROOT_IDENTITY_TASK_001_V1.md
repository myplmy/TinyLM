# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1401791
original SHA-256: B0EC123CC03DDC71242781F5E3544774C5E502C44C80D2C13F808F23B3755963
candidate SHA-256: B0EC123CC03DDC71242781F5E3544774C5E502C44C80D2C13F808F23B3755963
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401791_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401791_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401791_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1401847
original SHA-256: BCE75B40236E34CF16626597C817A78D10F627C15C870F6ACF7E0DEA1C8F37E9
candidate SHA-256: BCE75B40236E34CF16626597C817A78D10F627C15C870F6ACF7E0DEA1C8F37E9
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401847_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401847_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401847_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401847_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401847_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401847_0010.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1402064
original SHA-256: E2C9800F362CC2C7FB3B0EF2A038B32DCC567DF41B8650BBAE4ACC6E00DC1871
candidate SHA-256: E2C9800F362CC2C7FB3B0EF2A038B32DCC567DF41B8650BBAE4ACC6E00DC1871
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402064_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402064_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402064_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402064_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402064_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402064_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1402458
original SHA-256: 1297D28541ABDCF126635181179CE44AC81DCDE99F70DA1DE9EB183BA2F8B21D
candidate SHA-256: 1297D28541ABDCF126635181179CE44AC81DCDE99F70DA1DE9EB183BA2F8B21D
원문 frame 패킷: [1, 16]
최종 full_diff 패킷: [32, 32]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 32]
후보 중복만 있는 생략 가능 패킷: [17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402458_0032.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1402746
original SHA-256: C68777B1BF29BBDB68A208BD6F9BAEA9CEDE5184D18D131851663D912071CF89
candidate SHA-256: C68777B1BF29BBDB68A208BD6F9BAEA9CEDE5184D18D131851663D912071CF89
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402746_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402746_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402746_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402746_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

