# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:231644
original SHA-256: AD8BCCB3A9B3A5648776F023CB8227977ED6ADAEC9E40C0B8E05BBC950AD326B
candidate SHA-256: AD8BCCB3A9B3A5648776F023CB8227977ED6ADAEC9E40C0B8E05BBC950AD326B
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231644_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231644_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231644_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231644_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231644_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231644_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231644_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231644_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:231725
original SHA-256: CAE98C0E357A82E055269FC9514CF18744B36D5F13DA1097D90740C268E5881B
candidate SHA-256: CAE98C0E357A82E055269FC9514CF18744B36D5F13DA1097D90740C268E5881B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231725_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231725_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231725_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:231821
original SHA-256: E659E776528217CD6AA89C307C68322E352CA9F2EAC3511FC5543A67B7145E3C
candidate SHA-256: E659E776528217CD6AA89C307C68322E352CA9F2EAC3511FC5543A67B7145E3C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_231821_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:231973
original SHA-256: A6A7585FD794316090B204C8E13A013FC7F1F75F48E17540AA8ECF8BEFCE8B40
candidate SHA-256: A69F13238AA88E6214B2DF8EA19D918A212C27BD5127E92245D5E6C6BB1134A0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:232222
original SHA-256: B090C0A31C3564F90E1F569B819FC056BF954F0C5C81EC010D1CDA6BB08A51F2
candidate SHA-256: B090C0A31C3564F90E1F569B819FC056BF954F0C5C81EC010D1CDA6BB08A51F2
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232222_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232222_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232222_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232222_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

