# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:174868
original SHA-256: E9DD71A59C4EAA338529C674B47FCA27951575D54DD693685D9CB678ECE908FD
candidate SHA-256: E9DD71A59C4EAA338529C674B47FCA27951575D54DD693685D9CB678ECE908FD
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_174868_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_174868_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_174868_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_174868_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:175316
original SHA-256: 05782DCA7CBA090C7B3A451C5CC36BE7A7762855B619A5BDB42588664C83AF3D
candidate SHA-256: 05782DCA7CBA090C7B3A451C5CC36BE7A7762855B619A5BDB42588664C83AF3D
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_175316_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_175316_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_175316_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:175443
original SHA-256: AA83B1D1D44170633F949F7135E9B3A7B6BDC99CDDC4B375B4E1106C15B3E2F9
candidate SHA-256: E64363EA4E85E39EBF5928786F952CE5223CF11D4E0DDD6131CF5D0DBA5A14BB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:175616
original SHA-256: 339BA84A6D0D49DE9E6C8C9F7CCE52DA0EA70E13AE41B6EABF39AAA10EC08D8E
candidate SHA-256: 339BA84A6D0D49DE9E6C8C9F7CCE52DA0EA70E13AE41B6EABF39AAA10EC08D8E
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_175616_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_175616_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_175616_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_175616_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_175616_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:176357
original SHA-256: F2654E67C2C8F3043EBBD72DC0D099984C5B40A50D380C4EA65897770C30A98D
candidate SHA-256: D4C54FE0970DCFE024F1B8A2385DAA6C7C318F357115169277E71B6A12EB9369
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

