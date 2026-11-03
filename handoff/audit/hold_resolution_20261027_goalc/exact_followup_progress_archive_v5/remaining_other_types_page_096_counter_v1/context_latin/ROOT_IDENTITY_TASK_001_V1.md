# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1381560
original SHA-256: 67545DD42D70FE19A37F4E22CBEAEB0817F441EB1BF14ECBFC4CD7C793CE3379
candidate SHA-256: 67545DD42D70FE19A37F4E22CBEAEB0817F441EB1BF14ECBFC4CD7C793CE3379
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381560_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381560_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381560_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381560_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381560_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1381565
original SHA-256: 0912CC2A712F36A7C579982C3D0BF3D01887A962DC140638DE95B47FAA495934
candidate SHA-256: 0912CC2A712F36A7C579982C3D0BF3D01887A962DC140638DE95B47FAA495934
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381565_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381565_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381565_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381565_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1381728
original SHA-256: F00594F575E7DC1D65170407FC6DE5AB8A4B05FDD5064929E8D6E4DA75E881C5
candidate SHA-256: F00594F575E7DC1D65170407FC6DE5AB8A4B05FDD5064929E8D6E4DA75E881C5
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381728_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381728_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381728_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381728_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381728_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1382138
original SHA-256: E9C404A4E167ED503BDA6538C0559BC587648523BA3B98A1DC79251F760EA16E
candidate SHA-256: E9C404A4E167ED503BDA6538C0559BC587648523BA3B98A1DC79251F760EA16E
원문 frame 패킷: [1, 32]
최종 full_diff 패킷: [64, 64]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 64]
후보 중복만 있는 생략 가능 패킷: [33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382138_0064.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1382276
original SHA-256: B9ED1C680EF3DAFC8032F36815A50ECBE784382AF6C2F9043773FCF8855FAEA2
candidate SHA-256: B9ED1C680EF3DAFC8032F36815A50ECBE784382AF6C2F9043773FCF8855FAEA2
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382276_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382276_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382276_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382276_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

