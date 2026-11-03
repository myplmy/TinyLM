# 동일 입력 판독 연결: TASK_020

총괄이 실제 원문/후보 바이트·SHA와 순서 패킷 전체를 검산한 추가 계획이다.
아래 동일성 증명이 있는 ID만 적용한다. 원문 전문은 첫 문자부터 실제 END까지 실제 읽고,
candidate는 정확 바이트 동일성으로 연결하며 full_diff 프레임의 끝까지 읽는다.
이를 원문/후보 두 번의 독립 판독으로 기록하지 않는다. 새 수정 TXT는 전문 재열람과 전체 diff를 계속 확인한다.
TASK의 모든 ID는 각각 리뷰에 포함한다. READING_VIEWS는 경로 인덱스이며 전체 인덱스 EOF의 반복 판독은 불필요하다.
서로 다른 후보는 기존 전문/후보/전체diff와 모든 패킷을 그대로 읽는다.
기존 허용·금지·보호 경계와 다른 역할 접근 금지는 유지한다.
controls는 아래 정확 고정 reader 명령만 사용한다. 다른 역할은 아래 정확 cat 경로를 쓴다.

## expanded_train:1372180
original SHA-256: C9BFD3E421EB1A212EB4F4AD0048ECB8F49ADA2E423C0E6097CDC3B6F6CC8ED5
candidate SHA-256: C9BFD3E421EB1A212EB4F4AD0048ECB8F49ADA2E423C0E6097CDC3B6F6CC8ED5
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 2]
full_diff 프레임 패킷: [3, 3]
중복 후보만 포함해 생략 가능한 패킷: []
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1372180_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1372180_0002.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1372180_0003.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1372950
original SHA-256: 9F8EB51359D924DEFE090232AE75DE8B135AA84945822E93BBF77CF9103FF0CC
candidate SHA-256: 9F8EB51359D924DEFE090232AE75DE8B135AA84945822E93BBF77CF9103FF0CC
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 1]
full_diff 프레임 패킷: [2, 2]
중복 후보만 포함해 생략 가능한 패킷: []
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1372950_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1372950_0002.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1387568
original SHA-256: 1342AC487BEE687534AD3F8CD93DA5C3EFF6D17929428BB4D9CA7395F292E557
candidate SHA-256: 1342AC487BEE687534AD3F8CD93DA5C3EFF6D17929428BB4D9CA7395F292E557
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 4]
full_diff 프레임 패킷: [8, 8]
중복 후보만 포함해 생략 가능한 패킷: [5, 6, 7]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1387568_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1387568_0002.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1387568_0003.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1387568_0004.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1387568_0008.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1381897
original SHA-256: BC2DD715F93147A2D55810E362D3A1FC877F1DABC72E2D773EC978CA8EBA2222
candidate SHA-256: BC2DD715F93147A2D55810E362D3A1FC877F1DABC72E2D773EC978CA8EBA2222
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 3]
full_diff 프레임 패킷: [5, 5]
중복 후보만 포함해 생략 가능한 패킷: [4]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1381897_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1381897_0002.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1381897_0003.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1381897_0005.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1373671
original SHA-256: 3D40EB5D08C26586708448807975B611C7FB9FF500E689CCA7AEB1BD46E89BEC
candidate SHA-256: 3D40EB5D08C26586708448807975B611C7FB9FF500E689CCA7AEB1BD46E89BEC
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 6]
full_diff 프레임 패킷: [12, 12]
중복 후보만 포함해 생략 가능한 패킷: [7, 8, 9, 10, 11]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1373671_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1373671_0002.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1373671_0003.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1373671_0004.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1373671_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1373671_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/reading_packets_v1/expanded_train_1373671_0012.txt
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

