# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:431239
original SHA-256: 24647893E9284AAE8C6E43224CC7E6ECB6FD27ECCA2D075BCB2A6C6475C42EA9
candidate SHA-256: 24647893E9284AAE8C6E43224CC7E6ECB6FD27ECCA2D075BCB2A6C6475C42EA9
원문 frame 패킷: [1, 38]
최종 full_diff 패킷: [76, 76]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 76]
후보 중복만 있는 생략 가능 패킷: [39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0038.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431239_0076.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:431270
original SHA-256: 93398FCFFF006E8E717A4B1684176483293557CCF458F5AA87F036C1ACF60675
candidate SHA-256: 93398FCFFF006E8E717A4B1684176483293557CCF458F5AA87F036C1ACF60675
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431270_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431270_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431270_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431270_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:431286
original SHA-256: D97565C3BB165011881589F41DF9541620EF4547F710B6CD26FA592C940E497F
candidate SHA-256: D97565C3BB165011881589F41DF9541620EF4547F710B6CD26FA592C940E497F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431286_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:431287
original SHA-256: AD47A9DAC6C4A3E49B717B6C03564B055B44F2C4F103CCCA2FC5AE1C246F1F73
candidate SHA-256: AD47A9DAC6C4A3E49B717B6C03564B055B44F2C4F103CCCA2FC5AE1C246F1F73
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431287_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:431417
original SHA-256: 56BBE162BEC0DA3071FB0C086002D90D05A440D17E7E2B2970EDB14F0816373F
candidate SHA-256: DB573818CC0E301EE0F5ECB431E2D77336AEC3720F9552BDBD4C7CC6439F2441
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

