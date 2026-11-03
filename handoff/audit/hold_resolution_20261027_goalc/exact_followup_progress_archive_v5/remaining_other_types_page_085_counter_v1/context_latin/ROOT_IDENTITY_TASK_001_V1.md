# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1183416
original SHA-256: 9567D72F7278A85F1755B14B5E03EB756FBC87C09CB473F09AF4231735012E63
candidate SHA-256: 9567D72F7278A85F1755B14B5E03EB756FBC87C09CB473F09AF4231735012E63
원문 frame 패킷: [1, 14]
최종 full_diff 패킷: [28, 28]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 28]
후보 중복만 있는 생략 가능 패킷: [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183416_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183416_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183416_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183416_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183416_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183416_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183416_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183416_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183416_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183416_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183416_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183416_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183416_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183416_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183416_0028.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1183746
original SHA-256: 8A8C195FF5062D42E209BB461779C3D5477E15C7EFEB3A61089D27AE4CD49E50
candidate SHA-256: A243B83D102F376CC527FFB21914C11C60E88F3FE257A853D0718B8161581B57
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1183793
original SHA-256: A9643B408F2FB50F2F8D6EDE95463592B90F749D494F180727E70E5B3A48AA98
candidate SHA-256: A9643B408F2FB50F2F8D6EDE95463592B90F749D494F180727E70E5B3A48AA98
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183793_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1183937
original SHA-256: 1C3CD6AC0772B10A0C9A540887D73ED438B7B2F5F2067383B212F87ACAAB38B6
candidate SHA-256: 1C3CD6AC0772B10A0C9A540887D73ED438B7B2F5F2067383B212F87ACAAB38B6
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183937_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183937_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183937_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1184238
original SHA-256: 44113FE6941FBB8E35FC7A01FD1B0B37A32B841B43F39F24E83C16E5269798DC
candidate SHA-256: 793AC0B09C74E1DDADD53BB6684F7B54E4C386E994C70050774A56EE35EC992D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

