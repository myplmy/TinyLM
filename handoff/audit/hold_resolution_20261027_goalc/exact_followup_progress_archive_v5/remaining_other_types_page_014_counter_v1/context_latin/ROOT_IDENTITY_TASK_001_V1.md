# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:136310
original SHA-256: 17ACD00E6270F25AC26631C0E5E0B4DEDAEC37869328D8DC2BBA933337E350B1
candidate SHA-256: B2E369CB82640D6EAA4855C6EC834D861A7607857472765D67CF4AABC2109172
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:136349
original SHA-256: A3D4702252EB674E2DE94273F06E8B791FBAC8AA3B84CF3F860A3651A0629707
candidate SHA-256: A3D4702252EB674E2DE94273F06E8B791FBAC8AA3B84CF3F860A3651A0629707
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136349_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136349_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:136644
original SHA-256: DF42B0B5A9E16E927A6461545D797AB379DB8F5EE8AE94695EBD928012C6A834
candidate SHA-256: DF42B0B5A9E16E927A6461545D797AB379DB8F5EE8AE94695EBD928012C6A834
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136644_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136644_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136644_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:136665
original SHA-256: B16480A780F9EA5D24C7B173C8CE23C9ECD6485F00546311BF886CFFC15A50AE
candidate SHA-256: 0A007B37811EE4A2C1BD11D31249671F6D58FD7E7D9ACE4A00A5CBAD70665891
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:136689
original SHA-256: A1C373CE0974AC355499418065E0B1BF95E912A0274F7962AAE01852A8314882
candidate SHA-256: A1C373CE0974AC355499418065E0B1BF95E912A0274F7962AAE01852A8314882
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [20, 20]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18, 19]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136689_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136689_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136689_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136689_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136689_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136689_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136689_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136689_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136689_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136689_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136689_0020.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

