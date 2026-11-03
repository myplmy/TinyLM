# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1150937
original SHA-256: D48E85D6DEE6DBEE8FDBA9C39B53D8545B681FE64F5A2F015FD64A971E700F61
candidate SHA-256: D48E85D6DEE6DBEE8FDBA9C39B53D8545B681FE64F5A2F015FD64A971E700F61
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1150937_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1150937_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1150937_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1150937_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1150937_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1150937_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1151178
original SHA-256: 5F41B0474623BB9861F2356B922222CA69B22B3274BA0FD2549ED3E085F05BEE
candidate SHA-256: 5F41B0474623BB9861F2356B922222CA69B22B3274BA0FD2549ED3E085F05BEE
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151178_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151178_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151178_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1151262
original SHA-256: 3799D47DF9D32DD1193708F55D5DF2D68A1FE91CA905A31EB5C7B598C4F2CBE8
candidate SHA-256: 3799D47DF9D32DD1193708F55D5DF2D68A1FE91CA905A31EB5C7B598C4F2CBE8
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151262_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151262_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151262_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1151279
original SHA-256: 22A9B65E86A26AA67B146BB13E900C45149085D1F36F664ACA3B7DEE107AD1A4
candidate SHA-256: 8A0D7419B7631299D6FF04C86DE55FC3E990831DBB80BF2276BB227972B98CD4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1151930
original SHA-256: B29A3B1E21CD3966BF1703691A004E163F3AF1D7660802C9D6AA5AD1C4EF3476
candidate SHA-256: 31B553E0364A65E20C4D42B7DC39D2D73FB282238332EED328B2E90B804C2E54
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

