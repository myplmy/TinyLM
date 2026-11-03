# 동일 입력 판독 연결: TASK_023

총괄이 실제 원문/후보 바이트·SHA와 순서 패킷 전체를 검산한 추가 계획이다.
아래 동일성 증명이 있는 ID만 적용한다. 원문 전문은 첫 문자부터 실제 END까지 실제 읽고,
candidate는 정확 바이트 동일성으로 연결하며 full_diff 프레임의 끝까지 읽는다.
이를 원문/후보 두 번의 독립 판독으로 기록하지 않는다. 새 수정 TXT는 전문 재열람과 전체 diff를 계속 확인한다.
TASK의 모든 ID는 각각 리뷰에 포함한다. READING_VIEWS는 경로 인덱스이며 전체 인덱스 EOF의 반복 판독은 불필요하다.
서로 다른 후보는 기존 전문/후보/전체diff와 모든 패킷을 그대로 읽는다.
기존 허용·금지·보호 경계와 다른 역할 접근 금지는 유지한다.
controls는 아래 정확 고정 reader 명령만 사용한다. 다른 역할은 아래 정확 cat 경로를 쓴다.

## expanded_train:1375564
original SHA-256: 2F532220D294B619D563E6FFA352A19517D614B0010A25E5AC5DE0C280A14A90
candidate SHA-256: 2F532220D294B619D563E6FFA352A19517D614B0010A25E5AC5DE0C280A14A90
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 1]
full_diff 프레임 패킷: [2, 2]
중복 후보만 포함해 생략 가능한 패킷: []
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1375564_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1375564_0002.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1387411
original SHA-256: 8587B04F5DA91680AB45454D71E49D7E4DF4DE8D4C29FE3649A6730DE6471676
candidate SHA-256: 8587B04F5DA91680AB45454D71E49D7E4DF4DE8D4C29FE3649A6730DE6471676
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 2]
full_diff 프레임 패킷: [4, 4]
중복 후보만 포함해 생략 가능한 패킷: [3]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1387411_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1387411_0002.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1387411_0004.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1390696
original SHA-256: 7028997BDAB993FB5FCF872AC32C57095980F1F4FE0772864ED86081F0C130AC
candidate SHA-256: 7028997BDAB993FB5FCF872AC32C57095980F1F4FE0772864ED86081F0C130AC
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 5]
full_diff 프레임 패킷: [10, 10]
중복 후보만 포함해 생략 가능한 패킷: [6, 7, 8, 9]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1390696_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1390696_0002.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1390696_0003.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1390696_0004.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1390696_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1390696_0010.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1386367
original SHA-256: CA278F0FEC51951928F9B0E2D660E67574F8BE96F7DDA0C0912307A10F997B0F
candidate SHA-256: CA278F0FEC51951928F9B0E2D660E67574F8BE96F7DDA0C0912307A10F997B0F
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 1]
full_diff 프레임 패킷: [1, 1]
중복 후보만 포함해 생략 가능한 패킷: []
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1386367_0001.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1367479
original SHA-256: 661C06A65DA863DA6260528968BE603A7BF2159ECA754E6BA15D454EDF27DAC8
candidate SHA-256: 661C06A65DA863DA6260528968BE603A7BF2159ECA754E6BA15D454EDF27DAC8
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 1]
full_diff 프레임 패킷: [1, 1]
중복 후보만 포함해 생략 가능한 패킷: []
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1367479_0001.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

