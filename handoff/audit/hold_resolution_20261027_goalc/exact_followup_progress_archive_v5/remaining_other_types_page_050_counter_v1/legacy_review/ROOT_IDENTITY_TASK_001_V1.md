# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:636552
original SHA-256: 8321B1342AF4AF5FBBFDA3094CB4D1B87771BA28AAE8680F255A638B0B97EA59
candidate SHA-256: 8321B1342AF4AF5FBBFDA3094CB4D1B87771BA28AAE8680F255A638B0B97EA59
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636552_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636552_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636552_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636552_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636552_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636552_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:636664
original SHA-256: 6A0A96B574525E2C83B17E0E82526FD48AF8EAA45FE33B0DF29B109ECCD8F5F6
candidate SHA-256: BBB944381C8403AE09B8E723643FEA5DD3CA08079E2DB462CCDAA534CCEDDCB5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:636777
original SHA-256: 9BC0BBD3EB19BBF2CD9E144599C003CFB0A918343862B029233280EF6EF36392
candidate SHA-256: 9BC0BBD3EB19BBF2CD9E144599C003CFB0A918343862B029233280EF6EF36392
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [18, 18]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 18]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16, 17]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636777_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636777_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636777_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636777_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636777_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636777_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636777_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636777_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636777_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636777_0018.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:636930
original SHA-256: 7E6341F65E3BC4D196BE52301EB773213D510B4A849E8C6A66D081C8BCF2EF5F
candidate SHA-256: 487F7CB134ECE71E538E06DEBA34FA9CD8F65EAD121E8A78A4915C5CACBE8594
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:636974
original SHA-256: D2071C82DF9E1FF3FCE5AAD5CDEC1994681FC381F9EB8B6748A32F01E10DCC23
candidate SHA-256: D2071C82DF9E1FF3FCE5AAD5CDEC1994681FC381F9EB8B6748A32F01E10DCC23
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636974_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636974_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636974_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636974_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636974_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636974_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636974_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

