# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:529869
original SHA-256: 78D0FF5C79F1408DB6B45C42BF061B0056587090C10A0F01FDAC66C16C81C8C6
candidate SHA-256: 78D0FF5C79F1408DB6B45C42BF061B0056587090C10A0F01FDAC66C16C81C8C6
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [18, 18]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 18]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16, 17]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529869_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529869_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529869_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529869_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529869_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529869_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529869_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529869_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529869_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529869_0018.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:529897
original SHA-256: 3FEC51978A62C38184774E36CCADA16CE0235CD0C8F08218EAAE4EAC1E190803
candidate SHA-256: 5E4BDDBD0F77745A80CB494DF47A8D055D28E13957BC79D647396C0F85469A1C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:529922
original SHA-256: 9E4DBD674F09A817A5D6AA3E9D8EC81978EAF5327DA0202E1ACCD37B3DC39D82
candidate SHA-256: 9E4DBD674F09A817A5D6AA3E9D8EC81978EAF5327DA0202E1ACCD37B3DC39D82
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529922_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:529926
original SHA-256: D892F4B53BAA3E8CC525B7EA8185756E8DE8A7734E56E5BE96E15D9796115434
candidate SHA-256: 1C2888368D4E68F6B09015C6E86263049AEE6F1CB36B377B3DF575E7093E140C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:530034
original SHA-256: DBFA2884F289268DDD62B1361F03EFBAF3A1DC85B3A90876F32B2513DEE19B84
candidate SHA-256: 96F070AF46AEE606A24CF6303C9EACFDBF5C0839E2BBE892ADA4DCC0E73D32F0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

