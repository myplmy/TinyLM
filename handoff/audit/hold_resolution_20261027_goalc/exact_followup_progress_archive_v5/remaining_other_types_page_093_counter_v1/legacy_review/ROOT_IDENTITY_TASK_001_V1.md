# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1322666
original SHA-256: 821569761C18F13015D78A8C30C4F3529C9C70216B3814F86BE5F1E7CBC9DC8A
candidate SHA-256: 821569761C18F13015D78A8C30C4F3529C9C70216B3814F86BE5F1E7CBC9DC8A
원문 frame 패킷: [1, 13]
최종 full_diff 패킷: [26, 26]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 26]
후보 중복만 있는 생략 가능 패킷: [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322666_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322666_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322666_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322666_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322666_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322666_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322666_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322666_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322666_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322666_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322666_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322666_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322666_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322666_0026.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1322718
original SHA-256: 9D19F6ABF596DDDC985530E712F87EC811740DA4B353FC8690465061B1B69A6C
candidate SHA-256: 9D19F6ABF596DDDC985530E712F87EC811740DA4B353FC8690465061B1B69A6C
원문 frame 패킷: [1, 34]
최종 full_diff 패킷: [68, 68]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 68]
후보 중복만 있는 생략 가능 패킷: [35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322718_0068.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1322859
original SHA-256: 236B45535331F1D1D8CFED4469C05DD91B8498E7AEE86928C08CF5EB881BF461
candidate SHA-256: 236B45535331F1D1D8CFED4469C05DD91B8498E7AEE86928C08CF5EB881BF461
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322859_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322859_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322859_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1323226
original SHA-256: 590E5CF8B960728C05836AD00C4319AC0E61DB083FE6BCC213102292163CAEEC
candidate SHA-256: 590E5CF8B960728C05836AD00C4319AC0E61DB083FE6BCC213102292163CAEEC
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [24, 24]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 24]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323226_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323226_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323226_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323226_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323226_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323226_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323226_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323226_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323226_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323226_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323226_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323226_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323226_0024.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1323410
original SHA-256: 24E9B65564F122CC8AFC73B23A6EAEE73315669D0059A26AE39DDEB4F21F3D58
candidate SHA-256: 24E9B65564F122CC8AFC73B23A6EAEE73315669D0059A26AE39DDEB4F21F3D58
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323410_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323410_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323410_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323410_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

