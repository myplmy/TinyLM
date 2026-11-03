# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:663660
original SHA-256: 2C51085310DF5AC04395F4E7BE7FBD6D2A1A77969136DEBD331E4D5C9F0FC3EF
candidate SHA-256: CFB9E7750426E739DFBE76A5BF8922154FBED275D726794AE819531B5C560BC9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:663815
original SHA-256: 5D2F82DA6A90E0878D1A4DDDD7AEF1F78EAA2103782D21BD816FA9A1097EB108
candidate SHA-256: 5D2F82DA6A90E0878D1A4DDDD7AEF1F78EAA2103782D21BD816FA9A1097EB108
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_663815_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_663815_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:664083
original SHA-256: 906F02B0A7EA333E5E7C5587273EF3D704C363FE10806F5178DD059BED99BCAF
candidate SHA-256: 906F02B0A7EA333E5E7C5587273EF3D704C363FE10806F5178DD059BED99BCAF
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664083_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664083_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664083_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:664674
original SHA-256: 1F51575CA653615442283E57C977DB8BAEB96DE830A7CDE9B73C211CA7AE71C3
candidate SHA-256: 1F51575CA653615442283E57C977DB8BAEB96DE830A7CDE9B73C211CA7AE71C3
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664674_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664674_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664674_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:664851
original SHA-256: 956CDA7ACBB48D12FEC00C6E66BD5E279D91CBCC3717E7074F0ADA52C78D2698
candidate SHA-256: 956CDA7ACBB48D12FEC00C6E66BD5E279D91CBCC3717E7074F0ADA52C78D2698
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664851_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664851_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

