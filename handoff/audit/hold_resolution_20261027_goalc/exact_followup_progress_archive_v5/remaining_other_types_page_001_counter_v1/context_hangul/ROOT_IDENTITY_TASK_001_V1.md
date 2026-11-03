# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1091
original SHA-256: 6F581AB76B57F9A12140E4FD6589EC3733A86FB763D49A583ACE9F424E45F6C4
candidate SHA-256: 6F581AB76B57F9A12140E4FD6589EC3733A86FB763D49A583ACE9F424E45F6C4
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1091_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1091_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1091_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1091_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1091_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1091_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1091_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:120
original SHA-256: 494BC67E3064C9DC35F405E1655736E9D97E1E7284D66E2405DB11B42B0A0A33
candidate SHA-256: 17CBEDE643958999B854FC175C71AC414D85EC2D2DFAE5B7CC44A93EF3950564
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:160
original SHA-256: F12F493F34D4F01816AFD473CB5A541582A7519428B28272B75EF10CA3DC47EE
candidate SHA-256: 84AF6F6377827A2A0330556083896A75E82EE67A8F62BB06F792693B45FD9088
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1768
original SHA-256: 1EE587CE0AF30FAAAA05CA387A86B408BEED266537D70738CB9FFE9F5329E5E1
candidate SHA-256: FE2FB674F87DAFA0533103E9917D67F1E9A967E4536B48C83DD37FE080E49D9D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1844
original SHA-256: 464523E2992D95AD9423F29C48DAE38306E5FA533975B3F67D2F1D1AE658D6AA
candidate SHA-256: ECDF837F9A77588261DDEF3D44E1095CA78B2542E57808D9E080EF061DB62CA4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

