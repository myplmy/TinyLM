# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:359290
original SHA-256: 3B5862BAC0ADB420DF7564EF89E3A39354E301737A668096FD8A5535450D721D
candidate SHA-256: 3B5862BAC0ADB420DF7564EF89E3A39354E301737A668096FD8A5535450D721D
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_031_counter_v1/reading_packets_v1/expanded_train_359290_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_031_counter_v1/reading_packets_v1/expanded_train_359290_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:359302
original SHA-256: 3E667B0F708552967917AA2D9A1EA49F00C280A3FD5E1B0CD6525FB2601ABC1F
candidate SHA-256: BB36F7614ECC85B51A0C9021F2C705CEC5390C173F1DFFCF20739728C1833B30
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:359335
original SHA-256: C587B5D56B05E0570BDCBD690B89DEC49B76D860365C10BCC3190BC3CD90577C
candidate SHA-256: 3F24091327671D6E02200E9C6F1C9A34B33F8E08DF2FACD593D9272D1599AFF3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:359382
original SHA-256: 2B9BE1A72E762E47D2012D2EF018947BB7B077558E8A39D3A8E93F5FBE7B9F1C
candidate SHA-256: 2B9BE1A72E762E47D2012D2EF018947BB7B077558E8A39D3A8E93F5FBE7B9F1C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_031_counter_v1/reading_packets_v1/expanded_train_359382_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:359490
original SHA-256: 74F6D3F0CEE4747E49D1CEBEC18B7C02D9C44B8545C27511C568BF093E903A26
candidate SHA-256: 74F6D3F0CEE4747E49D1CEBEC18B7C02D9C44B8545C27511C568BF093E903A26
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_031_counter_v1/reading_packets_v1/expanded_train_359490_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_031_counter_v1/reading_packets_v1/expanded_train_359490_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_031_counter_v1/reading_packets_v1/expanded_train_359490_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_031_counter_v1/reading_packets_v1/expanded_train_359490_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_031_counter_v1/reading_packets_v1/expanded_train_359490_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_031_counter_v1/reading_packets_v1/expanded_train_359490_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_031_counter_v1/reading_packets_v1/expanded_train_359490_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

