# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:271327
original SHA-256: D2956B3FF71D0C6295D87881B3AFB38285AE5CFD1E0299F33AE8C77820E7ED6B
candidate SHA-256: D2956B3FF71D0C6295D87881B3AFB38285AE5CFD1E0299F33AE8C77820E7ED6B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_013_counter_v1/reading_packets_v1/expanded_train_271327_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_013_counter_v1/reading_packets_v1/expanded_train_271327_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:271520
original SHA-256: 43C277F8301B0152BA9524FE5BE8CAE5DB338235C071CD62F9FD70923C75A008
candidate SHA-256: 43C277F8301B0152BA9524FE5BE8CAE5DB338235C071CD62F9FD70923C75A008
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_013_counter_v1/reading_packets_v1/expanded_train_271520_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:271634
original SHA-256: F21950D1ACC9103B8A8548EDC705500E89AD6E597AF1030F4D752BF8942E1313
candidate SHA-256: 12894A19F793C1E5C37E2BE57C42480EEA24B0F3821BDE0569AD538EB09C96F0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:271778
original SHA-256: C69B26DAA8954FFCBBA94F214789142C84BE2F11FC610330AACDA24839B18918
candidate SHA-256: C69B26DAA8954FFCBBA94F214789142C84BE2F11FC610330AACDA24839B18918
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_013_counter_v1/reading_packets_v1/expanded_train_271778_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_013_counter_v1/reading_packets_v1/expanded_train_271778_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_013_counter_v1/reading_packets_v1/expanded_train_271778_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:272023
original SHA-256: F859EDA89677C51F74789F811CF7C5B048C1257EC4EC814E8588E5BE6D3A84DC
candidate SHA-256: F859EDA89677C51F74789F811CF7C5B048C1257EC4EC814E8588E5BE6D3A84DC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_013_counter_v1/reading_packets_v1/expanded_train_272023_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_013_counter_v1/reading_packets_v1/expanded_train_272023_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

