# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:828671
original SHA-256: E46BB11EA1661E05FB8732DDE16D7324915DC51977A5878FD6A680B68329F762
candidate SHA-256: E46BB11EA1661E05FB8732DDE16D7324915DC51977A5878FD6A680B68329F762
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [24, 24]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 24]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828671_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828671_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828671_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828671_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828671_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828671_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828671_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828671_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828671_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828671_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828671_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828671_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828671_0024.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:828680
original SHA-256: 969F857C4AB1C6045C26FD597D03A7496A4BBDAC58DBB857AF65B545FC23B3DD
candidate SHA-256: 969F857C4AB1C6045C26FD597D03A7496A4BBDAC58DBB857AF65B545FC23B3DD
원문 frame 패킷: [1, 45]
최종 full_diff 패킷: [90, 90]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 90]
후보 중복만 있는 생략 가능 패킷: [46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0038.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0039.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0040.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0041.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0042.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0043.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0044.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0045.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828680_0090.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:828779
original SHA-256: 2DEFDB468090EDE442879743D5DD78984CFCF1F00DF71C61B0A54AEBE4A41F22
candidate SHA-256: 2DEFDB468090EDE442879743D5DD78984CFCF1F00DF71C61B0A54AEBE4A41F22
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828779_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828779_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:828867
original SHA-256: 58C57721F44410450CC7660784F1F3880B1AB3101FC6A34E16077F3E0E875D00
candidate SHA-256: 3C080AD0C37C424E7972783930DD2B28E9BF01346A99DE77485F55EBC269F281
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:829047
original SHA-256: 05B4B5E5E7AF386F22BD88937C8B97AC450DC6CD43B4418ABD7559A2527D3CBB
candidate SHA-256: 05B4B5E5E7AF386F22BD88937C8B97AC450DC6CD43B4418ABD7559A2527D3CBB
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_829047_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_829047_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_829047_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_829047_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_829047_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_829047_0010.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

