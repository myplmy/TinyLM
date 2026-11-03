# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:678571
original SHA-256: 0B1E56E6DD9135AB512D5CA5B80D428EFD3532E56AB9372DDE9251DEF39B217A
candidate SHA-256: 0B1E56E6DD9135AB512D5CA5B80D428EFD3532E56AB9372DDE9251DEF39B217A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678571_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:678578
original SHA-256: F4E61793773AA1AC7BA36C73F168D0D5E980B097D3EFF9F2DC733D0499007785
candidate SHA-256: F4E61793773AA1AC7BA36C73F168D0D5E980B097D3EFF9F2DC733D0499007785
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678578_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678578_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678578_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678578_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:678670
original SHA-256: 59F410FE1440F523B46BA79A9A870922759F753E9844923C9EA522FB8F9B2A01
candidate SHA-256: 59F410FE1440F523B46BA79A9A870922759F753E9844923C9EA522FB8F9B2A01
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678670_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678670_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678670_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678670_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678670_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678670_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678670_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:678733
original SHA-256: A3116D45AC124A6722C76848AA64BEE1A7E44DFD9491390237E27987E33D54EC
candidate SHA-256: A3116D45AC124A6722C76848AA64BEE1A7E44DFD9491390237E27987E33D54EC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678733_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678733_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:678774
original SHA-256: 5E75AC68A386268ECC8E566EB25937C40A9206BADA7523CC4A2B4CB0CFAD8131
candidate SHA-256: 5E75AC68A386268ECC8E566EB25937C40A9206BADA7523CC4A2B4CB0CFAD8131
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [15, 15]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 15]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678774_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678774_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678774_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678774_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678774_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678774_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678774_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678774_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678774_0015.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

