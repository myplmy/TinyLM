# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:136300
original SHA-256: FDCF239B8B0164518EE3CD161BDEB1575F512135D81CEF3BF9F7DD248F97F438
candidate SHA-256: 5D649F54238778B504705F6C8BAFFA468C02EE4219C66853DD76F29B261B39B4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:136366
original SHA-256: 3E53A1D13FD692E71A8245F0A0B2E7E27A353701DE3C8CAB0C8F62A6606E21A8
candidate SHA-256: 3E53A1D13FD692E71A8245F0A0B2E7E27A353701DE3C8CAB0C8F62A6606E21A8
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [15, 15]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 15]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136366_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136366_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136366_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136366_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136366_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136366_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136366_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136366_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136366_0015.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:136429
original SHA-256: 900BCFA34D46B15D941D64411B35B3228DD84E1E812EDA8403045B40136DA839
candidate SHA-256: 900BCFA34D46B15D941D64411B35B3228DD84E1E812EDA8403045B40136DA839
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136429_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136429_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:136448
original SHA-256: 11EF12948FA37C37133D767323DFC049F88A59C0D51C3E31B1644A89A8758383
candidate SHA-256: 11EF12948FA37C37133D767323DFC049F88A59C0D51C3E31B1644A89A8758383
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136448_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136448_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136448_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:136498
original SHA-256: BBC544555F2449DB71A2F296ED47E34FE4CF5F9F917FC4C413446478B0866F1D
candidate SHA-256: E6ADFB261BC4242A196D0B85335DCF0A67FE445FDD9F131D1F111AF9D19075E7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

