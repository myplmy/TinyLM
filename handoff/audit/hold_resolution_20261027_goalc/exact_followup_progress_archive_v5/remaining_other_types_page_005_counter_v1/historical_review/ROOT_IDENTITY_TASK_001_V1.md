# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:48573
original SHA-256: AFD2A90B85CDC4B7189AFB26371C25FB94F3E3800599FF3F3450A5A3D41E0774
candidate SHA-256: AFD2A90B85CDC4B7189AFB26371C25FB94F3E3800599FF3F3450A5A3D41E0774
원문 frame 패킷: [1, 24]
최종 full_diff 패킷: [47, 47]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 47]
후보 중복만 있는 생략 가능 패킷: [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48573_0047.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:48583
original SHA-256: 91D00716259A9C8FBEF05F4489C39FAA60D758BC153F05CCF90DCC49423378E5
candidate SHA-256: 069A55A519C9B8B13B90B703985CAEE72C087E0F9ECCA45BCAA2E2DA4BD7159A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:48698
original SHA-256: 784C939BDC4BB21AFBBBFD5F0177045078D09EF98DDF24C4DC6D84A81B9A5F74
candidate SHA-256: 35DC215C4047DDF64844851348DC8341521E5B463AEE9B04624B140F34D32975
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:48717
original SHA-256: D3C82EAF0D804D8200F13FA072139F902A4F9DECDABF7387469839CAFA19D638
candidate SHA-256: D3C82EAF0D804D8200F13FA072139F902A4F9DECDABF7387469839CAFA19D638
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48717_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48717_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48717_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:48843
original SHA-256: DADB2D3ABAA0CC2E18B2CF29A4D963517272A6ED14FFC36F6F0447F5FC103C66
candidate SHA-256: 90649089F5C3A2B72FB0E7A086983E39BCD38A1422B33C05FF7F310085EE2473
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

