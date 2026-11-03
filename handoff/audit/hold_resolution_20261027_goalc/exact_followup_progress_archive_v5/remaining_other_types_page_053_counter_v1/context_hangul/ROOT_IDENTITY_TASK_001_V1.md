# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:678142
original SHA-256: 99A5B45A8878916CB1C639425E43FF39349F969C474356CD08F06C1C489B1674
candidate SHA-256: 99A5B45A8878916CB1C639425E43FF39349F969C474356CD08F06C1C489B1674
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678142_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:678266
original SHA-256: 20825FE2C4B7CAD5C38A5CC60CEEC024C8CD7236A4B8FA3B5E2480322103ED23
candidate SHA-256: 20825FE2C4B7CAD5C38A5CC60CEEC024C8CD7236A4B8FA3B5E2480322103ED23
원문 frame 패킷: [1, 50]
최종 full_diff 패킷: [100, 100]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 100]
후보 중복만 있는 생략 가능 패킷: [51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0038.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0039.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0040.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0041.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0042.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0043.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0044.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0045.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0046.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0047.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0048.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0049.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0050.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678266_0100.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:678335
original SHA-256: 95217647AB09003B00699A44D5799BAEE90E468D47DF8BF35A9A966664F6D866
candidate SHA-256: 0F33FCEE0AD59625271AA8E49D4C522108CC90ED889BA54634E42E6204E95286
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:678446
original SHA-256: EC44E05CD33DDFF6517C3F02DCD5FA67D74AEEA0BE885CF394871BB36EF2614F
candidate SHA-256: EC44E05CD33DDFF6517C3F02DCD5FA67D74AEEA0BE885CF394871BB36EF2614F
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [20, 20]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18, 19]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678446_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678446_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678446_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678446_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678446_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678446_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678446_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678446_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678446_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678446_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678446_0020.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:678595
original SHA-256: AEFE0B39EB7400F98BB8EA79C4B324F3E67D126802FC1BBDE20A7FFCB7E4C45B
candidate SHA-256: 158333D5369D3A00A8DD5C2E64BE2FB09436B88C979FE6A5DC73884F362E7AD3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

