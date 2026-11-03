# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1045920
original SHA-256: BCDBB06EE3B20A4145EFB3931DC62773CEAAD3F39341832772DF150D371B0B5E
candidate SHA-256: BCDBB06EE3B20A4145EFB3931DC62773CEAAD3F39341832772DF150D371B0B5E
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [20, 20]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18, 19]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1045920_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1045920_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1045920_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1045920_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1045920_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1045920_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1045920_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1045920_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1045920_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1045920_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1045920_0020.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1046114
original SHA-256: 80F07CFB33F156A88B20DBC36342D335372A14C79A305C2E5D851D426E5C8231
candidate SHA-256: 80F07CFB33F156A88B20DBC36342D335372A14C79A305C2E5D851D426E5C8231
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1046114_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1046141
original SHA-256: D127C9836E10580FD3DBA56C9B9C5BD28B71CE24E2CFA9EA163090D3EC9031B4
candidate SHA-256: D127C9836E10580FD3DBA56C9B9C5BD28B71CE24E2CFA9EA163090D3EC9031B4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1046141_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1046161
original SHA-256: 9B713C17F1334C6B58B5C73A593BF30993E38B6B9FE74C04599AD8BDA0C398E5
candidate SHA-256: 9B713C17F1334C6B58B5C73A593BF30993E38B6B9FE74C04599AD8BDA0C398E5
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1046161_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1046169
original SHA-256: F40C7444C12B6BB1BB5E4599421808870D0DB0C11FED41A6127CF4400E8BE6B4
candidate SHA-256: F40C7444C12B6BB1BB5E4599421808870D0DB0C11FED41A6127CF4400E8BE6B4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1046169_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1046169_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

