# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1381708
original SHA-256: 8EDF05682E435EB84499EA75E6534DE7370A3787D9F1E0847F24DFA0C38DB72F
candidate SHA-256: 8EDF05682E435EB84499EA75E6534DE7370A3787D9F1E0847F24DFA0C38DB72F
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381708_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381708_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381708_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381708_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381708_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1381735
original SHA-256: 8E66E0D0C815223E861959CC96964410F352E5482B9D57BCA0658ACADEC3EB19
candidate SHA-256: 8E66E0D0C815223E861959CC96964410F352E5482B9D57BCA0658ACADEC3EB19
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6, 7]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381735_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381735_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381735_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381735_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381735_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1381898
original SHA-256: F8B903254DD15A531A53AEE3836127E376CA1C8B6F7A3E7B32D7290324B6B9B5
candidate SHA-256: F8B903254DD15A531A53AEE3836127E376CA1C8B6F7A3E7B32D7290324B6B9B5
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381898_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381898_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381898_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381898_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1382026
original SHA-256: 8C6247FA53C8CE033143AAC1D5A10EC079DCAEF96AF2400560D613DFD09E6AED
candidate SHA-256: 8C6247FA53C8CE033143AAC1D5A10EC079DCAEF96AF2400560D613DFD09E6AED
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 4, 5]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382026_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382026_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382026_0004.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382026_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1382046
original SHA-256: 778AE276A40F20D9DDFDD215AF5BD335AB38FCDC99CF5E026BD2E3C9C498B4A7
candidate SHA-256: 778AE276A40F20D9DDFDD215AF5BD335AB38FCDC99CF5E026BD2E3C9C498B4A7
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382046_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382046_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382046_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382046_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

