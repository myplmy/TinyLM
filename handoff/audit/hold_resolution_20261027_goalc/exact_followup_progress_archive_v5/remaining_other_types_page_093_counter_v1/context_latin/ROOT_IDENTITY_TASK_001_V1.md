# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1322612
original SHA-256: 364B213DBBA9297124908EDEA04D6CC907F107DEEE0EB9E686DC70359E5D27D8
candidate SHA-256: 364B213DBBA9297124908EDEA04D6CC907F107DEEE0EB9E686DC70359E5D27D8
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322612_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322612_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322612_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322612_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1322731
original SHA-256: DD70FD227CD9C2C1B22DC0336E116A706F77989B2BB4D4024B3B742BD4D6A5EE
candidate SHA-256: DD70FD227CD9C2C1B22DC0336E116A706F77989B2BB4D4024B3B742BD4D6A5EE
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322731_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322731_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322731_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322731_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322731_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1322912
original SHA-256: 4D2D8C3C8EC3564BA8A4ECAFCDFD0F8F9980EC6D60808F0825F8A64F90C40A96
candidate SHA-256: 4D2D8C3C8EC3564BA8A4ECAFCDFD0F8F9980EC6D60808F0825F8A64F90C40A96
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322912_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322912_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322912_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322912_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1323212
original SHA-256: FA0A1AAE2800BE6B198A00F803107509CE68677722DDD463D5822574BF786DEC
candidate SHA-256: FA0A1AAE2800BE6B198A00F803107509CE68677722DDD463D5822574BF786DEC
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323212_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323212_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323212_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323212_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323212_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323212_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323212_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1323272
original SHA-256: A45932B6DA5959133CB9DFCF0F97AFDE445986CB896AEAE7173BE4F9D4B6A2DC
candidate SHA-256: A45932B6DA5959133CB9DFCF0F97AFDE445986CB896AEAE7173BE4F9D4B6A2DC
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323272_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323272_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323272_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

