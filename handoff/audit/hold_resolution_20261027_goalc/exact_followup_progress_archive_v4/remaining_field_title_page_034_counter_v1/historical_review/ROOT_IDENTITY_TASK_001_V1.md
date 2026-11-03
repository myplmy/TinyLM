# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1247047
original SHA-256: 80B655AF853127C5151383476813E208B4874D430074C876493D1A21C715EC6F
candidate SHA-256: 80B655AF853127C5151383476813E208B4874D430074C876493D1A21C715EC6F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1247047_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1247963
original SHA-256: 9A6BDCB7273BBD48501201D4866529244975EEDF46F98DC5CF94326F591EA58F
candidate SHA-256: ECA2E35D5CAB0653E296982A5CEC3CEEDF492EEF910577CEAC277D5C9BC7751F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1248084
original SHA-256: A3EE6C498957195AD7161D654C2D0B087C4AA6B6114B6D496B2F221D293AF75D
candidate SHA-256: A3EE6C498957195AD7161D654C2D0B087C4AA6B6114B6D496B2F221D293AF75D
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248084_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248084_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248084_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1248541
original SHA-256: 4EBE80E59D5F2C6C392ED955BC12B94E12186B31854D2F1317427F9E3EFFB89E
candidate SHA-256: 4EBE80E59D5F2C6C392ED955BC12B94E12186B31854D2F1317427F9E3EFFB89E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248541_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1248614
original SHA-256: 069E46A63971BE25CFC53C598AC0F4ECCC3BE215BA857A4F4FB0F2CD4805CDFB
candidate SHA-256: 37D1F525D03335EC1113F13F07580ED796900E679FAC3C603578E212192A3F64
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

