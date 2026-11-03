# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:830608
original SHA-256: A68380AE0F942394CFB31F450DBE9D47C43C71C2D39730BB68F16F4B518B4AF7
candidate SHA-256: A68380AE0F942394CFB31F450DBE9D47C43C71C2D39730BB68F16F4B518B4AF7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830608_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:831006
original SHA-256: 472C50443D603A910E41AD726718636C2F444305048DFCE786225A767FAEAD4C
candidate SHA-256: 472C50443D603A910E41AD726718636C2F444305048DFCE786225A767FAEAD4C
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [16, 16]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 16]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14, 15]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831006_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831006_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831006_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831006_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831006_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831006_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831006_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831006_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831006_0016.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:831609
original SHA-256: 6898D511A65278D4C05CCCBD8D5D0B41229C40DCEF610FD1427B9F07323E237C
candidate SHA-256: 6898D511A65278D4C05CCCBD8D5D0B41229C40DCEF610FD1427B9F07323E237C
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831609_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831609_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831609_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831609_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831609_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:832195
original SHA-256: 6BD7C23DC4F15A8F18CBB22D175CCC402887AAD811057FC00487720088B395B5
candidate SHA-256: D1407F67424F261FCDFEFD3902FE05A3C51EED2CE812734F74ED52746B680674
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:832239
original SHA-256: A83CEE42C4848481B5B82983516A92A4F84CADF0CD50BB8691871A0EB482C906
candidate SHA-256: A83CEE42C4848481B5B82983516A92A4F84CADF0CD50BB8691871A0EB482C906
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_832239_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

