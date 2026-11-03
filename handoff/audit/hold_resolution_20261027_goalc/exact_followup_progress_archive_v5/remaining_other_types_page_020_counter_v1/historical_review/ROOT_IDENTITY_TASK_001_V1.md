# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:217925
original SHA-256: 4A893AFE2306914209AADBEF30AC7856671B5F5D44AF2079AE89D2C8C6A08F25
candidate SHA-256: 4A893AFE2306914209AADBEF30AC7856671B5F5D44AF2079AE89D2C8C6A08F25
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [17, 17]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 17]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217925_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217925_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217925_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217925_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217925_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217925_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217925_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217925_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217925_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217925_0017.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:217976
original SHA-256: 1B77ECDB7585F6DBB04CCE1B03C53E893CD94FD92AFE89023E48C2EC1AE54764
candidate SHA-256: 6F2C8A67A3CCFE6422E67BF34A078BF3FE3C3889A27C204B531B2A2BD708A210
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:217995
original SHA-256: 3449B5BD22AD111354DB61B5E8363011D13D32489637025DB84F1169DF1B9EF7
candidate SHA-256: 3449B5BD22AD111354DB61B5E8363011D13D32489637025DB84F1169DF1B9EF7
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217995_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217995_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217995_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217995_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217995_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217995_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217995_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:218026
original SHA-256: 29FCAF071CB0779670DDCD4A495E45B48C09A4144B8BA5E52C25668881CD93ED
candidate SHA-256: 29FCAF071CB0779670DDCD4A495E45B48C09A4144B8BA5E52C25668881CD93ED
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_218026_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_218026_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_218026_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_218026_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_218026_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_218026_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_218026_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:218158
original SHA-256: 28F5F513D38F450E002CFE1DE237B018E227E96C8CEC282AC913441210777FB9
candidate SHA-256: 59F5744D72B3A03DDA28C4E293440E3414617998E2793D331277DCE167FCAAD1
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

