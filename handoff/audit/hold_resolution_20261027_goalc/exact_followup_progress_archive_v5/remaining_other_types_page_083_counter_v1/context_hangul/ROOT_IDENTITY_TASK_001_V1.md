# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1150930
original SHA-256: F900CF81ABF5F10CA8857794862E5225CD806595B24789826E786D32B6E17E2B
candidate SHA-256: F900CF81ABF5F10CA8857794862E5225CD806595B24789826E786D32B6E17E2B
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1150930_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1150930_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1150930_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1150930_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1150940
original SHA-256: B9B89F955915507EB04B507734EC0E49F0A3DBEDBD07453D7B43D382F539A2BA
candidate SHA-256: 4FEECEF4057C744BDEF93E0D77BBAD99F7972616BF6680FDE8094ABB2E949028
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1151012
original SHA-256: 52C4B5A3E00E5FD2D0262DFFBE56F8749AC0192070D4B297BE0905CF7B3B8EDF
candidate SHA-256: EE70B1C087BE2EEE72CF82C952B58A620A2AF87B7F8CEDE5271FC61A47ED6794
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1151131
original SHA-256: F729B630AF20FBB9B46FE52575D661805886101D2DADE8A0853BB29AC0C95AF3
candidate SHA-256: F534E5B74BCC5FE3FC912620F12FDA860ACB38AE43C015F6BE8DA7D9AF6E1077
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1151144
original SHA-256: FE0BB97BE6363D3427576D85A9B9901B434CB31B48BA1EDBED7664423EF5CE7B
candidate SHA-256: FE0BB97BE6363D3427576D85A9B9901B434CB31B48BA1EDBED7664423EF5CE7B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151144_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

