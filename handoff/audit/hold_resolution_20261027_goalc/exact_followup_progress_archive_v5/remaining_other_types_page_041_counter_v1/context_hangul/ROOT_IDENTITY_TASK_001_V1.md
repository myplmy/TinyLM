# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:501687
original SHA-256: DACC1FAB79D63815B61319D3E79677DEE60EAD073DF9F26BF3B886BE16B5AD55
candidate SHA-256: 85F41AC19A650112E511D1159629E207C29B6BA8D14FCFB810870F5826071499
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:501936
original SHA-256: 1CEF3A6233AA2BC6F7633697AFB3392EB36666EE539AF66879657259922C6F91
candidate SHA-256: D6DD661A75645970330D507CB2A65FC034620A8C4342BDC934C54EB1A029060E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:502069
original SHA-256: F21172258425DF2F20840C1042455A114B9C1B4D196C2B061A82C768D03F92D6
candidate SHA-256: F21172258425DF2F20840C1042455A114B9C1B4D196C2B061A82C768D03F92D6
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_502069_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_502069_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:502079
original SHA-256: 1C76D40C052FF70E94D7462D31F7C99EC1775BDAAD5A44A4B2BD18F34ABCE144
candidate SHA-256: 1C76D40C052FF70E94D7462D31F7C99EC1775BDAAD5A44A4B2BD18F34ABCE144
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_502079_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_502079_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_502079_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:502089
original SHA-256: FE56773622E342F75B28BA4384514E580196BD20368ACB9E373A391BD875315B
candidate SHA-256: 2B618141440D9D8AC07F880CD18F9E0F92471FEE7E4DF3644685476369041D39
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

