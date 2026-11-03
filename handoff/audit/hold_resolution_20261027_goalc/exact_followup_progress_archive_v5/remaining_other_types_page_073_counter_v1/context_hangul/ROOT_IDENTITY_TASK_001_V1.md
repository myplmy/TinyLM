# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1000896
original SHA-256: 32EC9911A025D01411C3DA1FEC12F566811804DB3FDC61DE759F55217C218DEA
candidate SHA-256: 32EC9911A025D01411C3DA1FEC12F566811804DB3FDC61DE759F55217C218DEA
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000896_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1002519
original SHA-256: D15CB5E850A0578609C273B07389A2AACA2B39ACF5C552DB671E7A4633CE3857
candidate SHA-256: D15CB5E850A0578609C273B07389A2AACA2B39ACF5C552DB671E7A4633CE3857
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002519_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002519_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002519_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002519_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002519_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002519_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002519_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002519_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1002907
original SHA-256: 6C8F67E3C8631DFF61BF89C676ACEB231B6D79ADBEE67CC2166F69B7D7E3A739
candidate SHA-256: 6C8F67E3C8631DFF61BF89C676ACEB231B6D79ADBEE67CC2166F69B7D7E3A739
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [23, 23]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 23]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002907_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002907_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002907_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002907_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002907_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002907_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002907_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002907_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002907_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002907_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002907_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002907_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1002907_0023.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1004236
original SHA-256: BC3EC829196D949FC8CD96E3CD78F56458322D7865D8C72CE4508D295971A7E5
candidate SHA-256: BC3EC829196D949FC8CD96E3CD78F56458322D7865D8C72CE4508D295971A7E5
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1004236_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1004236_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1004236_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1004236_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1004236_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1004432
original SHA-256: 6FE019460A515E8B392A658C4B014B59F8D715B70705EEC1117B6A7047D4709D
candidate SHA-256: 6FE019460A515E8B392A658C4B014B59F8D715B70705EEC1117B6A7047D4709D
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1004432_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1004432_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

