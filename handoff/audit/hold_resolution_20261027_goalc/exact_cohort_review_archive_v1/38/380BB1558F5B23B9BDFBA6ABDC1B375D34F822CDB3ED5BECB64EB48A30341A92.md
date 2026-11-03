# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:50468
original SHA-256: 680C745A121C2488075F4D6BA4ADE1DC57D83672F7A87C6969F9F8C684E50C28
candidate SHA-256: A4A0C76B382F8CB1E9862F63D28C1DCC7894FDA2DD8F17A27150D17F0D0E306D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:50505
original SHA-256: 9BA45544B9A230254D7F0016DEC1F2D08E2F9BCE306E9818B61323D88F6913E1
candidate SHA-256: 9BA45544B9A230254D7F0016DEC1F2D08E2F9BCE306E9818B61323D88F6913E1
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50505_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50505_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50505_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50505_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50505_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50505_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50505_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:50533
original SHA-256: 6E06446053A392EF9721683EEDFFD5F4791E5DBBA572283DCAA852C1C409E1EA
candidate SHA-256: 99EB0A9CA87E763715136D6FECCC495B08008609DA0DD75DF859DE6C5E78F223
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:50689
original SHA-256: D9BD413E20F8B26DD61F7E5371F295FD489944D019FDC9D66746F08B297E823E
candidate SHA-256: 6C89237B56D2E72CBEB63514E7FF3150507B84B6486C433C4AA0138400E76430
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:50790
original SHA-256: 8514744E4CF548D56197E89A514109B45D844A3A00061ABEF164E1E617426048
candidate SHA-256: 8514744E4CF548D56197E89A514109B45D844A3A00061ABEF164E1E617426048
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50790_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

