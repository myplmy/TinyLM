# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:386862
original SHA-256: A460114757D46390C1959452D39A238E8F195DEC7625F84436466DB3839FFE65
candidate SHA-256: AAFD3E94F7ACB4534822C97480FFC8DD0A3DF9F5982C7E954883E03592E07074
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:387030
original SHA-256: 4D4C7AA8A26FD9E8EAC8116B0C4C1BE166FD544FB46505DDDD83E3761F19F22F
candidate SHA-256: 4D4C7AA8A26FD9E8EAC8116B0C4C1BE166FD544FB46505DDDD83E3761F19F22F
원문 frame 패킷: [1, 11]
최종 full_diff 패킷: [22, 22]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 22]
후보 중복만 있는 생략 가능 패킷: [12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387030_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387030_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387030_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387030_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387030_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387030_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387030_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387030_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387030_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387030_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387030_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387030_0022.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:387257
original SHA-256: 4EE3F2C851AE9CE08DAE1DAA8826A955C8C189677B549596327A00BBB78179EE
candidate SHA-256: 4EE3F2C851AE9CE08DAE1DAA8826A955C8C189677B549596327A00BBB78179EE
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387257_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387257_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387257_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:387276
original SHA-256: 634C93A40AFEBDF91EA73DAB4D8F54FEFEA6DE03A48C0C31F31BEBF7D1D7C67C
candidate SHA-256: 244A115FB3689868FF39864AA68BB1E53EE6E4AA7ADD7D92D7BFBDB5053B7275
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:387484
original SHA-256: AA0019D6AC91643E3EB7DF4CCCCE1053EE4AD8DD45FF2BF9AD0BC7D69885AB67
candidate SHA-256: AC55D21CD8751A4EF31B5EA53BF6F96DA91D0C69EBB5233B221791778179003B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

