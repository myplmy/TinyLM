# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1000214
original SHA-256: D85BAE08ED093DFE37318DE5A5B6C34BB093529738636489F60DD42631CD29D8
candidate SHA-256: D85BAE08ED093DFE37318DE5A5B6C34BB093529738636489F60DD42631CD29D8
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000214_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000214_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000214_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1000396
original SHA-256: 63B58EEBFBB8C20B39195B217B234B850DCDF19B604959C54521D64125F9469C
candidate SHA-256: 63B58EEBFBB8C20B39195B217B234B850DCDF19B604959C54521D64125F9469C
원문 frame 패킷: [1, 21]
최종 full_diff 패킷: [41, 41]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 41]
후보 중복만 있는 생략 가능 패킷: [22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000396_0041.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1000696
original SHA-256: 80C83F4226F5753716B0507065F16133964937179E8AE2C98692E85A3C38B492
candidate SHA-256: 80C83F4226F5753716B0507065F16133964937179E8AE2C98692E85A3C38B492
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000696_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000696_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000696_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000696_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1000696_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1001249
original SHA-256: 49FC80EA558813D3793D3BF4940758F673888CC2593C2429DFBEBC7593187830
candidate SHA-256: 49FC80EA558813D3793D3BF4940758F673888CC2593C2429DFBEBC7593187830
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1001249_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1001249_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1001249_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_073_counter_v1/reading_packets_v1/expanded_train_1001249_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1001292
original SHA-256: 4EE51F907639823EB417DAEAB5D308FF3AD620FC1E65D9C38800F43C9C42E6F1
candidate SHA-256: 17E83324D9E81BA52E9CC7F9E9A736881B4FDA0B020064F7C84D9D4AF9F2AB5C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

