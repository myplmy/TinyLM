# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:332061
original SHA-256: 4999A612612B805C8B91C29545D444B6A17CF68E55029BD67A8EFBEDA94BAD65
candidate SHA-256: 4999A612612B805C8B91C29545D444B6A17CF68E55029BD67A8EFBEDA94BAD65
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332061_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332061_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:332181
original SHA-256: 4122046A07E49795C51DC37EE7ABA386D4B414DFE9C3EED5316B455E502BD061
candidate SHA-256: 4122046A07E49795C51DC37EE7ABA386D4B414DFE9C3EED5316B455E502BD061
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332181_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332181_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332181_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332181_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332181_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332181_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332181_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:332200
original SHA-256: 97ED1E08DDD959F5404EFB9743A4EB49D3E933AC18C839B386EF1B235BCDFDD1
candidate SHA-256: 6E37F58882F15F896F8E8C91EBB8418393348B062DE1A972003169952AF0D0AF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:332359
original SHA-256: 26A1D73698A8F213E2B489A7B3CC54E6FBE7DE5D32EEA98ECCE8ADA1E976EA6C
candidate SHA-256: 26A1D73698A8F213E2B489A7B3CC54E6FBE7DE5D32EEA98ECCE8ADA1E976EA6C
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332359_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332359_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332359_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332359_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332359_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332359_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:332376
original SHA-256: EB4FD7103CFD3EF71C4622F65C40A1083CA6C134A360444EA2369C203EE3FF1C
candidate SHA-256: 4576F6C37C5C86F714F6D26015C0FCBD9DCBEC9227A559A6E6CBB8E1589FAEC5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

