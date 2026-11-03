# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1197222
original SHA-256: 8C1FA50410FA0C254D19FB3AF35946D86FD78E13560E5289A46BF33EF550DE9A
candidate SHA-256: 2C7E4CD3F72EE3C1F03791DFB34B7F7B0557A5CECC17869B1EAA8FB31B3CA902
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1197356
original SHA-256: C5BAEF6DFD890B91CF5B20FB87800FA3D29A1F6BD495D2B131A11066623F0CCE
candidate SHA-256: C5BAEF6DFD890B91CF5B20FB87800FA3D29A1F6BD495D2B131A11066623F0CCE
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1197356_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1197356_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1197356_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1198361
original SHA-256: 81E0F68DAD1E90931E937D84D384930E3853824A926F029C5CE3ED2024F94AA9
candidate SHA-256: DEF69F5CF0CD1D3C8AEEF55269CEE65F5B287CDC31EFD2FF5B60868EBEDC8412
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1199140
original SHA-256: DCFE14FB07D7382B99164D5FF26DC51E66AE155E57865C6F91221664CDF3C981
candidate SHA-256: 05DE764D9BD3BFEB0C0E62B7ADAC5CDE912E5A35FF6C47E22E2B1D84507BB313
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1199485
original SHA-256: E96334E16BB085FF966356C65900873B474FFB382DCD3F914FF0AD70CFED71B3
candidate SHA-256: 1E78815E1AACC40BFE1345C5EF468340595E1606839102C0B616C6B9ED3B2A15
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

