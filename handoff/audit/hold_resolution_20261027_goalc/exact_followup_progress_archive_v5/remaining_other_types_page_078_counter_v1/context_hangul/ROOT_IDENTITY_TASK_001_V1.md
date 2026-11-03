# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1071054
original SHA-256: 9D2F6613BE1DFFECA072397E2A94A7C79EF111E12E33DD768D3F06313B467543
candidate SHA-256: 9D2F6613BE1DFFECA072397E2A94A7C79EF111E12E33DD768D3F06313B467543
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071054_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071054_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071054_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071054_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071054_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1071061
original SHA-256: B66846CBF7393CA2225C595C9C1791F3499D90587DD16E8F79598ADA72F150C6
candidate SHA-256: B66846CBF7393CA2225C595C9C1791F3499D90587DD16E8F79598ADA72F150C6
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071061_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071061_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071061_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071061_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071061_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071061_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071061_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071061_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1071298
original SHA-256: 628EC028E682F472D0EB11519CCD5286202A2E5CA4F65C5877949B741D32D741
candidate SHA-256: 628EC028E682F472D0EB11519CCD5286202A2E5CA4F65C5877949B741D32D741
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [15, 15]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 15]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071298_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071298_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071298_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071298_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071298_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071298_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071298_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071298_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071298_0015.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1071446
original SHA-256: DFD9AA11B5197E9F71E84862F474D358C2C6D826BF41C6DA4551F6827DC8D717
candidate SHA-256: 5573CD5C292F551BC5103A6FD3F6F307F2A0FA397146C3067F75177CCBAB22CA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1071511
original SHA-256: 15038143C95E4BA8A8A072602288563895D80AA918F5F810CE7596B46E698AB5
candidate SHA-256: 9B5ADB428923A9A62B6D31D26BFFC89F4326EDACE7AA6F22A42AF7B30CCBECD9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

