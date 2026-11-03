# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:205239
original SHA-256: 6CE311E59AE142C1A323393D7EF7164EB74D46A398B2A4B36E2C11C776EC0F86
candidate SHA-256: 28F62248552D63C47BDB1CD71F4B9C8BD5F2B526CD9A82D06D421D9C9010C24C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:205246
original SHA-256: 433E74048E76D0C4A54C3C5A4AF929ABC63F1584690E643B4AD944B82B381D50
candidate SHA-256: 433E74048E76D0C4A54C3C5A4AF929ABC63F1584690E643B4AD944B82B381D50
원문 frame 패킷: [1, 24]
최종 full_diff 패킷: [48, 48]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 48]
후보 중복만 있는 생략 가능 패킷: [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205246_0048.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:205274
original SHA-256: 6B7E7DC6872E85AC736D0F708F62CB22C69BB04D03D67CF1B6EEABCA6AA7F07D
candidate SHA-256: 6B7E7DC6872E85AC736D0F708F62CB22C69BB04D03D67CF1B6EEABCA6AA7F07D
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205274_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205274_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:205402
original SHA-256: B17D408F11193A6864E2509E1D9733AC8116561D7D920C46FD1C961EC1040B3B
candidate SHA-256: 00303F0975A68F9E8BE6A7E8E5E740848C87B33DD5B2AAA077987F5BECC6C85D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:205429
original SHA-256: FD4EDB5CEEE2211CC9D728A2B6B2103F74F92248399E92310A2B84480F714426
candidate SHA-256: 7010B307E27CD6425B9B14EB929383C7340C110220992A9B96967C3D2C9F94DA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

