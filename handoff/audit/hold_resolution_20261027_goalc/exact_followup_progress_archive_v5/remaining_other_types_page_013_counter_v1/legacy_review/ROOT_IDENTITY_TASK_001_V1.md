# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:126722
original SHA-256: 44606B73B80EE0DDA0B8020FF11A73E88363CBBDDDB833D0F23E80380DF79157
candidate SHA-256: 603E5940D5C20FA2408059336B152E44826783717E3EC6E3D0042BA792B9DB59
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:126766
original SHA-256: 2501C8DD6743F5A08D38ED99AEA648D5D927EB2B33D708F83F382321A63B4EF5
candidate SHA-256: 2501C8DD6743F5A08D38ED99AEA648D5D927EB2B33D708F83F382321A63B4EF5
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126766_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:126779
original SHA-256: 6943E307D025F72639B48D1B9F229C1FDE94D4206A73427BDD6B6399B237C01D
candidate SHA-256: 0E481401B6A91F4A4963C69B38795A7B9800E784CD770BB09A899F797A4DADDE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:126866
original SHA-256: B328618DDD7F2A3CBD84B9957C50723AE5F9C41D65B2E635A995A300A46E360D
candidate SHA-256: B328618DDD7F2A3CBD84B9957C50723AE5F9C41D65B2E635A995A300A46E360D
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126866_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126866_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126866_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126866_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126866_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126866_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126866_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126866_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:126913
original SHA-256: BB60414CE41DFFDA7CD86E985D762A44237DCAFB32532E8B7B83A0103D8CD211
candidate SHA-256: BB60414CE41DFFDA7CD86E985D762A44237DCAFB32532E8B7B83A0103D8CD211
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126913_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

