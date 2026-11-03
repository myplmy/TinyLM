# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:373536
original SHA-256: 4784AD2791F82F27A6E0B48ABB509A2E5F262DD06D3913F11617C141C3E5428C
candidate SHA-256: 4784AD2791F82F27A6E0B48ABB509A2E5F262DD06D3913F11617C141C3E5428C
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [19, 19]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 19]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373536_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373536_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373536_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373536_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373536_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373536_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373536_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373536_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373536_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373536_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373536_0019.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:373764
original SHA-256: 5D3E8E8F63E604C844A83451C75089C837E4100E3F22365FB9E1F671C8FE4AC2
candidate SHA-256: 5D3E8E8F63E604C844A83451C75089C837E4100E3F22365FB9E1F671C8FE4AC2
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373764_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373764_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373764_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373764_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373764_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:373799
original SHA-256: A9AAB98F3819303140BE5E52B52B1C5C49AC53DB48804B3517FE210338B4496A
candidate SHA-256: A9AAB98F3819303140BE5E52B52B1C5C49AC53DB48804B3517FE210338B4496A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373799_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:373927
original SHA-256: 0F9875101AAE281CF212493D7E898086B299E4B95E8A8D066032B4011F43ED60
candidate SHA-256: 0F9875101AAE281CF212493D7E898086B299E4B95E8A8D066032B4011F43ED60
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373927_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373927_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373927_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373927_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:373943
original SHA-256: 3AF213DD8778DE43250F6DB9566D9C68AAB37B091DE445176FB908D49832FC7E
candidate SHA-256: 0CD152FD928798F304C96E38DAE0C438289E7CFCD95C472F21380B31EE049C3D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

