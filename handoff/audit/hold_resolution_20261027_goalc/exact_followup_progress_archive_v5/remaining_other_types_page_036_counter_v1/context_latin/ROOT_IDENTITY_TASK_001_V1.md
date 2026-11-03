# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:431297
original SHA-256: E540A8421FAB5CE6F4865EA23E471B123FBF2913A3DB4F4650AF854E5C287E8D
candidate SHA-256: 4B249B2E7BCB4F0036C0B524235924CAF64B892BEA04A2ABFB7AC5C7F1B8EDD7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:431446
original SHA-256: 5C89859846FF38B7BA868F3B7CA544BB5F93EFBA4FF1B190809F13879CE48BB6
candidate SHA-256: 5C89859846FF38B7BA868F3B7CA544BB5F93EFBA4FF1B190809F13879CE48BB6
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431446_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431446_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431446_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431446_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431446_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431446_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431446_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:431529
original SHA-256: 3F6865E6612BB8F8DD65068B67506C55B3B5B6D6318871BCE8A5644DA1DFB544
candidate SHA-256: 3F6865E6612BB8F8DD65068B67506C55B3B5B6D6318871BCE8A5644DA1DFB544
원문 frame 패킷: [1, 16]
최종 full_diff 패킷: [31, 31]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 31]
후보 중복만 있는 생략 가능 패킷: [17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431529_0031.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:431594
original SHA-256: C51DC775967941E6C2B66DDF3DC3D9105CB8878C745BBE7380F479E8DD934D68
candidate SHA-256: 6EE466E2DC0590A35E9EEACE35EF268CB1D38FC1BC9DA3332B0FC55E1433B1AD
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:432151
original SHA-256: ADC3D8AA249883372D168626051DC38FCD055EEA250DE364BD743AE0363C19C6
candidate SHA-256: 0AC3C9B643A20FF515FC192A68CD5451677E6BFCE577ACDD3DAC26422FADED71
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

