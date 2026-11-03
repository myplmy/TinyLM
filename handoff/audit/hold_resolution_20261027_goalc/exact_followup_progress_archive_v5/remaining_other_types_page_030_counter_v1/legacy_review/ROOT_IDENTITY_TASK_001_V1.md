# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:344683
original SHA-256: F736F74FEC42979FD1A4A8F75EFA623117E75E0140AB3011FCCC56C57F038B7A
candidate SHA-256: F736F74FEC42979FD1A4A8F75EFA623117E75E0140AB3011FCCC56C57F038B7A
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344683_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344683_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344683_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344683_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344683_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344683_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:344725
original SHA-256: 761C444FB5366FC1D6C1A2AF431E107F555D6F594CDA1695BFCA68EC61C01AA1
candidate SHA-256: 761C444FB5366FC1D6C1A2AF431E107F555D6F594CDA1695BFCA68EC61C01AA1
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344725_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344725_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344725_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344725_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344725_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344725_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344725_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:344758
original SHA-256: 2869CBC12F2DD3BE584D89674889BD01BAD17BB78590FBADAC6A3A80CD31C76C
candidate SHA-256: 2869CBC12F2DD3BE584D89674889BD01BAD17BB78590FBADAC6A3A80CD31C76C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344758_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:344796
original SHA-256: A0CE5C5988063E9448C129FC99E479C495399152403FCB2B9231371BD1D62907
candidate SHA-256: 840D3450D252A66348F30067F0D099DFA58257065FACD982F08DC050DE76B342
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:345018
original SHA-256: AEBDF859881D79A78F740D672E8EF2B55E84E343D791634B20258666C9A9C087
candidate SHA-256: AEBDF859881D79A78F740D672E8EF2B55E84E343D791634B20258666C9A9C087
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_345018_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_345018_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_345018_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_345018_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

