# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:10040
original SHA-256: 8451F90F8857E0C400EB84E64893574E0811E26E5DFA8237060106E159328EAD
candidate SHA-256: EA907A995C74F90B4650F182E0EFDD29288EF894C3B46A59F3EA9C1AC2F6D4A7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10076
original SHA-256: 94F7BDA7EE645EF146EFFE8EE2BD58E8D78D0EE5A609D0317CD18955B2B34A0C
candidate SHA-256: 89EF81280C887D82184FFEB122918AC592758450E3300021D14AC21DC78B6C9F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10202
original SHA-256: 8F42D993F7C63810E308DEBB30AB30A3E984A71726F625C11295AE8EC6FF1EB7
candidate SHA-256: 138DAD92A880A0693B4A7A9F2CC1E6FA52F85B16C0C5CDD2CC2DB6EEECBEB10F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10341
original SHA-256: A7B39EB9E16384A46DCAE6A3F447F92E04EDF98D040EB22F110DDF71D9959803
candidate SHA-256: A7B39EB9E16384A46DCAE6A3F447F92E04EDF98D040EB22F110DDF71D9959803
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_002_counter_v1/reading_packets_v1/expanded_train_10341_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_002_counter_v1/reading_packets_v1/expanded_train_10341_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_002_counter_v1/reading_packets_v1/expanded_train_10341_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_002_counter_v1/reading_packets_v1/expanded_train_10341_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_002_counter_v1/reading_packets_v1/expanded_train_10341_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_002_counter_v1/reading_packets_v1/expanded_train_10341_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_002_counter_v1/reading_packets_v1/expanded_train_10341_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_002_counter_v1/reading_packets_v1/expanded_train_10341_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:10394
original SHA-256: 98D75F48E446A3EA94AA9000C0551DA16066C89A6331C325341FBF5FF9A9B7CC
candidate SHA-256: 98D75F48E446A3EA94AA9000C0551DA16066C89A6331C325341FBF5FF9A9B7CC
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_002_counter_v1/reading_packets_v1/expanded_train_10394_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_002_counter_v1/reading_packets_v1/expanded_train_10394_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_002_counter_v1/reading_packets_v1/expanded_train_10394_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_002_counter_v1/reading_packets_v1/expanded_train_10394_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_002_counter_v1/reading_packets_v1/expanded_train_10394_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_002_counter_v1/reading_packets_v1/expanded_train_10394_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

