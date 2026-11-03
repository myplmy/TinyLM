# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:400874
original SHA-256: 7024FCBEEF3F16416BE2DDDA840CB84D9EFA85A117BCCF840795A955D828E735
candidate SHA-256: 7024FCBEEF3F16416BE2DDDA840CB84D9EFA85A117BCCF840795A955D828E735
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_400874_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_400874_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:400964
original SHA-256: D68464A879E22B1B396023299E0D524DD8637F455CC793A64F5F2B3DE1CCA1B3
candidate SHA-256: D68464A879E22B1B396023299E0D524DD8637F455CC793A64F5F2B3DE1CCA1B3
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_400964_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_400964_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_400964_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:401524
original SHA-256: BB30F2F9D17F957DCE1B502C2CE498628263C670442C1C7D5C5B0137F3215382
candidate SHA-256: BB30F2F9D17F957DCE1B502C2CE498628263C670442C1C7D5C5B0137F3215382
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_401524_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_401524_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_401524_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_401524_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:402442
original SHA-256: 721D664CE5E0A4582D95DA380A88A588F0A46045D6AAEDC4A090A757D401953A
candidate SHA-256: 721D664CE5E0A4582D95DA380A88A588F0A46045D6AAEDC4A090A757D401953A
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_402442_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_402442_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_402442_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_402442_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_402442_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:403203
original SHA-256: 8F68D21C79D6D0C1CFA1D6614B069A21B92E3EF5BF8AB74833E63FBE7AB76D70
candidate SHA-256: 8F68D21C79D6D0C1CFA1D6614B069A21B92E3EF5BF8AB74833E63FBE7AB76D70
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_403203_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_403203_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_403203_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

