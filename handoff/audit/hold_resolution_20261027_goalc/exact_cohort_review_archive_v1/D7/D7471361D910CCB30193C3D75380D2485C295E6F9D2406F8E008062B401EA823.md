# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:50396
original SHA-256: B6EFE1115748C26A064A51C820AA092B9B4CE36DBC671D04C73238905EB6A14C
candidate SHA-256: AA191C15D18B4B4223F88ADB5FA80902892A7684721B95BAC39566979FC1B441
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:50466
original SHA-256: 38063E9C8D2265DFE4F79764F9E1F264FF4C4455778B7A5A6A183342C9548B4E
candidate SHA-256: 60FB1DF202438FDBBF80A2819B768CDDFE0E6C2A8538E3B125A313F802D43E2F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:50892
original SHA-256: 59B1A2516201111B7141258D23B5DE24D0B4F826D5D3E556F134505F17B0F243
candidate SHA-256: 59B1A2516201111B7141258D23B5DE24D0B4F826D5D3E556F134505F17B0F243
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50892_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:51059
original SHA-256: F717024DF83EE1098990CDBEB5ACD6C444220AD00A12A759693CFFB0C967FA80
candidate SHA-256: F717024DF83EE1098990CDBEB5ACD6C444220AD00A12A759693CFFB0C967FA80
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_51059_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_51059_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:51400
original SHA-256: BBE30E3BE78ED85C1C48423C7D26F8B101B115B579CBBA8A80642CB130ED32A4
candidate SHA-256: BBE30E3BE78ED85C1C48423C7D26F8B101B115B579CBBA8A80642CB130ED32A4
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_51400_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_51400_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_51400_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

