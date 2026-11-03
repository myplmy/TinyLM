# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:963639
original SHA-256: 6F8132E6BF6F90DAFD7688D1D88194E510DCA1F3720937EB1E772449F9410FAB
candidate SHA-256: A6BC0CCE71908ED18F848F5C6269512BEFFD7BE61345E196DFFD600206AEB0E0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:963745
original SHA-256: 5B077D7A535A7928D8682687484CE113998E934C37C27C5E3DC7CB44971786CF
candidate SHA-256: 5B077D7A535A7928D8682687484CE113998E934C37C27C5E3DC7CB44971786CF
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963745_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963745_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963745_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963745_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:963861
original SHA-256: AA86B96DB62E899B2C4C25A4C0440A979B025DE8289DDE21B2919FEAC92B5543
candidate SHA-256: AA86B96DB62E899B2C4C25A4C0440A979B025DE8289DDE21B2919FEAC92B5543
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963861_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963861_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963861_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:964549
original SHA-256: 187241FF3CAD80598921BF65C8575D6682070D430B33B865456C8FDCB430EC45
candidate SHA-256: A71EB4AF03338B6FB26F4B3AB7D525AAB9373E4640FFB3558E7319168B94E3CD
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:964558
original SHA-256: 7800ED6D9A3B62729A23D6E68369AEA0C64DBB856929009CE3D8617822806276
candidate SHA-256: 7800ED6D9A3B62729A23D6E68369AEA0C64DBB856929009CE3D8617822806276
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964558_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964558_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964558_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964558_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

