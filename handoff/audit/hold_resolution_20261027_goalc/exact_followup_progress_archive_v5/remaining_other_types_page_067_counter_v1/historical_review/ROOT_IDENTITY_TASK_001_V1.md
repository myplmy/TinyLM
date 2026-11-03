# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:880789
original SHA-256: 772E02CDC92F861AE4F1CC3F4E87D3A5AD4169A01866C569A2DE9730E8D43E38
candidate SHA-256: 772E02CDC92F861AE4F1CC3F4E87D3A5AD4169A01866C569A2DE9730E8D43E38
원문 frame 패킷: [1, 40]
최종 full_diff 패킷: [80, 80]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 80]
후보 중복만 있는 생략 가능 패킷: [41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0038.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0039.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0040.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880789_0080.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:880881
original SHA-256: 13A58475E3186A6B813F358CD5D6EDDF6A4EE4717315B3664D61548F70E93F12
candidate SHA-256: 520966677B483FBA010E1DECEF69EF897252AD5359D667B398981A213E0EB622
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:880934
original SHA-256: A807F5353AC5EA0F18FC86E8E75E2EAD1678026663C916BB2767F33585045DC7
candidate SHA-256: A807F5353AC5EA0F18FC86E8E75E2EAD1678026663C916BB2767F33585045DC7
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880934_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880934_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880934_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880934_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:881478
original SHA-256: 3BB6FD77BD46AFF2C53F10F0B8F3188D4C85CD1E064E6FF78885A47AEDC37C08
candidate SHA-256: E53416B48D5365746FA58A1DAE9216573F345592ADE90BF9D5588DE17060F393
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:881503
original SHA-256: 7DCE51BA24A556E396AC8ABBD774564B6BCF7146C65E5C427EDC0B4E699391FD
candidate SHA-256: 7DCE51BA24A556E396AC8ABBD774564B6BCF7146C65E5C427EDC0B4E699391FD
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881503_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881503_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881503_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

