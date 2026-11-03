# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1401925
original SHA-256: 54054FFB137A819E7002D258E85593EBEBE080BCBB0A4B7FDDEA40C3D6BCFA51
candidate SHA-256: 54054FFB137A819E7002D258E85593EBEBE080BCBB0A4B7FDDEA40C3D6BCFA51
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401925_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401925_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401925_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1402001
original SHA-256: C879E40016D9D6ED5340A1BCA099841F96405A88E79EE7EADF16BD82A4650D13
candidate SHA-256: C879E40016D9D6ED5340A1BCA099841F96405A88E79EE7EADF16BD82A4650D13
원문 frame 패킷: [1, 16]
최종 full_diff 패킷: [31, 31]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 31]
후보 중복만 있는 생략 가능 패킷: [17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402001_0031.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1402076
original SHA-256: 820D469CFAA71D1ACD71747F562A679107AB0D696476917CCDC7DE41C18C63CA
candidate SHA-256: 820D469CFAA71D1ACD71747F562A679107AB0D696476917CCDC7DE41C18C63CA
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 15]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14, 15]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402076_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402076_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402076_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402076_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402076_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402076_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402076_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402076_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402076_0015.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1402173
original SHA-256: 7785742E127EE7AF72D8532FFD850803DC19188284B45B4B85FACF00462350D2
candidate SHA-256: 7785742E127EE7AF72D8532FFD850803DC19188284B45B4B85FACF00462350D2
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402173_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402173_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402173_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402173_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402173_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402173_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1402450
original SHA-256: 6F70D3118D4684CD4E9DA0099B81F26FD70E42F8E4409568062E8AEF847D383A
candidate SHA-256: 6F70D3118D4684CD4E9DA0099B81F26FD70E42F8E4409568062E8AEF847D383A
원문 frame 패킷: [1, 33]
최종 full_diff 패킷: [66, 66]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 66]
후보 중복만 있는 생략 가능 패킷: [34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402450_0066.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

