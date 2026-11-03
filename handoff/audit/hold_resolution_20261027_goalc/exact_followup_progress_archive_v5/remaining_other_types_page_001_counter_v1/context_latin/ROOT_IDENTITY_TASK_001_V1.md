# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:161
original SHA-256: 3DE4E50FCD7035881D97D7EE4C2E4B1146A4BD326F73E45CFF1C5EE9D3FBF8F5
candidate SHA-256: 1CCD46388C7BCB342C73A788B67776C47DE5683098A2951B61DEF092B8691E84
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1632
original SHA-256: 46232517DD56A005BD0585243CED09A83BF55703BB7D1CA06630F34D025F9A2B
candidate SHA-256: 46232517DD56A005BD0585243CED09A83BF55703BB7D1CA06630F34D025F9A2B
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1632_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1632_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1632_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1632_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1632_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1632_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1689
original SHA-256: C22CF8444072F824C89E4FC2B3EF3E6828D57AC80B5D943BADE8D1CDEDBF0BD6
candidate SHA-256: 3CB2B8BC2EE3562BE9F23DACE192891D288099D5266391878B493AC5CBCD82F2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1795
original SHA-256: 63C9E98047AA57C28048F096849D4D3C04ADD2C98B14925F1E6EED951400FAF7
candidate SHA-256: 3C7D29C4421F1534A2FD6D7F8B2D49A99DD7CD86D779274A2B281ADE2D11C71D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:2044
original SHA-256: B09D93BBD23F8CA87A2AC13FEACA9481640A8F8EAED51F3786BAE3A11F04E166
candidate SHA-256: CF20794BF89B0D35BEA6AF651EBC36054773E1D910B9F50CB519F73282D65950
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

