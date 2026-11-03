# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1196889
original SHA-256: A39C5C0FCAB34E0A798170F15904A61563064F905F6AD633358BE08EA5955068
candidate SHA-256: A39C5C0FCAB34E0A798170F15904A61563064F905F6AD633358BE08EA5955068
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1196889_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1196889_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1196889_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1196889_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1196889_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1196889_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1196889_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1197762
original SHA-256: 20F853911413545D29A3E20754767D4E7130830344103D3DB489E69E1193D1DE
candidate SHA-256: 20F853911413545D29A3E20754767D4E7130830344103D3DB489E69E1193D1DE
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1197762_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1198354
original SHA-256: 1A499729F1A4AE4E193C238B80CA80B43555FC476EFD5F560AF6DED770734AA7
candidate SHA-256: 09C92257CAA499BE55EB508124331D9F1B2A13C106893B84FA4518C4DBD25A59
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1198517
original SHA-256: D7EB25D4D5147F946D240E2A49A624AD5859B6E08CA7A22B4212E700ED68259D
candidate SHA-256: 78D59DB6F995FB721F54CA9E24A350E05AA03074BA2D65A25D20C2CDE65B5063
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1198825
original SHA-256: 976A5355B707020845D16765C86DA96150D925E127F923A7E49871531530415D
candidate SHA-256: 976A5355B707020845D16765C86DA96150D925E127F923A7E49871531530415D
원문 frame 패킷: [1, 29]
최종 full_diff 패킷: [57, 57]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 57]
후보 중복만 있는 생략 가능 패킷: [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1198825_0057.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

