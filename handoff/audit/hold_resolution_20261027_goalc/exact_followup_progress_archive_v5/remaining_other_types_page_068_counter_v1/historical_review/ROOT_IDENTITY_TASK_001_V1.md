# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:896039
original SHA-256: D5A9A155035094C7C7288BF75C23BEDC8B68464E2678C2954918EA68E6457D3B
candidate SHA-256: D9CDB54BE73F782F21937F82B28B74184F2EFBFB9C50F1F3D713F3FCC4C97AAC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:896290
original SHA-256: 3126DA66F574E5213F0A4EB4F55A7E3C522F2C6214C5E4FEF6CC28AA81AA433F
candidate SHA-256: 3126DA66F574E5213F0A4EB4F55A7E3C522F2C6214C5E4FEF6CC28AA81AA433F
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896290_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896290_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896290_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:896735
original SHA-256: C6CDFCF6E9E76CD715620DA5F1654A931BB535A5D6D88239F21AED5970B99B73
candidate SHA-256: C6CDFCF6E9E76CD715620DA5F1654A931BB535A5D6D88239F21AED5970B99B73
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896735_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896735_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896735_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896735_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896735_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896735_0010.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:896753
original SHA-256: EFD6D9AE6E2BEF163ED6A9F85913705107FF7910301ED4FA4AC607B7DB657214
candidate SHA-256: EFD6D9AE6E2BEF163ED6A9F85913705107FF7910301ED4FA4AC607B7DB657214
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [18, 18]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 18]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16, 17]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896753_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896753_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896753_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896753_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896753_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896753_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896753_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896753_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896753_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896753_0018.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:897084
original SHA-256: 8213DFADB09ECE7A9563D08A5C2B340F4329866F00C20D1989AD1D4A216D5F21
candidate SHA-256: 8213DFADB09ECE7A9563D08A5C2B340F4329866F00C20D1989AD1D4A216D5F21
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_897084_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_897084_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_897084_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_897084_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

