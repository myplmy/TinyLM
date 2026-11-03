# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:255872
original SHA-256: 6D41932D14117BD704D3A8474FCB412BC157A07CF3986DAB95FEA29CB9C62D3F
candidate SHA-256: 6D41932D14117BD704D3A8474FCB412BC157A07CF3986DAB95FEA29CB9C62D3F
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_023_counter_v1/reading_packets_v1/expanded_train_255872_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_023_counter_v1/reading_packets_v1/expanded_train_255872_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_023_counter_v1/reading_packets_v1/expanded_train_255872_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_023_counter_v1/reading_packets_v1/expanded_train_255872_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:255907
original SHA-256: 4AC5C426FAF1575F3AA62ECF3D754237D1F5B4CE1D72C1D0C425D465358692FD
candidate SHA-256: 4AC5C426FAF1575F3AA62ECF3D754237D1F5B4CE1D72C1D0C425D465358692FD
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_023_counter_v1/reading_packets_v1/expanded_train_255907_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_023_counter_v1/reading_packets_v1/expanded_train_255907_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_023_counter_v1/reading_packets_v1/expanded_train_255907_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:255999
original SHA-256: 9EE9851A305D466E0A609246980734D9C5837B6458DB9E96F7948CC624C39BB2
candidate SHA-256: 31E0FA0F28857B6591213E9C73046ECCB5021E39C5A67D0BC98A6A06919882F3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:256110
original SHA-256: 35A9E534DE6D5C079ED02481603B47D0B96E8929568FFA0E4747776FF7CEE995
candidate SHA-256: FF8F48E8723CF1D024C44A1401745A7F79499EA2DDEA14F54441D05534D61FE9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:256123
original SHA-256: EDD3D8B968B888130EE662CD0C878CFF8C20E9B4C2EC38C080DFD8C94A478C78
candidate SHA-256: EDD3D8B968B888130EE662CD0C878CFF8C20E9B4C2EC38C080DFD8C94A478C78
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_023_counter_v1/reading_packets_v1/expanded_train_256123_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

