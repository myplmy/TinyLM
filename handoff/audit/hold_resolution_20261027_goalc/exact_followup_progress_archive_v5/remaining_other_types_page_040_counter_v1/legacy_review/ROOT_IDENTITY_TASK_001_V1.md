# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:487298
original SHA-256: 4F4045982E5D299A699FE860865B4E98A3DCDFF6F3F797EEBC158EA75C90606A
candidate SHA-256: 4F4045982E5D299A699FE860865B4E98A3DCDFF6F3F797EEBC158EA75C90606A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487298_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:487299
original SHA-256: 8175C5B6E785FD5F5260B4F79DFC5469977209EF76EB674D37600019F94E5B5E
candidate SHA-256: 8175C5B6E785FD5F5260B4F79DFC5469977209EF76EB674D37600019F94E5B5E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487299_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:487484
original SHA-256: 2A44A72A8126254593E5C4978A6B34DC2F6B8F2710D1C7DFD68556C862C02221
candidate SHA-256: 2A44A72A8126254593E5C4978A6B34DC2F6B8F2710D1C7DFD68556C862C02221
원문 frame 패킷: [1, 11]
최종 full_diff 패킷: [22, 22]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 22]
후보 중복만 있는 생략 가능 패킷: [12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487484_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487484_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487484_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487484_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487484_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487484_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487484_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487484_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487484_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487484_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487484_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487484_0022.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:487500
original SHA-256: C52E73C521FD9636BF2DAEE5951D7C4D68B916B484546F43D73320EF8DD35391
candidate SHA-256: C52E73C521FD9636BF2DAEE5951D7C4D68B916B484546F43D73320EF8DD35391
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487500_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:487537
original SHA-256: 639D710374C7F568FE3EA2152CBE7CF9D758739FFF6D90D2F51A9D356D822721
candidate SHA-256: F492CA80C95BC25BE67DFC6515141CD544F9E247EAB4E549F24DF61FFF2E2CD6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

