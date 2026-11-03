# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1341857
original SHA-256: 7CA0FB1370267FF71F3459F8E221357697E04ABE09268A52C2443980DFF9C240
candidate SHA-256: 7CA0FB1370267FF71F3459F8E221357697E04ABE09268A52C2443980DFF9C240
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341857_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1341883
original SHA-256: F3EC2C5D9FBD79B5396A6F6B48522DA0B92D385908B14448D53734B5831DA896
candidate SHA-256: F3EC2C5D9FBD79B5396A6F6B48522DA0B92D385908B14448D53734B5831DA896
원문 frame 패킷: [1, 16]
최종 full_diff 패킷: [32, 32]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 32]
후보 중복만 있는 생략 가능 패킷: [17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341883_0032.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1342035
original SHA-256: DE7665669F298237DF0DAE82B48A2A89B2D370C7F5EFBDE4727AC187B628A283
candidate SHA-256: DE7665669F298237DF0DAE82B48A2A89B2D370C7F5EFBDE4727AC187B628A283
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342035_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342035_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342035_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1342180
original SHA-256: 3A7BBEF6C208946352A939DA8E0B428D7A2C0AD7E6B33AC36C09B46BC46FF1F6
candidate SHA-256: 3A7BBEF6C208946352A939DA8E0B428D7A2C0AD7E6B33AC36C09B46BC46FF1F6
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342180_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342180_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342180_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342180_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1342253
original SHA-256: B2080E20BB3E1035C290FFEE1235EB6CF893A2B7901BF9D38F79C3175E5D7F3A
candidate SHA-256: B2080E20BB3E1035C290FFEE1235EB6CF893A2B7901BF9D38F79C3175E5D7F3A
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342253_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342253_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342253_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

