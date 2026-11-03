# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1421161
original SHA-256: 43C5A69F41A5D5CA2C4FE22B2758FF32C0F119D7057E7F49DA3FE83E61BEB091
candidate SHA-256: 43C5A69F41A5D5CA2C4FE22B2758FF32C0F119D7057E7F49DA3FE83E61BEB091
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421161_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421161_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421161_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421161_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421161_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1421238
original SHA-256: F4CFF7D03074AE9E262FDBD90D68C41CAA9FA270A989F48F8DA32839D724FDBA
candidate SHA-256: F4CFF7D03074AE9E262FDBD90D68C41CAA9FA270A989F48F8DA32839D724FDBA
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421238_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421238_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421238_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421238_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421238_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1421657
original SHA-256: FA8EF2057020CDF67679175EBE7B7155F617C157030BF313D183BEAA70B0AC7E
candidate SHA-256: FA8EF2057020CDF67679175EBE7B7155F617C157030BF313D183BEAA70B0AC7E
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421657_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421657_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421657_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421657_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421657_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421657_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421657_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1421683
original SHA-256: EBDFCEE1512929E076B8DE3EE2F7C9394ED967B9F7B7CD6A92E3CD85E0548613
candidate SHA-256: EBDFCEE1512929E076B8DE3EE2F7C9394ED967B9F7B7CD6A92E3CD85E0548613
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421683_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421683_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421683_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1422221
original SHA-256: 29167D4CCDFB9414BE051375A5F24E1B125CF2CBC598FB29C8BED9EDDEBB40D9
candidate SHA-256: 29167D4CCDFB9414BE051375A5F24E1B125CF2CBC598FB29C8BED9EDDEBB40D9
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422221_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422221_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422221_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422221_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422221_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422221_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422221_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

