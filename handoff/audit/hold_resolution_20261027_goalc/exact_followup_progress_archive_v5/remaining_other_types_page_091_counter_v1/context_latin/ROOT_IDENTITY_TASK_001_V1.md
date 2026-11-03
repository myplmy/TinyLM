# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1283742
original SHA-256: D1AFF859203B35253D3E7027B923933A2DE736FF2FD0D9DAD50B6053FBFCE718
candidate SHA-256: D1AFF859203B35253D3E7027B923933A2DE736FF2FD0D9DAD50B6053FBFCE718
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283742_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283742_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283742_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283742_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283742_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283742_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283742_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283742_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1283993
original SHA-256: 43986C1BEC271D032436BBDB71AF61E604A49F04F98DFB3EE9519D9C0B456DF1
candidate SHA-256: 43986C1BEC271D032436BBDB71AF61E604A49F04F98DFB3EE9519D9C0B456DF1
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283993_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283993_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283993_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1284217
original SHA-256: 9CAEE386828AC745B301CC2C867310540CDB12913B21AB55C8A70DA7E7D2C8E9
candidate SHA-256: 9CAEE386828AC745B301CC2C867310540CDB12913B21AB55C8A70DA7E7D2C8E9
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284217_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284217_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284217_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284217_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284217_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284217_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284217_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1284353
original SHA-256: A53BD78078FB9CFF8DB4780EDCED7E8EEC1A7E572B1F7749315A36849991DEA4
candidate SHA-256: A53BD78078FB9CFF8DB4780EDCED7E8EEC1A7E572B1F7749315A36849991DEA4
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284353_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284353_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284353_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1284427
original SHA-256: 1BC55EC39E4E211B7AD38E1F72A9DA196EC9C56C3A80DA66B89BFB1497166108
candidate SHA-256: 1BC55EC39E4E211B7AD38E1F72A9DA196EC9C56C3A80DA66B89BFB1497166108
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284427_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284427_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284427_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284427_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284427_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284427_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

