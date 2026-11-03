# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:912442
original SHA-256: C6E696D5AE5A41970051993C7697A4B49EBB5A24AA696E3949489C65C46502EE
candidate SHA-256: C6E696D5AE5A41970051993C7697A4B49EBB5A24AA696E3949489C65C46502EE
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912442_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912442_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912442_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912442_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912442_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912442_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912442_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:912505
original SHA-256: 61E829B755DB456CEA4628C84FA43BEAF4BB58D543C9E90BD109E22424F92DF0
candidate SHA-256: 61E829B755DB456CEA4628C84FA43BEAF4BB58D543C9E90BD109E22424F92DF0
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912505_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912505_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912505_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912505_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912505_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:912970
original SHA-256: B682C806401EE4C85BD0C25CA60B688F56C1226DD6BAAD65622205FEDB543EA0
candidate SHA-256: B682C806401EE4C85BD0C25CA60B688F56C1226DD6BAAD65622205FEDB543EA0
원문 frame 패킷: [1, 23]
최종 full_diff 패킷: [45, 45]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 45]
후보 중복만 있는 생략 가능 패킷: [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912970_0045.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:913345
original SHA-256: F133812F35E017A774632B205BBF2B4A5DF60E6350B5D2C4C3448E9787CD74F2
candidate SHA-256: C46EB6EAB6243B70336334AC8963C6CDE98894F8E645966C6424EB52AD08CEDB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:913811
original SHA-256: F9E51BD07586D71E545F1E63852C498E396D3FBC60206AD643F29332C3EFF353
candidate SHA-256: F9E51BD07586D71E545F1E63852C498E396D3FBC60206AD643F29332C3EFF353
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913811_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

