# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:474411
original SHA-256: 6E39DFA7D2800AC99C5434C8E7CA8378715A7F2B17FB5DBAA26049C7E802F6F9
candidate SHA-256: 6E39DFA7D2800AC99C5434C8E7CA8378715A7F2B17FB5DBAA26049C7E802F6F9
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474411_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474411_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:474609
original SHA-256: 93660201803B951B303B2984644C1C50F96E6334B4AB0965BA4005B1C02F96FD
candidate SHA-256: 93660201803B951B303B2984644C1C50F96E6334B4AB0965BA4005B1C02F96FD
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474609_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:474758
original SHA-256: B80F338F7A5E3606C52E57CDBA87230899349F5336713A26D84D4F9542683338
candidate SHA-256: B80F338F7A5E3606C52E57CDBA87230899349F5336713A26D84D4F9542683338
원문 frame 패킷: [1, 15]
최종 full_diff 패킷: [29, 29]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 29]
후보 중복만 있는 생략 가능 패킷: [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474758_0029.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:474836
original SHA-256: 077CBDF61105BBCB0F9DE64862C63F9ECF3178E7F2884A6A7E8364275983B348
candidate SHA-256: 577C4261DAF996CBD7E61343BC4CE4EB3ABAAF6CAC37384582682630449F1592
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:475035
original SHA-256: 9FFC446058F67303626D52D067F01A53430717EADD7F6FB47B041394CA3E6087
candidate SHA-256: 9FFC446058F67303626D52D067F01A53430717EADD7F6FB47B041394CA3E6087
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_475035_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_475035_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_475035_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

