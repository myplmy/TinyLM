# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1131027
original SHA-256: A43AAF3B1666ECCD73DFC003577AC06599EB2A1E3CFE24C8E2F2918EB8FD868A
candidate SHA-256: E12E0629FC8E0E9B2E4F34F99C63A628F24521BE340A9C128543E80643EBDC74
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1131199
original SHA-256: 0CA658232039D4F12CCCDAB930B6B98D6A5F1B16044F8F552B85DC9C90A3465F
candidate SHA-256: 0CA658232039D4F12CCCDAB930B6B98D6A5F1B16044F8F552B85DC9C90A3465F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131199_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1131211
original SHA-256: 6863BF8A15E02F6ACFF3D39791ECCBDCEDC18529576A918553740177AB98DB62
candidate SHA-256: 6863BF8A15E02F6ACFF3D39791ECCBDCEDC18529576A918553740177AB98DB62
원문 frame 패킷: [1, 21]
최종 full_diff 패킷: [42, 42]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 42]
후보 중복만 있는 생략 가능 패킷: [22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131211_0042.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1131623
original SHA-256: F792E96A07501C95362B3CE167D32807DAFDB16F12322ADD6B144490DA211236
candidate SHA-256: BF6F13E03724D2A0BE326E6F3941F5FC95AEE9A2CCBCE48A76E2A04CB686A691
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1132323
original SHA-256: 7604FDC3F2C1CDD495FB03BD54084EA4DF49899EE40E31BB1D0AE6E74AE1A712
candidate SHA-256: 32E28F61339597EEC4A56458C95BA67A74FF53366D15FEA97F1C853C05DDA522
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

