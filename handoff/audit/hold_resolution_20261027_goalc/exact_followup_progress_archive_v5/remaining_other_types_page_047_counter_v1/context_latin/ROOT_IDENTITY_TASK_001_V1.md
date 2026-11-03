# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:593331
original SHA-256: ACC8B0B6ED4D7B7727672DDAA6F28AE3F90AE57686107C9FC138259AA8D607C7
candidate SHA-256: ACC8B0B6ED4D7B7727672DDAA6F28AE3F90AE57686107C9FC138259AA8D607C7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593331_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:593395
original SHA-256: 96F4DAC2A5F4C0C186BD54BB1CE28ABDB7D863CA9038D6403CFDF59FEFA77004
candidate SHA-256: 613F6C9DF6A28ADE7B80CF6B20709034A3FDFE46199D0435CCD061017B905C8F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:593579
original SHA-256: 0DE6AA149A7E24849D527FE38D454D8B0E6CDE91A41CB61157DDFDE8E7A7DEC0
candidate SHA-256: 0DE6AA149A7E24849D527FE38D454D8B0E6CDE91A41CB61157DDFDE8E7A7DEC0
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593579_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:593834
original SHA-256: 41597A6328D354127B8E39461E1F2B9275A3A03D2E9CB1C4D2147DE018471738
candidate SHA-256: 41597A6328D354127B8E39461E1F2B9275A3A03D2E9CB1C4D2147DE018471738
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [18, 18]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 18]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16, 17]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593834_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593834_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593834_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593834_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593834_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593834_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593834_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593834_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593834_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593834_0018.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:594166
original SHA-256: F7798FA78E3D30136513F58FC07F160DB21236874D259C8295C735256E393D05
candidate SHA-256: F7798FA78E3D30136513F58FC07F160DB21236874D259C8295C735256E393D05
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_594166_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

