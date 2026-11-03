# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:100096
original SHA-256: 31C2FAA7E87792B1FB7B49A292020B19AC8460D9F617FAD925BF72CEF2CF238C
candidate SHA-256: 31C2FAA7E87792B1FB7B49A292020B19AC8460D9F617FAD925BF72CEF2CF238C
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [16, 16]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 16]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14, 15]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100096_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100096_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100096_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100096_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100096_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100096_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100096_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100096_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100096_0016.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:100171
original SHA-256: D577D2A86BFB7B418ACF06620EA455B1AB87BEF6BEB197F5CA70B89B93AD2A23
candidate SHA-256: A2C34C0D1DCFF342FE7305B58CDE97151072358CBFC2637CBAB3316C1752F8FB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:100195
original SHA-256: CED829058C601AC19FAFCC843F82442EC68120276C99CD0E8D60DC0C2FB29C6E
candidate SHA-256: CED829058C601AC19FAFCC843F82442EC68120276C99CD0E8D60DC0C2FB29C6E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100195_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:100230
original SHA-256: 6E590D58C460358CE363745B79554AC12C6546F5808BB9D3575E51F47321298B
candidate SHA-256: 6E590D58C460358CE363745B79554AC12C6546F5808BB9D3575E51F47321298B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100230_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100230_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:100264
original SHA-256: D85ACCF6774DAE8CEDE02440C516745EEB061FA65F5D85E7F0BDB48852E20F13
candidate SHA-256: 878D9EBB65A843887BE341E0C9A7EA1D03C772A8E780D11EDFDB132B86F6D6DC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

