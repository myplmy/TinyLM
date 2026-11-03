# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1202006
original SHA-256: 8EFDEE3D2B3B59E03E005E40AE872546C5E056FB1BD7490122C0078B38DD2512
candidate SHA-256: 8EFDEE3D2B3B59E03E005E40AE872546C5E056FB1BD7490122C0078B38DD2512
원문 frame 패킷: [1, 14]
최종 full_diff 패킷: [27, 27]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 27]
후보 중복만 있는 생략 가능 패킷: [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202006_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202006_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202006_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202006_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202006_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202006_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202006_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202006_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202006_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202006_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202006_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202006_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202006_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202006_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202006_0027.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1202080
original SHA-256: 33ADE91A451ED0F2A8A8100B0551A04D2FDDD8CD9A0A1F2BE092966DACFD4864
candidate SHA-256: 33ADE91A451ED0F2A8A8100B0551A04D2FDDD8CD9A0A1F2BE092966DACFD4864
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [15, 15]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 15]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202080_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202080_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202080_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202080_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202080_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202080_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202080_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202080_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202080_0015.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1202121
original SHA-256: B31D20D81B3AA9A58F546B077402490BF85872DAA2A93B270B4F3054640CE9C2
candidate SHA-256: B31D20D81B3AA9A58F546B077402490BF85872DAA2A93B270B4F3054640CE9C2
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202121_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1202164
original SHA-256: AEB385798B02DF8A57BC12278D465B08CD369E27E4A83EE08D854089FCFE78A0
candidate SHA-256: AEB385798B02DF8A57BC12278D465B08CD369E27E4A83EE08D854089FCFE78A0
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202164_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202164_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202164_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1202221
original SHA-256: F41C9757C161A14E99FB77D93ED5A18D83FF1ABFD401DF493CC6A6908C56C6BB
candidate SHA-256: F41C9757C161A14E99FB77D93ED5A18D83FF1ABFD401DF493CC6A6908C56C6BB
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202221_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202221_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202221_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202221_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202221_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202221_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

