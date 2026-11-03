# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1219526
original SHA-256: 18CE1AB925EC669AAB7338CC798D19116DB56FC30AF9CFFA113A44A4D81DE33E
candidate SHA-256: 18CE1AB925EC669AAB7338CC798D19116DB56FC30AF9CFFA113A44A4D81DE33E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219526_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1219565
original SHA-256: ABDBE5B75E7F2C158A785DEDD7B2B2DDCA951B629FB9968A77810343AFC928A0
candidate SHA-256: ABDBE5B75E7F2C158A785DEDD7B2B2DDCA951B629FB9968A77810343AFC928A0
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219565_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219565_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219565_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219565_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219565_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219565_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219565_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1219565_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1220009
original SHA-256: 9644440D7A97829D8F1AC0FFF65C64BE745DFB7A41E1C744A560A95690CE8E78
candidate SHA-256: E597A4FE6F894AAC6BB50BD4A21A0427470162BF052EBD0478D95565F21BBEAF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1220051
original SHA-256: 7B0D60E82F4205C7F33C206136B602FF135B8427A62B0DFE57ED135BCD969BCB
candidate SHA-256: 7B0D60E82F4205C7F33C206136B602FF135B8427A62B0DFE57ED135BCD969BCB
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220051_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220051_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1220248
original SHA-256: CEB81A0D20D060C375CA100062BDA3553ED12C9C05DB23C9B6BE894ABDF02BF2
candidate SHA-256: CEB81A0D20D060C375CA100062BDA3553ED12C9C05DB23C9B6BE894ABDF02BF2
원문 frame 패킷: [1, 23]
최종 full_diff 패킷: [45, 45]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 45]
후보 중복만 있는 생략 가능 패킷: [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_087_counter_v1/reading_packets_v1/expanded_train_1220248_0045.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

