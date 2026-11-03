# 동일 입력 판독 연결: TASK_042

총괄이 실제 원문/후보 바이트·SHA와 순서 패킷 전체를 검산한 추가 계획이다.
아래 동일성 증명이 있는 ID만 적용한다. 원문 전문은 첫 문자부터 실제 END까지 실제 읽고,
candidate는 정확 바이트 동일성으로 연결하며 full_diff 프레임의 끝까지 읽는다.
이를 원문/후보 두 번의 독립 판독으로 기록하지 않는다. 새 수정 TXT는 전문 재열람과 전체 diff를 계속 확인한다.
TASK의 모든 ID는 각각 리뷰에 포함한다. READING_VIEWS는 경로 인덱스이며 전체 인덱스 EOF의 반복 판독은 불필요하다.
서로 다른 후보는 기존 전문/후보/전체diff와 모든 패킷을 그대로 읽는다.
기존 허용·금지·보호 경계와 다른 역할 접근 금지는 유지한다.
controls는 아래 정확 고정 reader 명령만 사용한다. 다른 역할은 아래 정확 cat 경로를 쓴다.

## expanded_train:492515
original SHA-256: 98FA4ED455C115D64B79E67B131EF09946EE1E23BD6E74C882B51D96372E018C
candidate SHA-256: 98FA4ED455C115D64B79E67B131EF09946EE1E23BD6E74C882B51D96372E018C
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 7]
full_diff 프레임 패킷: [14, 14]
중복 후보만 포함해 생략 가능한 패킷: [8, 9, 10, 11, 12, 13]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_492515_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_492515_0002.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_492515_0003.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_492515_0004.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_492515_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_492515_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_492515_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_492515_0014.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:483875
original SHA-256: 99434924EF1FF193F9AA965162DCC79D21422AA6146A30A3C389F570FEE95E1D
candidate SHA-256: 99434924EF1FF193F9AA965162DCC79D21422AA6146A30A3C389F570FEE95E1D
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 1]
full_diff 프레임 패킷: [2, 2]
중복 후보만 포함해 생략 가능한 패킷: []
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_483875_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_483875_0002.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:488712
original SHA-256: FF01FCB2FC779350B5E8FC75D7AA2F761A4D2CF2A376200F08A5C45892395F25
candidate SHA-256: FF01FCB2FC779350B5E8FC75D7AA2F761A4D2CF2A376200F08A5C45892395F25
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 5]
full_diff 프레임 패킷: [10, 11]
중복 후보만 포함해 생략 가능한 패킷: [6, 7, 8, 9]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_488712_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_488712_0002.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_488712_0003.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_488712_0004.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_488712_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_488712_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_488712_0011.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:49113
original SHA-256: 209DFE3A359C723B33C029F824D2C6A8F1A3B34338046ED13417B6F85ADB0388
candidate SHA-256: 209DFE3A359C723B33C029F824D2C6A8F1A3B34338046ED13417B6F85ADB0388
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 18]
full_diff 프레임 패킷: [35, 35]
중복 후보만 포함해 생략 가능한 패킷: [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0002.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0003.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0004.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0008.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0009.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0010.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0014.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0015.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0016.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_49113_0035.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:490971
original SHA-256: 6A2A800103EFDFADB2A6CF1D1E1E5DAFFFC9DB82979461B48843162CC10DEF50
candidate SHA-256: 6A2A800103EFDFADB2A6CF1D1E1E5DAFFFC9DB82979461B48843162CC10DEF50
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 6]
full_diff 프레임 패킷: [11, 11]
중복 후보만 포함해 생략 가능한 패킷: [7, 8, 9, 10]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_490971_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_490971_0002.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_490971_0003.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_490971_0004.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_490971_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_490971_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_490971_0011.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

