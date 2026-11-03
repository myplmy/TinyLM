# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:575372
original SHA-256: BCE7FBE4D00F7573D2D897C57F654BF2D61B314C4B6EDABAD3F5075D80EF5896
candidate SHA-256: BCE7FBE4D00F7573D2D897C57F654BF2D61B314C4B6EDABAD3F5075D80EF5896
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_046_counter_v1/reading_packets_v1/expanded_train_575372_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_046_counter_v1/reading_packets_v1/expanded_train_575372_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_046_counter_v1/reading_packets_v1/expanded_train_575372_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_046_counter_v1/reading_packets_v1/expanded_train_575372_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:575685
original SHA-256: 4B4635FCAEDFAA6ECFB46E9B7A455C7CC5DF376A70026D1B44B6C206B2FE6866
candidate SHA-256: 4B4635FCAEDFAA6ECFB46E9B7A455C7CC5DF376A70026D1B44B6C206B2FE6866
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_046_counter_v1/reading_packets_v1/expanded_train_575685_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_046_counter_v1/reading_packets_v1/expanded_train_575685_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:575690
original SHA-256: F06484BA44E20CA530661BD2823093743AB45B270080DB3FD3B94606E99FB688
candidate SHA-256: 61FF47641FA8553B48D696FFE48DFC8ECEAEEE98C7A803738E35C421E8E15103
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:575715
original SHA-256: 0A8CC2B720E7D4FE766286C0782BA406C5ACC9501E83DABE883CA47964505D2B
candidate SHA-256: 0A8CC2B720E7D4FE766286C0782BA406C5ACC9501E83DABE883CA47964505D2B
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_046_counter_v1/reading_packets_v1/expanded_train_575715_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_046_counter_v1/reading_packets_v1/expanded_train_575715_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_046_counter_v1/reading_packets_v1/expanded_train_575715_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:575762
original SHA-256: 1D46F2F5131BC4321002522485DB7F743A9BA8CA862975BCC784721745C0D6E0
candidate SHA-256: 876467B0993B1367344BCB3CF3000146A89BAB49EBDDA4BA89223C3BF21AFEBC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

