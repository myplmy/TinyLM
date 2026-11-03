# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1145124
original SHA-256: 948AFDCEFECCABAB83927E9FAF1D7B9FDC140001B4F5617849E991EC93FB1BB9
candidate SHA-256: 9C9EFE5599D432FC70C17F83414F7D049962DF472E72E8C7E65A96CE29A70922
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1145518
original SHA-256: 6D83E63341201B6500DDF50EA6BBEAC1FF454BF49A791BC3DD4986FBAE34C3B2
candidate SHA-256: B4F93702C3621A09F288E0B84CDC6D715C415BC576AB7D355B49FE7850144D51
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1145861
original SHA-256: F3B921D7A1E07ACAD9FF939ED41B88ECA454140AE6C260FA1C28495A4D88DFAD
candidate SHA-256: F3B921D7A1E07ACAD9FF939ED41B88ECA454140AE6C260FA1C28495A4D88DFAD
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1145861_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1145861_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1145861_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1145861_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1146058
original SHA-256: 4842220EEC7451EEB801D22D2E93D26435A4761DADFF8360B8621CB33E4F86F7
candidate SHA-256: 4842220EEC7451EEB801D22D2E93D26435A4761DADFF8360B8621CB33E4F86F7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1146058_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1146488
original SHA-256: DDF79FD1027DC28B4F2AEF172AEE457A0E31F96352435B579587D7E85A307F7B
candidate SHA-256: DDF79FD1027DC28B4F2AEF172AEE457A0E31F96352435B579587D7E85A307F7B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1146488_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

