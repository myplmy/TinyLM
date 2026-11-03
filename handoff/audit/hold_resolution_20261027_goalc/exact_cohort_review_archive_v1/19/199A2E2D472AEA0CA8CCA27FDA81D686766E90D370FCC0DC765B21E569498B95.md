# 동일 입력 판독 연결: TASK_007

총괄이 실제 원문/후보 바이트·SHA와 순서 패킷 전체를 검산한 추가 계획이다.
아래 동일성 증명이 있는 ID만 적용한다. 원문 전문은 첫 문자부터 실제 END까지 실제 읽고,
candidate는 정확 바이트 동일성으로 연결하며 full_diff 프레임의 끝까지 읽는다.
이를 원문/후보 두 번의 독립 판독으로 기록하지 않는다. 새 수정 TXT는 전문 재열람과 전체 diff를 계속 확인한다.
TASK의 모든 ID는 각각 리뷰에 포함한다. READING_VIEWS는 경로 인덱스이며 전체 인덱스 EOF의 반복 판독은 불필요하다.
서로 다른 후보는 기존 전문/후보/전체diff와 모든 패킷을 그대로 읽는다.
기존 허용·금지·보호 경계와 다른 역할 접근 금지는 유지한다.
controls는 아래 정확 고정 reader 명령만 사용한다. 다른 역할은 아래 정확 cat 경로를 쓴다.

## expanded_train:115621
original SHA-256: 795EAA39367887827A0A83DC1C5A05C66CCF98C477218759C8F9843EDB2C61E9
candidate SHA-256: 795EAA39367887827A0A83DC1C5A05C66CCF98C477218759C8F9843EDB2C61E9
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 10]
full_diff 프레임 패킷: [19, 19]
중복 후보만 포함해 생략 가능한 패킷: [11, 12, 13, 14, 15, 16, 17, 18]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_115621_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_115621_0002.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_115621_0003.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_115621_0004.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_115621_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_115621_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_115621_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_115621_0008.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_115621_0009.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_115621_0010.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_115621_0019.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1162095
original SHA-256: 0D885ED623FB5F5E2A2A4EF87DFABA50488D6421946DE7A8938EAC3882145205
candidate SHA-256: 0D885ED623FB5F5E2A2A4EF87DFABA50488D6421946DE7A8938EAC3882145205
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 1]
full_diff 프레임 패킷: [2, 2]
중복 후보만 포함해 생략 가능한 패킷: []
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1162095_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1162095_0002.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1156872
original SHA-256: D958640517FBB5375C61CD02C671906CD1F6FFD8A501770FF7881D910EB315E6
candidate SHA-256: D958640517FBB5375C61CD02C671906CD1F6FFD8A501770FF7881D910EB315E6
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 3]
full_diff 프레임 패킷: [6, 6]
중복 후보만 포함해 생략 가능한 패킷: [4, 5]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1156872_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1156872_0002.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1156872_0003.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1156872_0006.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1155366
original SHA-256: 3BF1DD7E79ABA608FC9C87037F607DB323AE1AAA90934352C06FC27B3BBC4151
candidate SHA-256: 3BF1DD7E79ABA608FC9C87037F607DB323AE1AAA90934352C06FC27B3BBC4151
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 3]
full_diff 프레임 패킷: [6, 6]
중복 후보만 포함해 생략 가능한 패킷: [4, 5]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1155366_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1155366_0002.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1155366_0003.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1155366_0006.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1163811
original SHA-256: 3A999F445D8FB8829E9B31A40A5782654F74D2638F3B95BD4D92D5C59F23D951
candidate SHA-256: 3A999F445D8FB8829E9B31A40A5782654F74D2638F3B95BD4D92D5C59F23D951
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 2]
full_diff 프레임 패킷: [4, 4]
중복 후보만 포함해 생략 가능한 패킷: [3]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1163811_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1163811_0002.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1163811_0004.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

