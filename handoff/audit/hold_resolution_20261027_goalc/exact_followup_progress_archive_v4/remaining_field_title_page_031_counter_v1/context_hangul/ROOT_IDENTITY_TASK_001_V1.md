# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1079731
original SHA-256: A7DC3582AF4F8053A9A1E81E944626AD62C265D499220D4D7DB8B5DE4A4D68A4
candidate SHA-256: F79C1F1F9980A60153B1E3EE8246DD063E6131E46F1764EC18504C3AA1552CB8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1079743
original SHA-256: CCD308DB6D8570CE5E618A994B9D459D8039C967C5FD83877E57552D16D586C4
candidate SHA-256: CCD308DB6D8570CE5E618A994B9D459D8039C967C5FD83877E57552D16D586C4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079743_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1079755
original SHA-256: 599AC16D3CFED9DF1DA31D867FB0B4B41DA9F732A9EB8C287F4CF7F9860E56C9
candidate SHA-256: 4881FD5CEB9701127741546FD41859428234C97FBD478FABB06BD9F41078C909
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1079859
original SHA-256: 561D7C60DD08B43EABF12DFA62A02A01FCCB0A082FDF6DE3B03329B321BCF1C7
candidate SHA-256: 561D7C60DD08B43EABF12DFA62A02A01FCCB0A082FDF6DE3B03329B321BCF1C7
원문 frame 패킷: [1, 21]
최종 full_diff 패킷: [42, 43]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 42, 43]
후보 중복만 있는 생략 가능 패킷: [22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0042.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1079859_0043.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1079880
original SHA-256: 4A703B4E3C31B77212C5CFA38A39211329751FD872B5C79DDE3C9A5F294DD98D
candidate SHA-256: 39D36F6B9027B90A14AEA0D5844152F0909DEFEB3FC7290FDAE0149031B0C6C6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

