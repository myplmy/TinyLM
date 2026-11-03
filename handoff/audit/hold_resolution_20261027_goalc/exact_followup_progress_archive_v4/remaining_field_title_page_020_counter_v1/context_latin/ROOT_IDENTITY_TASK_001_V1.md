# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:571374
original SHA-256: 32B46B36FB66151E693408700A459B8D8010747A77B24AF40454C7A0B985E77C
candidate SHA-256: 32B46B36FB66151E693408700A459B8D8010747A77B24AF40454C7A0B985E77C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_020_counter_v1/reading_packets_v1/expanded_train_571374_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_020_counter_v1/reading_packets_v1/expanded_train_571374_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:571601
original SHA-256: 58431704799A3A31D343A6F79C0F44E6D7E607561471916A651CF17234128C47
candidate SHA-256: 58431704799A3A31D343A6F79C0F44E6D7E607561471916A651CF17234128C47
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_020_counter_v1/reading_packets_v1/expanded_train_571601_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_020_counter_v1/reading_packets_v1/expanded_train_571601_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_020_counter_v1/reading_packets_v1/expanded_train_571601_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_020_counter_v1/reading_packets_v1/expanded_train_571601_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:572274
original SHA-256: 3F8ABF51A6A5BD8D57FEA86FB5F1C0868828CE451EDF132EAB36A0B77993B61C
candidate SHA-256: 35DC9CAE0FCD9CEF71E4B84CB82E314C7CFAA3305857E77DCFC42B6167170CD2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:572503
original SHA-256: EF45F9C689CD2387106B7F0B098AEF8942B8926F4673F2CC3416D36F0D50E4EE
candidate SHA-256: EF45F9C689CD2387106B7F0B098AEF8942B8926F4673F2CC3416D36F0D50E4EE
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_020_counter_v1/reading_packets_v1/expanded_train_572503_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_020_counter_v1/reading_packets_v1/expanded_train_572503_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:573801
original SHA-256: AAAA372564262E91FA4A7D204D1693F94A41B72C38BCCA5AD7070F7C30333E0B
candidate SHA-256: F37E33CE8EDE4A1DBFB30EA3B23A516FFEAC67F57F49B09293280029479CCE8E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

