# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:231513
original SHA-256: 53DAA5A6F47370FCD42EFB285C62245F666BDCB9B63B69C9A3AFCE7DF6CEE3A3
candidate SHA-256: 53DAA5A6F47370FCD42EFB285C62245F666BDCB9B63B69C9A3AFCE7DF6CEE3A3
원문 frame 패킷: [1, 40]
최종 full_diff 패킷: [80, 80]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 80]
후보 중복만 있는 생략 가능 패킷: [41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0038.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0039.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0040.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231513_0080.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:231691
original SHA-256: FBCB21D1C9DED500DE4A4789517861EBDF5E0837430D2B29D96405C0E768EABA
candidate SHA-256: BE50F337A08FDA50B889DE1E9ED4105FF6C37A8E9A124461C4B7108EE25B9AEC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:231713
original SHA-256: 3A297E22B1B2B77BBE7318ABD72B9EDC6A6D9896972C80C0DE16DEB72A1EF6FD
candidate SHA-256: 3A297E22B1B2B77BBE7318ABD72B9EDC6A6D9896972C80C0DE16DEB72A1EF6FD
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231713_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231713_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231713_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231713_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231713_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:231769
original SHA-256: C18BB2C4A99F1205C6A95662E7BC05A6203206A7F28114ED07B0803EA2F09783
candidate SHA-256: C18BB2C4A99F1205C6A95662E7BC05A6203206A7F28114ED07B0803EA2F09783
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12, 13]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231769_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231769_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231769_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231769_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231769_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231769_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231769_0012.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231769_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:231800
original SHA-256: 70FF1A9300B10EA199BDFB4629A5246FDBBC2CEA51136D11D624493803139485
candidate SHA-256: 70FF1A9300B10EA199BDFB4629A5246FDBBC2CEA51136D11D624493803139485
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231800_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231800_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231800_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231800_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231800_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

