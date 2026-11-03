# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:231628
original SHA-256: 6A1A58870AA6BD543DA180678D34EBFBEDCAEB72BC36ED68E772B5C559541E69
candidate SHA-256: 45CB59380F079C3CDCA5A33EC271812CC722C1386F264B29DC24D1351FF97200
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:232039
original SHA-256: 3E6B3625E0AC4030DD16EAEB74F980FF58D5BF4A169BCF20139A1AA1A17A411B
candidate SHA-256: 3E6B3625E0AC4030DD16EAEB74F980FF58D5BF4A169BCF20139A1AA1A17A411B
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [19, 19]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 19]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232039_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232039_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232039_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232039_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232039_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232039_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232039_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232039_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232039_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232039_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232039_0019.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:232212
original SHA-256: 137FDD6FF709C7E276DF72CE9F7481FFC4F65C3F6932CC59285C72E8016F501D
candidate SHA-256: 137FDD6FF709C7E276DF72CE9F7481FFC4F65C3F6932CC59285C72E8016F501D
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232212_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232212_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_021_counter_v1/reading_packets_v1/expanded_train_232212_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:232252
original SHA-256: FC7DF3FDB2622848F3B0EB438FE4FC4CFE6FC888E6B0F4AC3E844803E68B7FAF
candidate SHA-256: 7759BEE00504ECDDB67D07ABEAD3EAB09F156C75923BD78A89C84B01947E4122
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:232260
original SHA-256: 01B476457B4B96189C17C7D691F46B9A6111DFDDABABF547F33C13A8AFA33CD5
candidate SHA-256: DB793AB45C59D67679DE8C0CE2D0377DE394A200AD12742018F584596ED6C36D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

