# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1264688
original SHA-256: C01FD31B053C449D35FA0B3C8C409AE4930899647E8E73E5DB7A72BBE978208E
candidate SHA-256: C01FD31B053C449D35FA0B3C8C409AE4930899647E8E73E5DB7A72BBE978208E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264688_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1264732
original SHA-256: 7A15EF88EE8BBDF5BBF79072400F0D50080DBE6CBA639E88295DDA5FDF896452
candidate SHA-256: 7A15EF88EE8BBDF5BBF79072400F0D50080DBE6CBA639E88295DDA5FDF896452
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264732_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264732_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264732_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1264798
original SHA-256: 40E3FEB1C4CB7DCB9AFCF201C9CE1B0B947030994236D4CAAC4643DFCB5CAA27
candidate SHA-256: 22E585B526DD4ABDDEAF9650A5AD7BB31897606948F20A864635EBBD923CF86F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1264816
original SHA-256: B50C6C23BE31D90E7FB875BBF938A825FD103D0A11192752EDCE76BB42E576B6
candidate SHA-256: B50C6C23BE31D90E7FB875BBF938A825FD103D0A11192752EDCE76BB42E576B6
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264816_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264816_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264816_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264816_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1264987
original SHA-256: A9E35217EC02F31AFE433F5DBAD37719DDF272228D4DD4A2D50A62C5B8677727
candidate SHA-256: A9E35217EC02F31AFE433F5DBAD37719DDF272228D4DD4A2D50A62C5B8677727
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264987_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264987_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264987_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264987_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

