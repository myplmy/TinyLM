# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:619506
original SHA-256: 8CA6CBBD55BAD6B33B73E9506DC67A71717C4AB51898093877262B167EB818C3
candidate SHA-256: 8CA6CBBD55BAD6B33B73E9506DC67A71717C4AB51898093877262B167EB818C3
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_619506_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_619506_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:619826
original SHA-256: 1257DC8D914F37C035345C92C667899441E8B99300F93A59CB4201BCB160161E
candidate SHA-256: 1257DC8D914F37C035345C92C667899441E8B99300F93A59CB4201BCB160161E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_619826_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:620879
original SHA-256: D2F47A1597A1353D7F839D1A72831C215E57E96D4432CFEC8CE99586F0C93F77
candidate SHA-256: D2F47A1597A1353D7F839D1A72831C215E57E96D4432CFEC8CE99586F0C93F77
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 14]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_620879_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_620879_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_620879_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_620879_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_620879_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_620879_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_620879_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_620879_0014.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:621563
original SHA-256: 7E74B87AD8B17B2CB33589D2C65E81654E3D4C0F14D656FDBDE5843C5084E10A
candidate SHA-256: 0EBF6C5AC13138219F1C23DBB227EBC4F8170E0F60139B9D5253E9D0362034ED
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:621827
original SHA-256: 3CF910B232B251D9FDEF1671AF696547940EF2DB9C194683A72A3F621992149D
candidate SHA-256: 3CF910B232B251D9FDEF1671AF696547940EF2DB9C194683A72A3F621992149D
원문 frame 패킷: [1, 25]
최종 full_diff 패킷: [49, 49]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 49]
후보 중복만 있는 생략 가능 패킷: [26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_621827_0049.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

