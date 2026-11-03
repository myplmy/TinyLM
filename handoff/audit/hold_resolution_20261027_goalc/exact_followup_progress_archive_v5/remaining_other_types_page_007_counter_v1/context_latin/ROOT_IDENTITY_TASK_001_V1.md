# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:62036
original SHA-256: 2D2B10844423161C07211A7B39FB00C355F319CD90895FD224E83C033C6AE31A
candidate SHA-256: 2D2B10844423161C07211A7B39FB00C355F319CD90895FD224E83C033C6AE31A
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62036_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62036_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62036_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62036_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62036_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62036_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62036_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:62195
original SHA-256: 2D1907F36FCF135CEBC4F01C2FB02DF1B22CF3C6DC5C8FFAAD3DB7C7F125BAE1
candidate SHA-256: 2D1907F36FCF135CEBC4F01C2FB02DF1B22CF3C6DC5C8FFAAD3DB7C7F125BAE1
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [23, 23]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 23]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62195_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62195_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62195_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62195_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62195_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62195_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62195_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62195_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62195_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62195_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62195_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62195_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62195_0023.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:62632
original SHA-256: 5E42B0DBBE30FD0BA99F0BB5B727E680DB40916C80301E579EE7FCBD5367320E
candidate SHA-256: 65FC240884D7EF2985EED577B9F6A2634BE13426942A7044BD0EA2BB4410E26D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:62684
original SHA-256: 58C02DA137758A83C75C3935E0F531FAC757BF82144DC8841EEF54C8F4AC2AEF
candidate SHA-256: A2316083FD25C584501ADA0DBC8CB7D633FAFE83A93F3D0804D682DC9E2197F9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:62710
original SHA-256: 5BB62E2857B5F75E0DC8978BCBBD814F57272365FDC814431A79977E147128EE
candidate SHA-256: C78AB6665F876FD00FA78758E3B21CD2D5547A7F88F57BD8BBDFD6324E035EC7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

