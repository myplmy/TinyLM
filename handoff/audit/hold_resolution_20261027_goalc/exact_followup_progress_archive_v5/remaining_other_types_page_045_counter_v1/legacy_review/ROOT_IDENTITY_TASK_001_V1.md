# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:561536
original SHA-256: CC16D29596FF20F68F065FA053336D79F4BAE6D3B5E5C5D0413EABB5F9D29562
candidate SHA-256: CC16D29596FF20F68F065FA053336D79F4BAE6D3B5E5C5D0413EABB5F9D29562
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561536_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561536_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561536_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561536_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561536_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:561538
original SHA-256: 2543771C7F973B3BDCBB36DA1A6DDA06718573DE417CA41B0E08623DCC27DC0C
candidate SHA-256: 2543771C7F973B3BDCBB36DA1A6DDA06718573DE417CA41B0E08623DCC27DC0C
원문 frame 패킷: [1, 53]
최종 full_diff 패킷: [106, 106]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 106]
후보 중복만 있는 생략 가능 패킷: [54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0038.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0039.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0040.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0041.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0042.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0043.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0044.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0045.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0046.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0047.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0048.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0049.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0050.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0051.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0052.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0053.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561538_0106.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:561660
original SHA-256: 2F0C1286DE2366448981FB217799468C0AD5BB5BFAE47F12CE1A05A63248840E
candidate SHA-256: 2F0C1286DE2366448981FB217799468C0AD5BB5BFAE47F12CE1A05A63248840E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561660_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:561708
original SHA-256: 2F5CDFCABC67839FDCBA57C7172E5AB89C38802DEB8B1318CC9ACFC95CF49503
candidate SHA-256: 2F5CDFCABC67839FDCBA57C7172E5AB89C38802DEB8B1318CC9ACFC95CF49503
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561708_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561708_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561708_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561708_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:561929
original SHA-256: A2A5277C6499C08C506757935B57363F410C9AFD0705B77511E8489B9AABC907
candidate SHA-256: A2A5277C6499C08C506757935B57363F410C9AFD0705B77511E8489B9AABC907
원문 frame 패킷: [1, 14]
최종 full_diff 패킷: [27, 27]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 27]
후보 중복만 있는 생략 가능 패킷: [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561929_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561929_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561929_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561929_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561929_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561929_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561929_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561929_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561929_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561929_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561929_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561929_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561929_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561929_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561929_0027.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

