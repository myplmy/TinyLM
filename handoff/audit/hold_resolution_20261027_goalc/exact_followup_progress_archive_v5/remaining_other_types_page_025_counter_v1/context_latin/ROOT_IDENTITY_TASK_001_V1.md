# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:282456
original SHA-256: DBBF51332DB989D92C69DE623B5032DF7C3BB371791954FD798294F7B93F4167
candidate SHA-256: 810682AD94DE574C82C38B84D35E8997A1C135AE73D0D0EE6E61F8D7B20C5C55
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:282470
original SHA-256: F2357F2508EDA1795CDEEB0D6FAF5BB9112A0F86E831FAE789DF972D12CE1600
candidate SHA-256: F2357F2508EDA1795CDEEB0D6FAF5BB9112A0F86E831FAE789DF972D12CE1600
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282470_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282470_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282470_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:282486
original SHA-256: AD65FF637740DBABC7455ECEB4D4838E369CFF8A8158AFD0607A628EE2C46899
candidate SHA-256: AD65FF637740DBABC7455ECEB4D4838E369CFF8A8158AFD0607A628EE2C46899
원문 frame 패킷: [1, 29]
최종 full_diff 패킷: [57, 57]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 57]
후보 중복만 있는 생략 가능 패킷: [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282486_0057.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:282783
original SHA-256: 9159729485919813D468A0DFB94533D87B6D3D3E18B776D13BDA578AC0E4AD4F
candidate SHA-256: C303F62260503D658D31D986435529C760A6586BF1BE5BDF46763E7AA7338AC6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:283019
original SHA-256: 59921DBD2D500623EFB41F38B12102D44C5875B4F3419BEBC12747DF33C3A610
candidate SHA-256: CCCE1E6CCD3EDC8D8E4A6BBAD344962BEE6CB886765A83C4A63017A14AE6696A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

