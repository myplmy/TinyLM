# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1421524
original SHA-256: 6AFCF5B160473B162738E7FDB6328DC29EBC27C8189B243D0C7EFB550E5A64B4
candidate SHA-256: 6AFCF5B160473B162738E7FDB6328DC29EBC27C8189B243D0C7EFB550E5A64B4
원문 frame 패킷: [1, 11]
최종 full_diff 패킷: [22, 22]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 22]
후보 중복만 있는 생략 가능 패킷: [12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421524_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421524_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421524_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421524_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421524_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421524_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421524_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421524_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421524_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421524_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421524_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421524_0022.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1421807
original SHA-256: 8C6C12A51203751369E1B5E9F4FDF0F78376E69AA1442EEF6198FA19450A7402
candidate SHA-256: 8C6C12A51203751369E1B5E9F4FDF0F78376E69AA1442EEF6198FA19450A7402
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [17, 17]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 17]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421807_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421807_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421807_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421807_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421807_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421807_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421807_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421807_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421807_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421807_0017.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1422011
original SHA-256: 083C153386C807D588C94FF08D5BBD79D492C80F2B18B73DD8A05D52EBD75A29
candidate SHA-256: 083C153386C807D588C94FF08D5BBD79D492C80F2B18B73DD8A05D52EBD75A29
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422011_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422011_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422011_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422011_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422011_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1422022
original SHA-256: 0DFC4E6E93CCA2E0AE5A31C89FF523159F8984A566B3BAB60D179296F0D02F20
candidate SHA-256: 0DFC4E6E93CCA2E0AE5A31C89FF523159F8984A566B3BAB60D179296F0D02F20
원문 frame 패킷: [1, 14]
최종 full_diff 패킷: [27, 27]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 27]
후보 중복만 있는 생략 가능 패킷: [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422022_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422022_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422022_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422022_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422022_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422022_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422022_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422022_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422022_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422022_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422022_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422022_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422022_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422022_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422022_0027.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1422518
original SHA-256: 4A6AED646D32F4CA93471DB85E13E58830910048AFBA69A40BEA02AB77D5CDD4
candidate SHA-256: 4A6AED646D32F4CA93471DB85E13E58830910048AFBA69A40BEA02AB77D5CDD4
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422518_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422518_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422518_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

