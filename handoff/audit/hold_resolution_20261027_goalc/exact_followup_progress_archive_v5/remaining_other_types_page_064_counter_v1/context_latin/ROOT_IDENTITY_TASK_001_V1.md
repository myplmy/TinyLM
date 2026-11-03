# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:828809
original SHA-256: 3081787853424DAA575A5A6B1CB67E35791A5C5CA733526051AD7EDB4278694E
candidate SHA-256: 6DBE4DA0BDD0A4467AEF06B0C7577FC4947A19ECCF2E3FA6859AD161B6EE9ADF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:828813
original SHA-256: 6837819832F2C01A301CFE1D65AFCF8A1BEC98F0038000C1EBB1EFE7B4ACF480
candidate SHA-256: 5291C9BA96E29E8A8C8148C08680E5571CADDCBEAD1076C864C3DEF82BED62B0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:828871
original SHA-256: B75077E89687DD94794BEF86E2942ABE562DD8C21AD62FCA780F3E81302BB881
candidate SHA-256: F917FAF406853F01347BF5B1DF94D3AE4C249697BFF008A6DD6AAD9D1591E392
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:829027
original SHA-256: C784B44DA878FF3FAD727709AA49B7E2D98C986CACE2A4B1388A16168EF325A0
candidate SHA-256: C784B44DA878FF3FAD727709AA49B7E2D98C986CACE2A4B1388A16168EF325A0
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_829027_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_829027_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_829027_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:829624
original SHA-256: 68662A820F27E4F766734841FA27F183168D0FC3C049ECD924D240ADDD3DF17E
candidate SHA-256: 68662A820F27E4F766734841FA27F183168D0FC3C049ECD924D240ADDD3DF17E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_829624_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

