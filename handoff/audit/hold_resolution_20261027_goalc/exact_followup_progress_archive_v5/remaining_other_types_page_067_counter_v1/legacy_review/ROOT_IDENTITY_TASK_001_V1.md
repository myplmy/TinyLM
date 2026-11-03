# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:880784
original SHA-256: 5D770E549F54C5AC87016403B6086CB0E963DD24EDDEF29117CB3A3C168B07EB
candidate SHA-256: 5D770E549F54C5AC87016403B6086CB0E963DD24EDDEF29117CB3A3C168B07EB
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880784_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880784_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880784_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880784_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880784_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880784_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880784_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:880851
original SHA-256: 549EE92166740DF06AABFD715B5A63075EB976DAB66280D9C9F76B0F545A8785
candidate SHA-256: A111B78DD673E8EEC4DBBD87454954A9E91C527AF1AD721EA41673A28D8FC582
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:880862
original SHA-256: 3BE0B442D30EEF1F6F3C5EE2C0B1AFEC6857453DC4F208CF9FB3D2062F3A194A
candidate SHA-256: E86ADF7EFC95A74370BB51D8C61CB1B55ABCB41FA29BE8D88A6B6A84551AAD90
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:880977
original SHA-256: 831694B1840A61C768DED1D7C5C2BA5F6FA01917E21A89FD617591FDA30EA35D
candidate SHA-256: 831694B1840A61C768DED1D7C5C2BA5F6FA01917E21A89FD617591FDA30EA35D
원문 frame 패킷: [1, 22]
최종 full_diff 패킷: [44, 44]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 44]
후보 중복만 있는 생략 가능 패킷: [23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880977_0044.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:881103
original SHA-256: 1D9D4BD987B16DE010D6E6C84607AC50D5A0CA3745B354C89CBFD1DCD19D4568
candidate SHA-256: 1D9D4BD987B16DE010D6E6C84607AC50D5A0CA3745B354C89CBFD1DCD19D4568
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881103_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881103_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881103_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881103_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

