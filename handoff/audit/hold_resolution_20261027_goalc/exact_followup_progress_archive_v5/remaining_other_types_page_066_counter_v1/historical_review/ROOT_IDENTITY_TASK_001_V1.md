# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:862560
original SHA-256: AB1849A54989826F3841ACA101E41A8D03169C51EC3D3397A27CDE4034B943BE
candidate SHA-256: AB1849A54989826F3841ACA101E41A8D03169C51EC3D3397A27CDE4034B943BE
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_066_counter_v1/reading_packets_v1/expanded_train_862560_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_066_counter_v1/reading_packets_v1/expanded_train_862560_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_066_counter_v1/reading_packets_v1/expanded_train_862560_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:862587
original SHA-256: 6FD30E03613363235D21A190ADFDF00DC78A077869F84261890CE788A2E06436
candidate SHA-256: 6FD30E03613363235D21A190ADFDF00DC78A077869F84261890CE788A2E06436
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_066_counter_v1/reading_packets_v1/expanded_train_862587_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_066_counter_v1/reading_packets_v1/expanded_train_862587_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_066_counter_v1/reading_packets_v1/expanded_train_862587_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_066_counter_v1/reading_packets_v1/expanded_train_862587_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:862762
original SHA-256: 668984FF2539A8B225EF4ADBD80893CE8117D3F0CF272F7A45E18583F282E3A8
candidate SHA-256: 9810E5CDA0B2A976A10D5CD5618081B3B387703EEB8E6A4E0F7AC659FF83CB73
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:863296
original SHA-256: 79269FB56AF822FC4588760C79707B28F1865E37A17CBA14E67A21626DE24281
candidate SHA-256: 79269FB56AF822FC4588760C79707B28F1865E37A17CBA14E67A21626DE24281
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_066_counter_v1/reading_packets_v1/expanded_train_863296_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_066_counter_v1/reading_packets_v1/expanded_train_863296_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_066_counter_v1/reading_packets_v1/expanded_train_863296_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_066_counter_v1/reading_packets_v1/expanded_train_863296_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_066_counter_v1/reading_packets_v1/expanded_train_863296_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_066_counter_v1/reading_packets_v1/expanded_train_863296_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_066_counter_v1/reading_packets_v1/expanded_train_863296_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:863467
original SHA-256: 8E800F2A965023D41810F0C9B6040E6199356490CF8806DB91179318EA8C3E72
candidate SHA-256: B7B20D04AC01EACDB02761CDF713C5F255E9B67574ED974CAE330A75C170AEAF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

