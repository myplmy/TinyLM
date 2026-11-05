# 정확 입력 전문 판독 연결 TASK_017

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:444026
original SHA-256: 71573EB0D998242EC07A01BA150CF53DF98572C6FD12651FCD5BAEDCB3E4D85E
candidate SHA-256: 71573EB0D998242EC07A01BA150CF53DF98572C6FD12651FCD5BAEDCB3E4D85E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444026_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:444028
original SHA-256: 0ECB3C5B699EF21DA72709C76550A69620F46DDB0DABD2F21BAF23D3E20E9A20
candidate SHA-256: 0ECB3C5B699EF21DA72709C76550A69620F46DDB0DABD2F21BAF23D3E20E9A20
원문 frame 패킷: [1, 17]
최종 full_diff 패킷: [34, 34]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 34]
후보 중복만 있는 생략 가능 패킷: [18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444028_0034.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:444192
original SHA-256: 7512F99942AD3C448F31C78D87A9DFEEBA10062C5FE146B8BBE4D71A2C15B4DF
candidate SHA-256: 7512F99942AD3C448F31C78D87A9DFEEBA10062C5FE146B8BBE4D71A2C15B4DF
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444192_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_444192_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:444202
original SHA-256: 5BA2045AC035972EDB62FAF863D5D420618E0FD1FB412EFD2F8559D4EFF70794
candidate SHA-256: 0B117500018258F401928CB4339D51E76EFE87A2FC042F1C229D25BC5D1821E7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:444332
original SHA-256: BF287E95D7CBED955E4E3DD447618EE12B4F1DEA021ABA766C4D9D000CEAB464
candidate SHA-256: 575F1993FA3A57E664845405BA47EE2BEDF7AA9A20ABF957C6A9BBE5EE532056
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

