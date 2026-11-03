# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1264595
original SHA-256: 1A2297EDABBA5C9F4AA6F30921A1AFF5D402EB1BA8707EDA83C128FDB4590FAF
candidate SHA-256: 1A2297EDABBA5C9F4AA6F30921A1AFF5D402EB1BA8707EDA83C128FDB4590FAF
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264595_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1264624
original SHA-256: C166B90DC4E89B2ED2B5C9661F39245E44E54D44816420954780A062892CD3D4
candidate SHA-256: 49659A90180D61251DA10A93AFF5C92C3EAA314EDBB32A340ED571B850646B45
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1264650
original SHA-256: 72A1EE1EBF2A2E58F994A94E1922311635E9074ECD81B59F8299EEDB51833C7A
candidate SHA-256: 4178D17A86F3CA5DE734642B0B26436A1BDC6E58B3F0F6EFA8E73DFA0D7ED664
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1264689
original SHA-256: D3FCAF9D03B6DBE3264F1868E35D58E1ADA490BCEE212FDF102C76AB145D5E19
candidate SHA-256: D3FCAF9D03B6DBE3264F1868E35D58E1ADA490BCEE212FDF102C76AB145D5E19
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264689_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1265025
original SHA-256: E5F675C7BB69345829B4D4AFD42B84BB86EB401410E83DB309AB39648A671F77
candidate SHA-256: E5F675C7BB69345829B4D4AFD42B84BB86EB401410E83DB309AB39648A671F77
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1265025_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1265025_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1265025_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

