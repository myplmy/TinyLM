# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:190204
original SHA-256: 5985CD0DDE0E9FAC5333757E1D227E4EEA2D9A0CE98072A66142AC24EB96C393
candidate SHA-256: 5985CD0DDE0E9FAC5333757E1D227E4EEA2D9A0CE98072A66142AC24EB96C393
원문 frame 패킷: [1, 28]
최종 full_diff 패킷: [55, 55]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 55]
후보 중복만 있는 생략 가능 패킷: [29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190204_0055.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:190251
original SHA-256: D565494233701D1C4E161C57384C61106DE5FA644C569DC1A7E23BECBAD49257
candidate SHA-256: D565494233701D1C4E161C57384C61106DE5FA644C569DC1A7E23BECBAD49257
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190251_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190251_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190251_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190251_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190251_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190251_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190251_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:190485
original SHA-256: DA177C1D4A25C3EAEA38E2A6CEE05BCB20BEC9F5BFE6BCC34A132CB028DAD083
candidate SHA-256: DA177C1D4A25C3EAEA38E2A6CEE05BCB20BEC9F5BFE6BCC34A132CB028DAD083
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190485_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190485_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190485_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:190730
original SHA-256: 8789381A6F0FD4E9AD29F5C60E2ABDB014D17A31E3CAF34F2698D9EA47F350FC
candidate SHA-256: 8789381A6F0FD4E9AD29F5C60E2ABDB014D17A31E3CAF34F2698D9EA47F350FC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190730_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190730_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:190926
original SHA-256: BC04EFE47F74D8651FE75533D7516C2B613D3A3AF9A743EED7BE67CC6254F44C
candidate SHA-256: 2485463B12926769F02AE254AE2AE55E081AA2E21F10B000D46F959725A9EA50
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

