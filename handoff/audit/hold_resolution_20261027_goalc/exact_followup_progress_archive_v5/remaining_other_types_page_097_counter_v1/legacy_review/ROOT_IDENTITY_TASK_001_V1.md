# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1401924
original SHA-256: 066A9DD73F2845C68B66B4E53400F4E76E7EAF8B7B6719DE691004DF099B2E88
candidate SHA-256: 066A9DD73F2845C68B66B4E53400F4E76E7EAF8B7B6719DE691004DF099B2E88
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401924_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401924_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401924_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401924_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401924_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401924_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401924_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401924_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1401986
original SHA-256: 08853343D302FFCF326AF482CB1242E1D2D308DFB367068D795B2ECFE503D97D
candidate SHA-256: 08853343D302FFCF326AF482CB1242E1D2D308DFB367068D795B2ECFE503D97D
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401986_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401986_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401986_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1401986_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1402288
original SHA-256: CB69CCE0C13E609D34C25C73632FC3AE68D285A9D083E37E2602B748198EB19E
candidate SHA-256: CB69CCE0C13E609D34C25C73632FC3AE68D285A9D083E37E2602B748198EB19E
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402288_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402288_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402288_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402288_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1402431
original SHA-256: 4CB5884D3ABBA27443C50A0228ED2514C1BF03D30B1ACF600DDE2BA83E4B5F97
candidate SHA-256: 4CB5884D3ABBA27443C50A0228ED2514C1BF03D30B1ACF600DDE2BA83E4B5F97
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 4, 5]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402431_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402431_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402431_0004.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402431_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1402433
original SHA-256: 122421E7136E80F468AAA08D63E61958E8DE296F90A66AC3A5AA15FC79D50618
candidate SHA-256: 122421E7136E80F468AAA08D63E61958E8DE296F90A66AC3A5AA15FC79D50618
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402433_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402433_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402433_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402433_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_097_counter_v1/reading_packets_v1/expanded_train_1402433_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

