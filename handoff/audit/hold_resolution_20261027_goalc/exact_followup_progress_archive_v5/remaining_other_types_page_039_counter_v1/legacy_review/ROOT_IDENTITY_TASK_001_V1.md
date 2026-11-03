# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:474560
original SHA-256: 77DD215235F0126538F18012A8E408A7D5195B503C37CEF405295FF4A1939A0F
candidate SHA-256: 77DD215235F0126538F18012A8E408A7D5195B503C37CEF405295FF4A1939A0F
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474560_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474560_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474560_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:474585
original SHA-256: BEAF8FE7C81830698BBB64F8B8EBE19751EB00A883CCC666C97DDE1DD2005FCC
candidate SHA-256: BEAF8FE7C81830698BBB64F8B8EBE19751EB00A883CCC666C97DDE1DD2005FCC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474585_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474585_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:474591
original SHA-256: 947E4D4B67F3D93358442AB879172B069247A6D7DB04D4D56E71042D73D477E5
candidate SHA-256: B2BD0B743B38039E97902C130231C5AC35A5D3B81B617266AA523F779ED351A3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:474961
original SHA-256: 1130380FA1501A7C59508BDD5E6149709C06FEAD50ACDCFA82697318DE201B3B
candidate SHA-256: 1130380FA1501A7C59508BDD5E6149709C06FEAD50ACDCFA82697318DE201B3B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474961_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:475158
original SHA-256: B988649BA43FABEDC96302BE211FF1B7D7B50B328217F75C446F24B504A1F20A
candidate SHA-256: 9014B259F27C905556ADAF19CB568C666C8D9927410F536AF297B433E01223C8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

