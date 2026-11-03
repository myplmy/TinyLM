# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:663851
original SHA-256: 6496482CD23D4EFE08530EED1EE4128AF9AF9C081F08CEE3FA87586EE12277F4
candidate SHA-256: 6496482CD23D4EFE08530EED1EE4128AF9AF9C081F08CEE3FA87586EE12277F4
원문 frame 패킷: [1, 44]
최종 full_diff 패킷: [88, 88]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 88]
후보 중복만 있는 생략 가능 패킷: [45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0038.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0039.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0040.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0041.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0042.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0043.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0044.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663851_0088.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:663998
original SHA-256: 9890B312EE9E24DA765475CA244751408DA5CA1D46B83AEFDDE536E851EC7AF5
candidate SHA-256: 9890B312EE9E24DA765475CA244751408DA5CA1D46B83AEFDDE536E851EC7AF5
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663998_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:664028
original SHA-256: 7822E86500C4ADAE5521BE3F6B01469A903A01C5BEA3D5F241759170C67B6A98
candidate SHA-256: 7822E86500C4ADAE5521BE3F6B01469A903A01C5BEA3D5F241759170C67B6A98
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_664028_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_664028_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_664028_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_664028_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_664028_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:664213
original SHA-256: 44C963C91A8BFCE9463F9A87D2E29592F72DD60C5ACD7D49133283BB2AA82C82
candidate SHA-256: 44C963C91A8BFCE9463F9A87D2E29592F72DD60C5ACD7D49133283BB2AA82C82
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_664213_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_664213_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_664213_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:664387
original SHA-256: A2B439AD0D7BDE86B2CD998368DAF26CEF1D328822AF36ACBBE9F1102B8F155B
candidate SHA-256: A2B439AD0D7BDE86B2CD998368DAF26CEF1D328822AF36ACBBE9F1102B8F155B
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_664387_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_664387_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_664387_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

