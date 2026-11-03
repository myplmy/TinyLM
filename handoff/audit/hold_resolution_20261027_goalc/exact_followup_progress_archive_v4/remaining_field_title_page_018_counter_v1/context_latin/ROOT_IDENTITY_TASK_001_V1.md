# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:485162
original SHA-256: 8B3E70E1FFB3341DD736F3D3B187C6FA1CA34AB2B9D23A9169E8449F78B20423
candidate SHA-256: 6034F69C430FDD50FA1795AF05F3EAF5EDB97BA69A386C499A543B9E685D45AE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:485934
original SHA-256: F2B1DF14BB838238EA040AE7A8F72A87DD25E9F050511A49761847B0075A7DF8
candidate SHA-256: F2B1DF14BB838238EA040AE7A8F72A87DD25E9F050511A49761847B0075A7DF8
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_018_counter_v1/reading_packets_v1/expanded_train_485934_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:486923
original SHA-256: 0DA5BB93D4767F9BA14B73D03545D7A55FD8D6509435F0FB3200B82236558463
candidate SHA-256: 42F742679298907E385C5A44E936873D7BE344E50617C68E323548394D12F49E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:487384
original SHA-256: BAAA441518B3FA8861EADCAF52D8599F2B16028ED17458257DB3261894A57E70
candidate SHA-256: BAAA441518B3FA8861EADCAF52D8599F2B16028ED17458257DB3261894A57E70
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_018_counter_v1/reading_packets_v1/expanded_train_487384_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_018_counter_v1/reading_packets_v1/expanded_train_487384_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_018_counter_v1/reading_packets_v1/expanded_train_487384_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_018_counter_v1/reading_packets_v1/expanded_train_487384_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_018_counter_v1/reading_packets_v1/expanded_train_487384_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_018_counter_v1/reading_packets_v1/expanded_train_487384_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:487961
original SHA-256: 1D797B1B25B14A11D0BDC86891CF90E70406DEABBC4D614CD8B7E72EC3282C06
candidate SHA-256: 1D797B1B25B14A11D0BDC86891CF90E70406DEABBC4D614CD8B7E72EC3282C06
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_018_counter_v1/reading_packets_v1/expanded_train_487961_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

