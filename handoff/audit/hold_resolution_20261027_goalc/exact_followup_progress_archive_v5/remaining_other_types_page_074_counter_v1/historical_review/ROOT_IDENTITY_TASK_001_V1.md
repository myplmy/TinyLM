# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1010434
original SHA-256: 65CDE4FFFD2934FA4A3C8C87B2EFA9F9ADC7788A68CD9B706B385CBAC9BFB4BD
candidate SHA-256: 65CDE4FFFD2934FA4A3C8C87B2EFA9F9ADC7788A68CD9B706B385CBAC9BFB4BD
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010434_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1010930
original SHA-256: DFFBEE4738BAF1CD98A29A3C9E0DFBDFFD587992B02742E1881293862A0136C4
candidate SHA-256: DFFBEE4738BAF1CD98A29A3C9E0DFBDFFD587992B02742E1881293862A0136C4
원문 frame 패킷: [1, 14]
최종 full_diff 패킷: [27, 27]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 27]
후보 중복만 있는 생략 가능 패킷: [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010930_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010930_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010930_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010930_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010930_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010930_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010930_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010930_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010930_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010930_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010930_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010930_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010930_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010930_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010930_0027.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1011252
original SHA-256: 048B3E260D0B27D049E31BD803A34A0FECBDC30A6055AC768408E0193F742C27
candidate SHA-256: 048B3E260D0B27D049E31BD803A34A0FECBDC30A6055AC768408E0193F742C27
원문 frame 패킷: [1, 20]
최종 full_diff 패킷: [39, 39]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 39]
후보 중복만 있는 생략 가능 패킷: [21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011252_0039.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1011357
original SHA-256: 4687F0B3D7E7412310CEA8FCEF81F4E27C5197E37A43FC8354F41AE3E57DDEF7
candidate SHA-256: 4687F0B3D7E7412310CEA8FCEF81F4E27C5197E37A43FC8354F41AE3E57DDEF7
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011357_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011357_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011357_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011357_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1011901
original SHA-256: E14A5B7D2A8CCAA836F5E266B4CD0C26E43DA1B2272BEFC07D04E087D32575D0
candidate SHA-256: E14A5B7D2A8CCAA836F5E266B4CD0C26E43DA1B2272BEFC07D04E087D32575D0
원문 frame 패킷: [1, 41]
최종 full_diff 패킷: [81, 81]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 81]
후보 중복만 있는 생략 가능 패킷: [42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0038.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0039.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0040.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0041.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1011901_0081.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

