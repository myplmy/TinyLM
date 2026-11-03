# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:765173
original SHA-256: 0E6CD08B25D1DD36F61360D2BB14896A453DCB5A38D3B826A60C33B894D20CD1
candidate SHA-256: 95F9FC919F7A50EC0C1710F021D6907FF1AEB8D09A08F206FCE939A7396AFBA9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:765223
original SHA-256: 560F296CDF881AB9D9105C0E93CF9988E72B02FFAA64EE2DA2888CD6EB08400B
candidate SHA-256: 560F296CDF881AB9D9105C0E93CF9988E72B02FFAA64EE2DA2888CD6EB08400B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765223_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:765273
original SHA-256: 632E0D32E87A7C27DBCFE4C9EB0AE3ECD10A4EB8128420339D6252B51256C05A
candidate SHA-256: 632E0D32E87A7C27DBCFE4C9EB0AE3ECD10A4EB8128420339D6252B51256C05A
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765273_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765273_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765273_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765273_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765273_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:765314
original SHA-256: 3D682E7A6C6BADB56778D10335F9CBC60EB0169A92BA2EDC349C83295513F914
candidate SHA-256: 3D682E7A6C6BADB56778D10335F9CBC60EB0169A92BA2EDC349C83295513F914
원문 frame 패킷: [1, 11]
최종 full_diff 패킷: [21, 21]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 21]
후보 중복만 있는 생략 가능 패킷: [12, 13, 14, 15, 16, 17, 18, 19, 20]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765314_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765314_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765314_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765314_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765314_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765314_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765314_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765314_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765314_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765314_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765314_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765314_0021.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:765469
original SHA-256: 9D9E2FEE9C0982ED7767147F84E60AEAE1C9661DD80DEAC66CE6A2B42B05C9A5
candidate SHA-256: 6115768BA587746AC8DFD96D0A4F1E4C97F141B3C72A18969841B976DE45D246
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

