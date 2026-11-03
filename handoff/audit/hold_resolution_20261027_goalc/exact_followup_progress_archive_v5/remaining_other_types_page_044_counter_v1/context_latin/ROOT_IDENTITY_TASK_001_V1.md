# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:546879
original SHA-256: EB439BE3EEBD1A5DF874FC3DA276ACC74B81597A95A748BDE54CF0A063B045FA
candidate SHA-256: 280D63E12BD8D83B983F2E24F9DA8B21AEED894516321B1ABD0AAC41372FD494
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:547190
original SHA-256: C68519B1EE2F0C32D24087F8E5F67B2CC0E4BBB864A3523FC5BC5A98D43450ED
candidate SHA-256: 6116F13A25A48D4CA91CA9D964D6C01113090CE82FE309704018E6D5839E86C7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:547356
original SHA-256: AF84202C6883F1B672D66F3F5E9D0FBFE053ECD3B9EB1C6A3450078524CC3F0C
candidate SHA-256: AF84202C6883F1B672D66F3F5E9D0FBFE053ECD3B9EB1C6A3450078524CC3F0C
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_547356_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_547356_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_547356_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_547356_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_547356_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_547356_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_547356_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_547356_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:547429
original SHA-256: 22E5C5348D83D738A75175882F41313D3E6D4EECCC37A6E6297A7968582722FB
candidate SHA-256: 22E5C5348D83D738A75175882F41313D3E6D4EECCC37A6E6297A7968582722FB
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_547429_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_547429_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_547429_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:547600
original SHA-256: EC542405890E1DD04B5B006EB99BCC874C635E39B46620902EA7196ED2F945CB
candidate SHA-256: EC542405890E1DD04B5B006EB99BCC874C635E39B46620902EA7196ED2F945CB
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_547600_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

