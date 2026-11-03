# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1000068
original SHA-256: FABA2CD08D387526D9E3F1A5A4C92E1F550923E22078507227DFD2F5650FACBC
candidate SHA-256: FABA2CD08D387526D9E3F1A5A4C92E1F550923E22078507227DFD2F5650FACBC
원문 frame 패킷: [1, 57]
최종 full_diff 패킷: [113, 113]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 113]
후보 중복만 있는 생략 가능 패킷: [58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0038.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0039.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0040.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0041.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0042.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0043.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0044.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0045.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0046.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0047.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0048.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0049.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0050.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0051.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0052.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0053.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0054.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0055.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0056.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0057.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000068_0113.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1000315
original SHA-256: 00B703B6A3F065C850036917F7DD665FF93BA86540B8B1FDA5939D631558D2D1
candidate SHA-256: 00B703B6A3F065C850036917F7DD665FF93BA86540B8B1FDA5939D631558D2D1
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000315_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000315_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000315_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1000491
original SHA-256: A5681404B17ACE9F8FEA410A22DFB4F2D686E0BB4715FA50C739E69EC8AB4D5C
candidate SHA-256: A5681404B17ACE9F8FEA410A22DFB4F2D686E0BB4715FA50C739E69EC8AB4D5C
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000491_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000491_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000491_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000491_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000491_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000491_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1000769
original SHA-256: F66FBB9B81C7237605A4A0E96F109F18259281DE5B25795488C9A68469F471D8
candidate SHA-256: F66FBB9B81C7237605A4A0E96F109F18259281DE5B25795488C9A68469F471D8
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000769_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000769_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000769_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000769_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000769_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1001029
original SHA-256: EAD229821444CB48D72BDBCB98FB3C242813E83AADDE4468DB0A08CF6AFD967A
candidate SHA-256: EAD229821444CB48D72BDBCB98FB3C242813E83AADDE4468DB0A08CF6AFD967A
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [19, 19]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 19]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1001029_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1001029_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1001029_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1001029_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1001029_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1001029_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1001029_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1001029_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1001029_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1001029_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1001029_0019.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

