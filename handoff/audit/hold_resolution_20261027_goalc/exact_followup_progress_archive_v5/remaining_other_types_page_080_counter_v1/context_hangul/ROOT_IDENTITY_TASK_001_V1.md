# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1101542
original SHA-256: 7489EAD6957F5368147DB6365B80AE5C5C2159DF3D542E92EE2D36CFB690BDE5
candidate SHA-256: 7489EAD6957F5368147DB6365B80AE5C5C2159DF3D542E92EE2D36CFB690BDE5
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101542_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101542_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101542_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1101751
original SHA-256: 792091C541C20EEC3EF692CE69E24821E5DE95167FD95EB9F692D801147FAB4D
candidate SHA-256: B9170E44ADA8C9C5C22830DDFAA67DF7FEBC386B9BD1BBE44AB5A2389902BBC5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1102014
original SHA-256: 43A5CE8BC2A9F10BC22C2DD2F824A7E5B7F6AD70B7AEFCED2520B0F1801E6A2B
candidate SHA-256: 43A5CE8BC2A9F10BC22C2DD2F824A7E5B7F6AD70B7AEFCED2520B0F1801E6A2B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102014_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102014_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1102027
original SHA-256: 5A63BF147C583D0063ADCC8B2EEB69F6FEF3914766FDC704884B30449CE57890
candidate SHA-256: 5A63BF147C583D0063ADCC8B2EEB69F6FEF3914766FDC704884B30449CE57890
원문 frame 패킷: [1, 20]
최종 full_diff 패킷: [40, 40]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 40]
후보 중복만 있는 생략 가능 패킷: [21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102027_0040.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1102270
original SHA-256: E4C308020CE2D74213903AC5D7C691E839DD65A076A62B9312E41BDA40E1F6E1
candidate SHA-256: E4C308020CE2D74213903AC5D7C691E839DD65A076A62B9312E41BDA40E1F6E1
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102270_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102270_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102270_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

