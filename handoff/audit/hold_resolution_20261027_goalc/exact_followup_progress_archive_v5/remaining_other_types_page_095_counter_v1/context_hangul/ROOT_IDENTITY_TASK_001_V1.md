# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1361106
original SHA-256: AEC3C368C07C19726CE4851D195CAC9739762130464516C30F6FAAC896AC9B8C
candidate SHA-256: AEC3C368C07C19726CE4851D195CAC9739762130464516C30F6FAAC896AC9B8C
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361106_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361106_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361106_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361106_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361106_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1361215
original SHA-256: F5970F0BE2C3213DC0D136E6AAF10F848675608B696DCC4EECC2308D4CDE2138
candidate SHA-256: B8BB4E829E8FC2260DDE23ED532A9B187400EC101002E358F30E9295C42F6A0E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1361292
original SHA-256: 55E054DA998CFE4FFB5017CD8CBA713F120DFA4D32CE99D101BE1C6BF47F044A
candidate SHA-256: 55E054DA998CFE4FFB5017CD8CBA713F120DFA4D32CE99D101BE1C6BF47F044A
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361292_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361292_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361292_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361292_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361292_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1361396
original SHA-256: F2143C7090C88175861D58BB6C71B8A7F1A707B06A0C7578C12C95F3FD367BA4
candidate SHA-256: F2143C7090C88175861D58BB6C71B8A7F1A707B06A0C7578C12C95F3FD367BA4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361396_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1361447
original SHA-256: ACF6B7C49097F116C47E3BA31FDB488636771D816668C750D146F913AAF2363D
candidate SHA-256: ACF6B7C49097F116C47E3BA31FDB488636771D816668C750D146F913AAF2363D
원문 frame 패킷: [1, 14]
최종 full_diff 패킷: [27, 27]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 27]
후보 중복만 있는 생략 가능 패킷: [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361447_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361447_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361447_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361447_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361447_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361447_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361447_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361447_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361447_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361447_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361447_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361447_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361447_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361447_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361447_0027.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

