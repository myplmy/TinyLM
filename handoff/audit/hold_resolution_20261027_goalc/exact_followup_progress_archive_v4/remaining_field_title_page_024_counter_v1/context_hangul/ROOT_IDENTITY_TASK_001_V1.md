# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:736111
original SHA-256: A0F07190DC63A90BC31B16E16C389DBF3AA07DC271C13682691996FF7B18C8B4
candidate SHA-256: A0F07190DC63A90BC31B16E16C389DBF3AA07DC271C13682691996FF7B18C8B4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_736111_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_736111_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:736447
original SHA-256: A955F348BE60A0C499739AF0D02B9287B8093153EAC28DDFB4630447DED295EF
candidate SHA-256: 9C9B2EF3A7A7525B800060F24B0062DFE4EBD68823A95B75C57A7125572E67F5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:737000
original SHA-256: 00EC2A6B5A6D491809CAB7EB4D0F631B8E22630AC7ECD046FE0FD16BD72AC9B5
candidate SHA-256: 391E015D125688E1A24A1AB5BBDFEC427C93EAFFFA8889B3DC002BFBD4CFB382
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:738160
original SHA-256: DE39B564AB24B48731641370218FD1A3A3C2E1386B7C9C2007882F1F3D751B05
candidate SHA-256: DE39B564AB24B48731641370218FD1A3A3C2E1386B7C9C2007882F1F3D751B05
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_738160_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_738160_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_738160_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_738160_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:738460
original SHA-256: F5CD85B6946CB19936A2BE2DC379A3134D69B0819A8B38C9947E11A2DA9C779C
candidate SHA-256: 3379AC8A8743796C8A0951EF5B9D7D47D39BC937999630BDB3C1B8292C80ADEA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

