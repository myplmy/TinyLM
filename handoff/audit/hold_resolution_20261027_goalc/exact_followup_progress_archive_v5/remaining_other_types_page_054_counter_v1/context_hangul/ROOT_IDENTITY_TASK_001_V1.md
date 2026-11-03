# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:689939
original SHA-256: 3299C741A15BC53E60D616C7BBCF0610F32A8831742DD3C6A78C476E3423D268
candidate SHA-256: 3299C741A15BC53E60D616C7BBCF0610F32A8831742DD3C6A78C476E3423D268
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_689939_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:689955
original SHA-256: C6F48B5D8411DDBDA7DF33E90B3BFAB9056DE203C4B1620758FD4C89E6165809
candidate SHA-256: C6F48B5D8411DDBDA7DF33E90B3BFAB9056DE203C4B1620758FD4C89E6165809
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_689955_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:689996
original SHA-256: 8670E15180C8B4F56650E6C7194BF5E4BE30C1548C9C28842B84F4DB58CBEB86
candidate SHA-256: 8670E15180C8B4F56650E6C7194BF5E4BE30C1548C9C28842B84F4DB58CBEB86
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_689996_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:690027
original SHA-256: 0E042D031FE01C545CEEC4A5570E2A20493B2DD414147117729C3CE366BDA2D9
candidate SHA-256: 0E042D031FE01C545CEEC4A5570E2A20493B2DD414147117729C3CE366BDA2D9
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690027_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:690031
original SHA-256: 57C61F81B2188BAD23B9736595A1718B939B638C083C2C395B930E2BCC4CFA9A
candidate SHA-256: 57C61F81B2188BAD23B9736595A1718B939B638C083C2C395B930E2BCC4CFA9A
원문 frame 패킷: [1, 45]
최종 full_diff 패킷: [89, 89]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 89]
후보 중복만 있는 생략 가능 패킷: [46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0038.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0039.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0040.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0041.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0042.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0043.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0044.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0045.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_054_counter_v1/reading_packets_v1/expanded_train_690031_0089.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

