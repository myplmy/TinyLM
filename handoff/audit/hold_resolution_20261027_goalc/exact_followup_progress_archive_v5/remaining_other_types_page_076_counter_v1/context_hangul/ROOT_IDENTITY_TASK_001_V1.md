# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1045828
original SHA-256: FEE2B204AAA0AE1C9395161789F62A5DCB7052CEB0A2FC6D9A4D789324E68AF5
candidate SHA-256: FEE2B204AAA0AE1C9395161789F62A5DCB7052CEB0A2FC6D9A4D789324E68AF5
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1045828_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1045828_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1045828_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1045828_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1046038
original SHA-256: 497C221B9CC86ADFB33C451333E6FC9056F999A54CCF5667AE2E589BD04D4689
candidate SHA-256: 497C221B9CC86ADFB33C451333E6FC9056F999A54CCF5667AE2E589BD04D4689
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1046038_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1046038_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1046130
original SHA-256: 5B7EC15B962AB97DA3DCAC8037120CFE7073FEAF87C70AAFA840D71890F05F0F
candidate SHA-256: 5B7EC15B962AB97DA3DCAC8037120CFE7073FEAF87C70AAFA840D71890F05F0F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1046130_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1046165
original SHA-256: D492EE18AD217B04A7FF7221F50D0EE83BA0383ECF6930D068BB3313ED6BDA26
candidate SHA-256: D492EE18AD217B04A7FF7221F50D0EE83BA0383ECF6930D068BB3313ED6BDA26
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_076_counter_v1/reading_packets_v1/expanded_train_1046165_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1046210
original SHA-256: 29D68843E8D488B999FDEEB8BD367CF62EC00A444413FD7A4C2BC5C5699B29BF
candidate SHA-256: 21981AA5738072FC212F83EDF9E07893684B3B2AB7FAB1223B1724F39D5C4692
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

