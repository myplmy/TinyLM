# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:461126
original SHA-256: 465676E18B3973646C02E4EBE1DBAC6A70EA91E8B84CF3AD56077255B8909938
candidate SHA-256: 6BC005118B8DDEB76B05B79284EDE6366C1E5D0BC13601A9569C1EDD2E899724
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:461230
original SHA-256: D3482724735C92DB676E146AFF830C36031C460475A5777466F4B02EF16A6B25
candidate SHA-256: D3482724735C92DB676E146AFF830C36031C460475A5777466F4B02EF16A6B25
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461230_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461230_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461230_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461230_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461230_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461230_0010.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:461503
original SHA-256: E8727F878887C5947222EDA0348BD84DCF8866E18350DB09F601260A81CF0C1A
candidate SHA-256: 39C0FB0FFEEC1944A17336F553533B906F1E618BD2105031458A565FAEF0EAC6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:461515
original SHA-256: A6D287524F6BF0BEBAB034C0C2F8418252CD1E71A937F8DC9554F2925CFE0BD1
candidate SHA-256: A6D287524F6BF0BEBAB034C0C2F8418252CD1E71A937F8DC9554F2925CFE0BD1
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461515_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461515_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461515_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461515_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461515_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461515_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461515_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461515_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:461659
original SHA-256: 2E216028D44C8F19696E6E2B6D54F4C95A651158CBF5BC655C1438453DD6139F
candidate SHA-256: 349A26D61396CF464F3D865382BACF2EA526C18F2DFFA25AB9B0EE9B79A7D34A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

