# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:294505
original SHA-256: 77030B539B5DD148E2E0669B6C724DDE063A6A1BC37513D6108AD8527318CE0C
candidate SHA-256: 77030B539B5DD148E2E0669B6C724DDE063A6A1BC37513D6108AD8527318CE0C
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294505_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294505_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294505_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294505_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294505_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:294653
original SHA-256: FCD9FCF161AB94A4A6A8081BB6BA0F9830AA9639A4BDEABBB4079B7DC4E4D28D
candidate SHA-256: 7D2B76A00354A6243299EF6738DDD9BD86B9AC6E3373B8EB8F050D5FAD69FCDA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:294657
original SHA-256: A0D21BDBA22565ECD048DC9E77D1AD4D08A0C4C8C595C0251E4838EAE74A501D
candidate SHA-256: A0D21BDBA22565ECD048DC9E77D1AD4D08A0C4C8C595C0251E4838EAE74A501D
원문 frame 패킷: [1, 35]
최종 full_diff 패킷: [69, 69]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 69]
후보 중복만 있는 생략 가능 패킷: [36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294657_0069.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:294832
original SHA-256: EFBFA221827F64C2F89CEB03F42FCECD2BF4616E4015AEEF7DF6D51FF9A1F543
candidate SHA-256: C2DE3DB7D3FF9887073E35A5422C954F70B6B7EDFF3AD47AEC23A8FACD92F36F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:294854
original SHA-256: 92F3E6D91620329E665A5D78382B53A840437B3CEF352D53B060A00D88D6318B
candidate SHA-256: 884398BE731033D2AEF091CE606F4BD2DFB51C9D31D85D0D6C2F8EC6ECE33E57
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

