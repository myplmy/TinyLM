# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1131141
original SHA-256: 09ED8DF387C2F2C946F0E20B5380C53CACAD065236A3A8E316BE4A301407B053
candidate SHA-256: 7445E2076F595B272C63734905EAEA4CC72290132F730B5C7A6945D0DB67F48D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1131155
original SHA-256: E9E6765D3709AABA23A4326251D4F5FC6D82683568E86B6BB8B7E031DB47C77A
candidate SHA-256: E9E6765D3709AABA23A4326251D4F5FC6D82683568E86B6BB8B7E031DB47C77A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131155_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1131174
original SHA-256: D802C9668DCFCEE5533C9D18A7EF85BEB5871B0CA54E625370D36216A8612DE3
candidate SHA-256: D802C9668DCFCEE5533C9D18A7EF85BEB5871B0CA54E625370D36216A8612DE3
원문 frame 패킷: [1, 25]
최종 full_diff 패킷: [50, 50]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 50]
후보 중복만 있는 생략 가능 패킷: [26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131174_0050.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1131471
original SHA-256: 38B9CD4F114264CA440233B2730095579A500F8804BEA6C58DA0805227AE2236
candidate SHA-256: 75CE3B16BFCFBA25E2D4D459DADA9464748A9C13B8DE318512023312E7F0BC88
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1131719
original SHA-256: 554A04B525D64798813F01FA289CE15BE0B1EFCF216C72703269352818F74CF2
candidate SHA-256: CECAE47138CBB7FC73B41A1B7020927246FA36BB75AD3708A94A8A378FFB9A76
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

