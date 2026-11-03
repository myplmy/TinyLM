# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1310908
original SHA-256: 5CE2FF278DAAD49066CEC9D632C2BCE473793F67BC836539C017AD94F37CEB7F
candidate SHA-256: 5CE2FF278DAAD49066CEC9D632C2BCE473793F67BC836539C017AD94F37CEB7F
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [16, 16]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 16]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14, 15]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1310908_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1310908_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1310908_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1310908_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1310908_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1310908_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1310908_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1310908_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1310908_0016.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1312044
original SHA-256: 7107C4F58F3CE1AE9227446BB282E57D43DDBC5596950398A1DBEB8C1DE5EC58
candidate SHA-256: 7107C4F58F3CE1AE9227446BB282E57D43DDBC5596950398A1DBEB8C1DE5EC58
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312044_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312044_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312044_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312044_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312044_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312044_0010.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1312453
original SHA-256: 07CFAB414930B2B6AFB5092EE6DF281FC1B78A7E1892B5FAE3568DE60E413E6C
candidate SHA-256: 07CFAB414930B2B6AFB5092EE6DF281FC1B78A7E1892B5FAE3568DE60E413E6C
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312453_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312453_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312453_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312453_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312453_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312453_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1312776
original SHA-256: 44993E78478D5A4C9EB321C12556F8A2435263F4E5731EC70B20DA4DCADFC4DA
candidate SHA-256: 44993E78478D5A4C9EB321C12556F8A2435263F4E5731EC70B20DA4DCADFC4DA
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [15, 15]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 15]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312776_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312776_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312776_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312776_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312776_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312776_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312776_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312776_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312776_0015.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1312833
original SHA-256: 6D7F697851C0235E59AF9BB6692E11145ECF3CF5BDA76E69A47FC867B77DE0E3
candidate SHA-256: 6D7F697851C0235E59AF9BB6692E11145ECF3CF5BDA76E69A47FC867B77DE0E3
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312833_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312833_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1312833_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

