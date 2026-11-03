# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:270246
original SHA-256: 5FD05C391CEB863C8406E91BE7177B802D7400289D618ADA148A71214489BF4C
candidate SHA-256: 5FD05C391CEB863C8406E91BE7177B802D7400289D618ADA148A71214489BF4C
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270246_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270246_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270246_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270246_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:270766
original SHA-256: 39F5474ACDD5EA0EB1EC76344296D02E5C40035886A1C20A0E6BF2A300A6DFAB
candidate SHA-256: 39F5474ACDD5EA0EB1EC76344296D02E5C40035886A1C20A0E6BF2A300A6DFAB
원문 frame 패킷: [1, 15]
최종 full_diff 패킷: [30, 30]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 30]
후보 중복만 있는 생략 가능 패킷: [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270766_0030.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:270790
original SHA-256: 9A3CDC2890F87C953FB812858AD5324AEF50A39D3D42F6E7327B3342085F7639
candidate SHA-256: CEC8DDE944989F13766D822EA0FE28AD445DFEB89AD66BAB6BACA2038ED6C1F3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:270800
original SHA-256: C2F11FC6710A8CF2BABA154003F9C228F96E8845F8B82FF0DEEBCB399E075E00
candidate SHA-256: C2F11FC6710A8CF2BABA154003F9C228F96E8845F8B82FF0DEEBCB399E075E00
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270800_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270800_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:270826
original SHA-256: 6B3F14560AA92AB8B81C73C8FBF51FDD92E841A2E5522853622822B7A25358A9
candidate SHA-256: 6B3F14560AA92AB8B81C73C8FBF51FDD92E841A2E5522853622822B7A25358A9
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270826_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270826_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270826_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

