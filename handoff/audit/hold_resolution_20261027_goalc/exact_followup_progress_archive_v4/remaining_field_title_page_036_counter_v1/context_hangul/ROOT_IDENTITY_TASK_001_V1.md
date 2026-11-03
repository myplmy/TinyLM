# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1311080
original SHA-256: E2687C875AD795FE11940658E875CA3D923E9A610D73BEABC7A000E7DB6028FA
candidate SHA-256: E2687C875AD795FE11940658E875CA3D923E9A610D73BEABC7A000E7DB6028FA
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 14]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1311080_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1311080_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1311080_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1311080_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1311080_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1311080_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1311080_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1311080_0014.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1314030
original SHA-256: D2065748282804EBF07309890D818351259B104F8774963ACD5E9E43E5F73BA0
candidate SHA-256: D2065748282804EBF07309890D818351259B104F8774963ACD5E9E43E5F73BA0
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [16, 16]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 16]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14, 15]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1314030_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1314030_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1314030_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1314030_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1314030_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1314030_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1314030_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1314030_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1314030_0016.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1319095
original SHA-256: 87BDE46F959FC4191593F419E0FA245203ABFE7A68DC3EE46F04F5C7E4310FFD
candidate SHA-256: 87BDE46F959FC4191593F419E0FA245203ABFE7A68DC3EE46F04F5C7E4310FFD
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1319095_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1319095_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1319095_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1319095_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1321984
original SHA-256: A0A78A881C0153A22638D50D9608EAB8289429113B11871810AEF011470ED3EF
candidate SHA-256: A0A78A881C0153A22638D50D9608EAB8289429113B11871810AEF011470ED3EF
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321984_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321984_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321984_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321984_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321984_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321984_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1322384
original SHA-256: 88F346D08050F3D36A1D3A8ED0F8A990D7D59D37949ABC2E4F46568F9F295C25
candidate SHA-256: 88F346D08050F3D36A1D3A8ED0F8A990D7D59D37949ABC2E4F46568F9F295C25
원문 frame 패킷: [1, 19]
최종 full_diff 패킷: [37, 37]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 37]
후보 중복만 있는 생략 가능 패킷: [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1322384_0037.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

