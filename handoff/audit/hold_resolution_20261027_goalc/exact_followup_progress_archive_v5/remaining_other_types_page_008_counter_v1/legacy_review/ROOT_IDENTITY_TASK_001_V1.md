# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:73668
original SHA-256: 912A01253E305267B798336D9004BD684910256D1FA7A010BB75415EF48E3415
candidate SHA-256: 912A01253E305267B798336D9004BD684910256D1FA7A010BB75415EF48E3415
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73668_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73668_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73668_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73668_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:73725
original SHA-256: CD3DEEAAEEB105F1406FF129E3C9A73C801C1367E9C9C0C998B522D1B8D991E3
candidate SHA-256: 4BF4F4A3CED763174673464F80278D170B46D7D0515F15A7A4ABB1E6584F5617
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:73973
original SHA-256: 56EDF949350A9EE31D7AB81D6DEF7BBB2E9B72D6B5ABDAFBC53E4718E037F48E
candidate SHA-256: 56EDF949350A9EE31D7AB81D6DEF7BBB2E9B72D6B5ABDAFBC53E4718E037F48E
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73973_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73973_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73973_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73973_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:74102
original SHA-256: 5E5439FC59FF009C12F24042FA1308B7566E8911EF65331A9B88A53E48A2A7C0
candidate SHA-256: 5E5439FC59FF009C12F24042FA1308B7566E8911EF65331A9B88A53E48A2A7C0
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_74102_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_74102_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_74102_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_74102_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:74172
original SHA-256: 5DD42B5F16E0AB760ED5CBC5B036F6A2AD1132AEBB3D91DBD0B114C9C9F95D5E
candidate SHA-256: 5DD42B5F16E0AB760ED5CBC5B036F6A2AD1132AEBB3D91DBD0B114C9C9F95D5E
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_74172_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_74172_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_74172_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_74172_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

