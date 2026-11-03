# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:10011
original SHA-256: 798426B44B9AA58BF415BB6A71111428CF1649D150FDA40234381CD9C3165C5B
candidate SHA-256: 798426B44B9AA58BF415BB6A71111428CF1649D150FDA40234381CD9C3165C5B
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_10011_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_10011_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_10011_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_10011_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_10011_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:10073
original SHA-256: 01899C43B110FBFFD80634CED18700A2B164202B3F1B292F1E6B99E19D27D7AD
candidate SHA-256: 01899C43B110FBFFD80634CED18700A2B164202B3F1B292F1E6B99E19D27D7AD
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_10073_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:10113
original SHA-256: 4BD246D415315C1DD692FE5FA14B8600B85B61A0908C951F4F885D6C5110E45E
candidate SHA-256: 5E1C295204E4B331211F52B53877D05AEEFE5875D903BF4586F6E5F127112C1E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10176
original SHA-256: 1D7D561DA0529CEECE3198BB26B3CB8F38DFD8A133DF596E11811B819DA596C5
candidate SHA-256: 3EB477655741512C4E58761804D0EF1DB47B1CC2C185B02FE25034FCD914AB70
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:150
original SHA-256: 592874FD27132A418862750D938A9942D3E6D66BF281F3E0530E2A142FC85E96
candidate SHA-256: 17EECAFFBDA262BE434D14726A3A09B644A1F49584E4A3767DC84C384FB65A80
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

