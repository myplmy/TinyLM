# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1116470
original SHA-256: 74AA735DBB1635BD84FAB93E3DC21CE1B3AF6785EA7B601D935715DCB80DD539
candidate SHA-256: 74AA735DBB1635BD84FAB93E3DC21CE1B3AF6785EA7B601D935715DCB80DD539
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116470_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116470_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116470_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1116723
original SHA-256: 24E88767D4A865315969CF7FB633806615D260267015B9685216D3411A2EEFE5
candidate SHA-256: BBCACBE2D1AD1D39193D54A6440C03ABBFDC826A475EEEB0E34172EC7B48519E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1116741
original SHA-256: 508701E58E4287DF53B6550AF43E42B27C25D673A0BC796089D4022B3741955F
candidate SHA-256: 99AC3C724328B32FA87AE66D8766D4AC85664B87396FF779BC09757B8B201673
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1117000
original SHA-256: AEF7D5B1E8B7F2F12BC35248643D9B070509F9E27E849AA05217AB7BCC3DF121
candidate SHA-256: AEF7D5B1E8B7F2F12BC35248643D9B070509F9E27E849AA05217AB7BCC3DF121
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1117000_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1117065
original SHA-256: 8531EA593369207981D7BDFC66BD77CB670E6B78D097C08D1AD655C82C319989
candidate SHA-256: 2A209775BC72BA7C5739F0217BFB786D8B45BD6376B4D5FE03E2DF0B74FF6B7D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

