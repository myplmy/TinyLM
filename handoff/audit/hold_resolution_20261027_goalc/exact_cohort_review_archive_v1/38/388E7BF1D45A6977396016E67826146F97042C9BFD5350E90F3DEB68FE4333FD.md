# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:112202
original SHA-256: E1D7DE7CE3F602CDC2EF7B1D77EE1C80B3C51F56E7DAD1F4268C597EB2E897D9
candidate SHA-256: DA1CB046B11ACBD0D6B93C37D3A83C47DFAE33E1175D6AB6D2FA4734252E3B11
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:112821
original SHA-256: 9C6E80C278D67F2B3120A853B3CA8CB10E2D8493F42F2A868F8067F01E404325
candidate SHA-256: B60CA8E66A3C6624D6C36E750C23AAA0D96E7A710D198093D60DC9B1C3BB4BF7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:113061
original SHA-256: 414C53FD77AB445161D02AA76FC23210A8C6C6A16E52523A12E0ADA4CD96A167
candidate SHA-256: 414C53FD77AB445161D02AA76FC23210A8C6C6A16E52523A12E0ADA4CD96A167
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_113061_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:113535
original SHA-256: E87E3F5259482D679F7CF7EC066EB84FBFE674741EA436015A8AECFD7B18910C
candidate SHA-256: E87E3F5259482D679F7CF7EC066EB84FBFE674741EA436015A8AECFD7B18910C
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_113535_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_113535_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_113535_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_113535_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:113813
original SHA-256: 07EAE671A2968EE3D8DAFF8CE0455A2E9D845A79C27B1B096FF9EC2E6225683D
candidate SHA-256: 07EAE671A2968EE3D8DAFF8CE0455A2E9D845A79C27B1B096FF9EC2E6225683D
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_113813_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_113813_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

