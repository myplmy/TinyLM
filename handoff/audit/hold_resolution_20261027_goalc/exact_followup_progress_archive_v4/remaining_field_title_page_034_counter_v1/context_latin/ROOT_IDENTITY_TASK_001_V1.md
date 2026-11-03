# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1247174
original SHA-256: 3DB6C3719D581858F5717BFA7CDA996845A54B06C3C38E680938B5B119D83FFE
candidate SHA-256: F08BFD775BBC109A5735DE149B5D15B4C49FDE15DEF194C5FC7FC25BDEC4DA9E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1247193
original SHA-256: 344F6D471E3A301E751C08BD2B3B193A213D5DDEF8DD4172BEBA551A17EC772A
candidate SHA-256: 7157A821C137CF09D76AD01814BD8A1F98A6761522218AC3ECF69C90AAD79FAB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1247930
original SHA-256: 5932D0C3937947C0F408B778B0CF61CD58F0834C7871F4760471ECB63E6EAE8E
candidate SHA-256: 5932D0C3937947C0F408B778B0CF61CD58F0834C7871F4760471ECB63E6EAE8E
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1247930_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1247930_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1247930_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1247930_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1247930_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1247930_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1247930_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1248056
original SHA-256: 3544AE5ADDAA4E9E6220C8AAA98A8459D215AF325274AAA9E72767948BCF99E1
candidate SHA-256: 3544AE5ADDAA4E9E6220C8AAA98A8459D215AF325274AAA9E72767948BCF99E1
원문 frame 패킷: [1, 24]
최종 full_diff 패킷: [47, 48]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 47, 48]
후보 중복만 있는 생략 가능 패킷: [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0047.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248056_0048.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1248203
original SHA-256: B99ED2838B59B8AF0CCEEBC9427670691EE05E5F4ECE5F44D1FC399CB4003A7F
candidate SHA-256: B99ED2838B59B8AF0CCEEBC9427670691EE05E5F4ECE5F44D1FC399CB4003A7F
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248203_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248203_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248203_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_034_counter_v1/reading_packets_v1/expanded_train_1248203_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

