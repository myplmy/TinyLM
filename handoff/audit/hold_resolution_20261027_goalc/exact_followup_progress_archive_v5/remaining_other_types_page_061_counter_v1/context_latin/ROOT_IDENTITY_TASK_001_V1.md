# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:792301
original SHA-256: C6308AF847AA6030C563542926CDB491287C43A391BC28D704D416442BD14897
candidate SHA-256: 52A798F87483D15C4AC37BBD101FA1AD2CB18BA9855597AF7758AB871D31F881
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:792310
original SHA-256: 9CCFB3953A725194CBD5C596F306E289994AEBFBCF1B8862CD93457DCF44FB91
candidate SHA-256: 9CCFB3953A725194CBD5C596F306E289994AEBFBCF1B8862CD93457DCF44FB91
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792310_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792310_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792310_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:792323
original SHA-256: 5F2A00BC01C6A3F581F178C6943ECC1C4F19A5140A426C293456E3F63E7D63AC
candidate SHA-256: 341C85DBD6681AD8BD027803116BC2B3BFE92C9E7FAD66454C262443B4D850F0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:792380
original SHA-256: 8EC0EF113458D6FFAA8D15786BFC86761550E0BB422A7A06C5F3C0501BC38B9B
candidate SHA-256: 8EC0EF113458D6FFAA8D15786BFC86761550E0BB422A7A06C5F3C0501BC38B9B
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792380_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792380_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792380_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792380_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792380_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:792435
original SHA-256: A67C61990F0F0A609061D1A5059E731BEB9AF1A0B1062117EFC419CEC9D0773C
candidate SHA-256: A67C61990F0F0A609061D1A5059E731BEB9AF1A0B1062117EFC419CEC9D0773C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792435_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

