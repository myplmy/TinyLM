# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:946829
original SHA-256: 8305F7091FDB238324E14ADD4FD7A6A40C18AFEEA080719D0555C331C817029E
candidate SHA-256: 265643EADB7988EBE9DEE9502C9FE61DCF97E4E870C0D9E4DFA3029F2624BFD6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:947004
original SHA-256: 84170FB8740DB6D9BE15269B43639C9D210D87E20974F13D82CEF4213FD276D5
candidate SHA-256: 84170FB8740DB6D9BE15269B43639C9D210D87E20974F13D82CEF4213FD276D5
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947004_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947004_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947004_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947004_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:947092
original SHA-256: 7D50BFDD7C0C2E14215C005E023DCE3E5E3EF36CEFA5A8122556969A2841A875
candidate SHA-256: 7D50BFDD7C0C2E14215C005E023DCE3E5E3EF36CEFA5A8122556969A2841A875
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947092_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947092_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947092_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947092_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947092_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947092_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:947095
original SHA-256: 63D172D971A47D693A366C173934884F59C6A8378358D0AE796A131F2A578C6C
candidate SHA-256: 8EB6B3721D5BE313DB87414E8DC1F9A55ECBB7F14A0A6CF56259E367C19E12EB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:947097
original SHA-256: CC56E2084C8AC9B2376BBB6C0E198BAC32640C63C0D4628504ED5E8639DEF745
candidate SHA-256: CC56E2084C8AC9B2376BBB6C0E198BAC32640C63C0D4628504ED5E8639DEF745
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947097_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947097_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947097_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947097_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

