# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1135
original SHA-256: E58905010D6DAE66D65548A7C4F16B2919937AFAAF46E3AB91C4C83E749BF662
candidate SHA-256: 74ED60E0F2CEA8C389DFEAF2E9E6F9301FF31A9705A49FDB562C138F35ECAEEE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1583
original SHA-256: E9380F8642A305EC54F2BC0DA2F0FF4F80CAAC5E7DF583AB1DC63141838BC267
candidate SHA-256: E9380F8642A305EC54F2BC0DA2F0FF4F80CAAC5E7DF583AB1DC63141838BC267
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1583_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1583_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1583_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1743
original SHA-256: 6AC3E5358A46045D599BB8403D0F099A01AC8C1A3990116EAF20FC0DA06CD7A6
candidate SHA-256: 0B73764FBD5E5DD5051397A808208DD01EEADF0455A05F54EF976143F45B9082
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1882
original SHA-256: 5DC9872D8940CB21A703D6A304423419EF8ABFC1BD3ADA6D5AD6DF66273EB511
candidate SHA-256: 5DC9872D8940CB21A703D6A304423419EF8ABFC1BD3ADA6D5AD6DF66273EB511
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [19, 19]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 19]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1882_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1882_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1882_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1882_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1882_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1882_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1882_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1882_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1882_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1882_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1882_0019.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1889
original SHA-256: 850FB8C2183D22F11A45AA7487F1F2F52C590E8EB87F85AB049583E745A8391C
candidate SHA-256: 1F80DF818F400517B918819B976C9CC454D024402D6BF691F71EB19FAC3F8D1B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

