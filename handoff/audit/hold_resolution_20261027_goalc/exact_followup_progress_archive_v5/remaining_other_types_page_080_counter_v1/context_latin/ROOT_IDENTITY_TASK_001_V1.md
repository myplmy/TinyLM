# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1101805
original SHA-256: 7BB5394929C60E1EB9FD41312434E4A7CB4EECC4916BA5FA8DE5CD562DCC0367
candidate SHA-256: 7BB5394929C60E1EB9FD41312434E4A7CB4EECC4916BA5FA8DE5CD562DCC0367
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101805_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101805_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101805_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101805_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101805_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101805_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101805_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1101914
original SHA-256: E570107B7E5F7BE50333B5BED776CFF7640F1926EDA14DC16BBC718D33FE39DC
candidate SHA-256: E570107B7E5F7BE50333B5BED776CFF7640F1926EDA14DC16BBC718D33FE39DC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101914_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101914_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1102093
original SHA-256: A3DDE9061C43EB3425F1B7BDEB2231397540124A3EF6F878F63521D84DA62EFB
candidate SHA-256: A3DDE9061C43EB3425F1B7BDEB2231397540124A3EF6F878F63521D84DA62EFB
원문 frame 패킷: [1, 13]
최종 full_diff 패킷: [25, 25]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 25]
후보 중복만 있는 생략 가능 패킷: [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102093_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102093_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102093_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102093_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102093_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102093_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102093_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102093_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102093_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102093_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102093_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102093_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102093_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102093_0025.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1102291
original SHA-256: 915D1BE9F389D278F9371B73140846A4C43F93117765737DAF5231693E89063B
candidate SHA-256: 915D1BE9F389D278F9371B73140846A4C43F93117765737DAF5231693E89063B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102291_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102291_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1102924
original SHA-256: BEC46790BE82574DB1E6D20F47AB8F21E5DDF241DFDA05FA969C4F41192FB3E6
candidate SHA-256: BEC46790BE82574DB1E6D20F47AB8F21E5DDF241DFDA05FA969C4F41192FB3E6
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102924_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

