# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1071178
original SHA-256: 9378265D4A82F2B2793F2EBADF4E1A397C6EDF6E8E700EBBB56E989A4E2C68FD
candidate SHA-256: DBC5AA0D8B0662721407BF708C53F9BE022C3977F780054193EC0E1E1BE36A6D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1071295
original SHA-256: 29A8EBB7A0FB8780E53A900A0141C95785A6326A75D67D2C8407C4F2D774E314
candidate SHA-256: 29A8EBB7A0FB8780E53A900A0141C95785A6326A75D67D2C8407C4F2D774E314
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071295_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071295_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071295_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071295_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071295_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1071328
original SHA-256: F48A0C602782844BF7C19825A5640F1E597DEC758C33471A1D8FE549E108D7C5
candidate SHA-256: F48A0C602782844BF7C19825A5640F1E597DEC758C33471A1D8FE549E108D7C5
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071328_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071328_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071328_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071328_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1071343
original SHA-256: CBBD2BD4C09EC1EE487312DB79E1F14E0DC3B031FD1D660EE55F6C20EAB57B0A
candidate SHA-256: CBBD2BD4C09EC1EE487312DB79E1F14E0DC3B031FD1D660EE55F6C20EAB57B0A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071343_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071343_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1071465
original SHA-256: D9EF2F942176A1DB2626548E561B1DF4B0509E687AD4E5974A44BE4A8DEB6263
candidate SHA-256: D9EF2F942176A1DB2626548E561B1DF4B0509E687AD4E5974A44BE4A8DEB6263
원문 frame 패킷: [1, 17]
최종 full_diff 패킷: [33, 33]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 33]
후보 중복만 있는 생략 가능 패킷: [18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071465_0033.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

