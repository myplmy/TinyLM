# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:716952
original SHA-256: 4AF5022ACEEAF8B283CD4E31E4C671A63ABDABA7480E43013B3C5F96BD9A9B86
candidate SHA-256: 4AF5022ACEEAF8B283CD4E31E4C671A63ABDABA7480E43013B3C5F96BD9A9B86
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_716952_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_716952_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_716952_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:717037
original SHA-256: 2FF0086E786D80A897E2527A4541B6E0F3E8A2037020ADA8E7D257993DD0EFCE
candidate SHA-256: 2FF0086E786D80A897E2527A4541B6E0F3E8A2037020ADA8E7D257993DD0EFCE
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_717037_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_717037_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_717037_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_717037_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:717139
original SHA-256: 72E51EF9EA325883A0E6FCD0B736D3AE4B645AACB05E90761C35A199FB9A9BCB
candidate SHA-256: 55C8EC02EE6F97E1F6038D41E572C4FA59F62222E1B5EB9D7BEA82DE8AA3DE2E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:717277
original SHA-256: D0B67AADAA7823357D7F4E05DD2943B2E48FDD97B24B2368D0CD99D0B171D45A
candidate SHA-256: 42A3B7917383F9FC26CB9D9514A7C749E4F7FCC7B94EADA87853AEEA408E9B48
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:717403
original SHA-256: 59092A1DEE0828049E4D905BA795F731BD425A90C137B0719C69FC57F63852C4
candidate SHA-256: C61A7A48EDDCBF1598A5141B46B2586EFD804B581C3191E910D8AA54DC073A52
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

