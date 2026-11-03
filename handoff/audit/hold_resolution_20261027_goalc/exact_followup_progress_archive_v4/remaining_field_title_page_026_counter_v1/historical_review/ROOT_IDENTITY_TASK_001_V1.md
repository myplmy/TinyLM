# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:829647
original SHA-256: CECFA0B69208FFBE17891EACD32EEDC3F892F255E01409F17082CEA440142A82
candidate SHA-256: CECFA0B69208FFBE17891EACD32EEDC3F892F255E01409F17082CEA440142A82
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_829647_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_829647_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_829647_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_829647_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:830135
original SHA-256: EAD2BF79199A96692738A1E3E20594F8ACDAE360A4F34AF6C6C11A4BFB37646E
candidate SHA-256: 42653D9743AE93A23A4025C6CE336D1012B2D03C7E96B64F5D97AE13B2947509
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:830182
original SHA-256: 5EE1E256FDEDD1A07E8CC1C558FD0BEE4BE6366E53627B74D2E96A42D50B94BF
candidate SHA-256: 5EE1E256FDEDD1A07E8CC1C558FD0BEE4BE6366E53627B74D2E96A42D50B94BF
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830182_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:830652
original SHA-256: 33FBAA52EE5E9170F48033F6AF069E360780BAC066ABE3F0E36AC10D47993DA1
candidate SHA-256: AADE0A4AFF43B9320230EF39AAAF22C2846F220DF407AB7143BE9B8B4B3C73EE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:831118
original SHA-256: 770005435FFB601477A81243F0A33E17F7582FD462F3F0B46B3978996256506E
candidate SHA-256: 770005435FFB601477A81243F0A33E17F7582FD462F3F0B46B3978996256506E
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [15, 15]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 15]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831118_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831118_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831118_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831118_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831118_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831118_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831118_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831118_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831118_0015.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

