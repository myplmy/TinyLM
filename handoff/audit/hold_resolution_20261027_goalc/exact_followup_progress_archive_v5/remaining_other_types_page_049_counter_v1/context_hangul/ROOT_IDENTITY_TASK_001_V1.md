# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:622059
original SHA-256: 59C6FBBEF2E6228CEC3D52FBD0460FA42437FDF662A7541C5588D71D5B7B14D8
candidate SHA-256: 59C6FBBEF2E6228CEC3D52FBD0460FA42437FDF662A7541C5588D71D5B7B14D8
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622059_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:622061
original SHA-256: ED7E6050D2C8E8C29F0D85A1FCB0FD6A3348614E8CCCF2AF4128B9FB85ACF0DA
candidate SHA-256: ED7E6050D2C8E8C29F0D85A1FCB0FD6A3348614E8CCCF2AF4128B9FB85ACF0DA
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622061_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622061_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622061_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622061_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622061_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:622239
original SHA-256: 37711A2B4D926B04713AF0AF63C8136910C61A9CE9A45320A8B64DCEA6C29FB1
candidate SHA-256: 37711A2B4D926B04713AF0AF63C8136910C61A9CE9A45320A8B64DCEA6C29FB1
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622239_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622239_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622239_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622239_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:622502
original SHA-256: E6EBDDBB0FC315DC8F4241C0BAC4DA5C4DA76E2171D5ACBD44A12AD8DA73224F
candidate SHA-256: E6EBDDBB0FC315DC8F4241C0BAC4DA5C4DA76E2171D5ACBD44A12AD8DA73224F
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [24, 24]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 24]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622502_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622502_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622502_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622502_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622502_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622502_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622502_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622502_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622502_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622502_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622502_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622502_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622502_0024.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:622624
original SHA-256: 34DE1D82EF243AA0AA65F71DF9E8F51CC9910616AC6E880A229C6113645E5369
candidate SHA-256: 34DE1D82EF243AA0AA65F71DF9E8F51CC9910616AC6E880A229C6113645E5369
원문 frame 패킷: [1, 14]
최종 full_diff 패킷: [27, 27]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 27]
후보 중복만 있는 생략 가능 패킷: [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622624_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622624_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622624_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622624_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622624_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622624_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622624_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622624_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622624_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622624_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622624_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622624_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622624_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622624_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622624_0027.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

