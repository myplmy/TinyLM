# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:149559
original SHA-256: 5F9ED6014BB1B6EF8472912F47CBC759EBF287F3DC406A09B7C01D40EFC099D1
candidate SHA-256: 5F9ED6014BB1B6EF8472912F47CBC759EBF287F3DC406A09B7C01D40EFC099D1
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149559_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149559_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149559_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:149626
original SHA-256: FDAE634C91DFD42014A9E4F3530C1F513FF34A55FB52C97AE73D30B2F1002B16
candidate SHA-256: FDAE634C91DFD42014A9E4F3530C1F513FF34A55FB52C97AE73D30B2F1002B16
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149626_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149626_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149626_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:149657
original SHA-256: F115E1D8257FEEC1A28623B72EA6EE25FC42A95C945B199C49990EFD37EC0048
candidate SHA-256: 9D66BFFA705A105B40521DC1ADF80F2A19C30EB47F71555A0151C4F21937FAF2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:149803
original SHA-256: 88036FD7B91C84487E38537FB9F780E348F04526BFD6D96782C3CCBCBAD2D403
candidate SHA-256: 88036FD7B91C84487E38537FB9F780E348F04526BFD6D96782C3CCBCBAD2D403
원문 frame 패킷: [1, 40]
최종 full_diff 패킷: [79, 79]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 79]
후보 중복만 있는 생략 가능 패킷: [41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0038.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0039.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0040.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_149803_0079.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:150671
original SHA-256: 1414FDBCC23021880F3F0E423D7B197E64CC8011D18309A9754B8C39EC51323A
candidate SHA-256: ECD58D4EF63633F04471C5F8EB5642A329E4360B3F6D5B545FA731DB749C3C50
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

