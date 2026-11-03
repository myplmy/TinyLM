# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1283732
original SHA-256: 8A06FCA27AEB473B2AD03C22F3293DF420808BCE62602509F20E075695D64053
candidate SHA-256: 8A06FCA27AEB473B2AD03C22F3293DF420808BCE62602509F20E075695D64053
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283732_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283732_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283732_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1283751
original SHA-256: 1549AF0D63D4DDBA9F0ABD69532B1675E0F978B9DEB54C5580F34F23AAA01647
candidate SHA-256: 1549AF0D63D4DDBA9F0ABD69532B1675E0F978B9DEB54C5580F34F23AAA01647
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283751_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283751_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283751_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1283876
original SHA-256: 20A5B18C399B8E09F0458BBC81B8D92E8B995FABE1C48D341001361537037401
candidate SHA-256: 20A5B18C399B8E09F0458BBC81B8D92E8B995FABE1C48D341001361537037401
원문 frame 패킷: [1, 75]
최종 full_diff 패킷: [150, 150]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 150]
후보 중복만 있는 생략 가능 패킷: [76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0038.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0039.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0040.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0041.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0042.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0043.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0044.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0045.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0046.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0047.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0048.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0049.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0050.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0051.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0052.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0053.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0054.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0055.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0056.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0057.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0058.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0059.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0060.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0061.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0062.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0063.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0064.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0065.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0066.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0067.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0068.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0069.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0070.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0071.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0072.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0073.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0074.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0075.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283876_0150.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1283910
original SHA-256: 2D85F5F667DDFD02BDF7467AFE32AB2F88BD9F4225CA0A1359150DD955F74026
candidate SHA-256: 2D85F5F667DDFD02BDF7467AFE32AB2F88BD9F4225CA0A1359150DD955F74026
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283910_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283910_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283910_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283910_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283910_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1283910_0010.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1284065
original SHA-256: 45CDDBC931A9D340700A731AE85AA6E7826B99B22838B4A5BCDD812A60CC6884
candidate SHA-256: 45CDDBC931A9D340700A731AE85AA6E7826B99B22838B4A5BCDD812A60CC6884
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284065_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284065_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284065_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284065_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284065_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284065_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284065_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284065_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

