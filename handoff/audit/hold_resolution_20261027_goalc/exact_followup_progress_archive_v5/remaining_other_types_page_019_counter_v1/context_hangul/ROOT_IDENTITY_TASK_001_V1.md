# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:205146
original SHA-256: 51EB381E335B98E9BAC7E0E0CB5803F10C22126FF66742A39DBE374C9CA0BD62
candidate SHA-256: 64EAD3A8B79C1AF95347FEA9090193B256FAE9CF18C2D21DFF384B0E94B50D06
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:205326
original SHA-256: 502CBB2396805C98B08A095012C05F64F8193680AB16647DC538300329CD5949
candidate SHA-256: 502CBB2396805C98B08A095012C05F64F8193680AB16647DC538300329CD5949
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205326_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:205391
original SHA-256: DBD7DDDB2960B5D527331392A229271EA6B88E0AB56DC77FA2F9A935E7C92761
candidate SHA-256: DBD7DDDB2960B5D527331392A229271EA6B88E0AB56DC77FA2F9A935E7C92761
원문 frame 패킷: [1, 11]
최종 full_diff 패킷: [21, 21]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 21]
후보 중복만 있는 생략 가능 패킷: [12, 13, 14, 15, 16, 17, 18, 19, 20]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205391_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205391_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205391_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205391_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205391_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205391_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205391_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205391_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205391_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205391_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205391_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205391_0021.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:205404
original SHA-256: 4C1421BD9F83520D4E4C3B04CA182B030FC2F4FA1B0BDC186DF49A7B83824B6A
candidate SHA-256: 1E8CF5F0B442B5D67CFF1D3F249B001F5D016D7821C584D08960D90B0F60C494
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:205451
original SHA-256: ABD15FF303AAE3BB5676B6C7B96807DBAD1739CE994F0FECF4FFC3930F0005E4
candidate SHA-256: A4F4C57C021BA035D3F226A337C07418C8959228A53626B0945070D9EF5001A5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

