# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1342145
original SHA-256: 8CCB85283F38D310B3238942DCC692A77CA82ECD825F99082E132D96286FC2E5
candidate SHA-256: 8CCB85283F38D310B3238942DCC692A77CA82ECD825F99082E132D96286FC2E5
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342145_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342145_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342145_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342145_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342145_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1342177
original SHA-256: 564C42459E00D33CC9D4BC48CCC25848B46D209B731E77C4F25024DBDC4083C9
candidate SHA-256: 564C42459E00D33CC9D4BC48CCC25848B46D209B731E77C4F25024DBDC4083C9
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342177_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342177_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342177_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342177_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342177_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342177_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1342405
original SHA-256: 589230725611FA45A372829AFB9E9405F60FBA3E48D6BCCE7D74FD168EC16781
candidate SHA-256: 589230725611FA45A372829AFB9E9405F60FBA3E48D6BCCE7D74FD168EC16781
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342405_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342405_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342405_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342405_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1342650
original SHA-256: 7C9BE25943F79C851CE06C5F4709763D66BCF6C8B79FA22B889CB782CE335C41
candidate SHA-256: 7C9BE25943F79C851CE06C5F4709763D66BCF6C8B79FA22B889CB782CE335C41
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342650_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342650_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342650_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342650_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1342863
original SHA-256: 97FEC288B3B72EC0D736BD5CC5780EC0A43A7785930F9C6EC6EF34A06108C5DB
candidate SHA-256: 97FEC288B3B72EC0D736BD5CC5780EC0A43A7785930F9C6EC6EF34A06108C5DB
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342863_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342863_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342863_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342863_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

