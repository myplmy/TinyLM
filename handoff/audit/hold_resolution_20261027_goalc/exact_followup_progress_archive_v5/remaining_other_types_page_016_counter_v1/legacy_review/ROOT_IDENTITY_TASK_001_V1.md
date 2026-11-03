# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:161346
original SHA-256: 85C6A0FDC29E56EA64F91254C9EA219184B7E0999FDC61C71CCEF558339EB99C
candidate SHA-256: 85C6A0FDC29E56EA64F91254C9EA219184B7E0999FDC61C71CCEF558339EB99C
원문 frame 패킷: [1, 32]
최종 full_diff 패킷: [63, 63]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 63]
후보 중복만 있는 생략 가능 패킷: [33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161346_0063.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:161425
original SHA-256: 23C4BE1183D32D54D8F93448636E88A9628A5F20F37DA3C2C9938203428422C8
candidate SHA-256: 23C4BE1183D32D54D8F93448636E88A9628A5F20F37DA3C2C9938203428422C8
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161425_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161425_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161425_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161425_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161425_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:161594
original SHA-256: 337F17187FA21F029B2EFB06EE609132EEFCB52102D6586D4E5B6DB6B184BB8F
candidate SHA-256: E2FCE0027167B90694A9293E391AED4036CAD0C0CD10C2336E82417FBE41C0A8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:161614
original SHA-256: 685111B68412B40C36A63310DB39D1D7552480F9DBB8FE3DB65A72154A043C65
candidate SHA-256: B6DB55BA3CC67E2A9F48DB7C1FA34677FC488CE06850B830AA0006B4C3A17F66
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:162149
original SHA-256: 37F265F648C9A3592B22CCF5D8B5204CFE15C80BB38C37833D6D321AD3A02462
candidate SHA-256: 37F265F648C9A3592B22CCF5D8B5204CFE15C80BB38C37833D6D321AD3A02462
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_162149_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

