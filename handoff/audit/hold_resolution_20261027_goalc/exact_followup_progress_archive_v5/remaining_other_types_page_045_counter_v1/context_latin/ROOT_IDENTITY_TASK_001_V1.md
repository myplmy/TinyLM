# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:561168
original SHA-256: 9EBE36B4D650DE516F16EE183DF7CA11EA30DAAB70128D3F25B2C70AA997BD76
candidate SHA-256: D0F014877754A1F2F80106DA6A52FD4923757E97DE761DB6A06F944C1014AD2C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:561219
original SHA-256: FBC2892DF106AAA0AE91FB6E8391A3279F3269FE778A977BFD8EAA1E7C69DB0B
candidate SHA-256: FBC2892DF106AAA0AE91FB6E8391A3279F3269FE778A977BFD8EAA1E7C69DB0B
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561219_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561219_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561219_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:561367
original SHA-256: CBEAC949DEDA66107BAE320FEDBC632799975C2DF6016355A50BAD149AF69A59
candidate SHA-256: B7FE024DB431393BFF048125BE1E61370364335622DDDB7D657965758DE5DD87
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:561472
original SHA-256: B5943CD3FB9832B75DBC0FA788FB30F3D83C8628F3CEE4C920BA9FFC2D00D115
candidate SHA-256: B5943CD3FB9832B75DBC0FA788FB30F3D83C8628F3CEE4C920BA9FFC2D00D115
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561472_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561472_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561472_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561472_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:561796
original SHA-256: DF1B72176DBE59FAE0FBFA9BBE711632C577DBEBC0E0C17B5C5990FBDE541B56
candidate SHA-256: DF1B72176DBE59FAE0FBFA9BBE711632C577DBEBC0E0C17B5C5990FBDE541B56
원문 frame 패킷: [1, 13]
최종 full_diff 패킷: [25, 25]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 25]
후보 중복만 있는 생략 가능 패킷: [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561796_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561796_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561796_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561796_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561796_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561796_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561796_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561796_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561796_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561796_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561796_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561796_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561796_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561796_0025.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

