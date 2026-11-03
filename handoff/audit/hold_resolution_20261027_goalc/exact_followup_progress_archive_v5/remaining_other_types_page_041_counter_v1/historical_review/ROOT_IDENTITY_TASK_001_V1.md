# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:501579
original SHA-256: D440139558C9A3B74AC4A6D0F85A39648A1517E16837A78C492299E6CCF4947E
candidate SHA-256: D440139558C9A3B74AC4A6D0F85A39648A1517E16837A78C492299E6CCF4947E
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501579_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501579_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501579_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501579_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:501820
original SHA-256: A5D7EC2BA6FB6624E6D08A0630048F545CEEA04AE5A23BE4D3F8C5DBA4BEC5E7
candidate SHA-256: 83D14390CFCBA2C5FE9EF81C99F6154399E3CB22B57140D432C19BFDB5F224B3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:501847
original SHA-256: 94A86CC389014640C47317D7F99AE65D9D946E43A86F5DA660535D79D89D9197
candidate SHA-256: 94A86CC389014640C47317D7F99AE65D9D946E43A86F5DA660535D79D89D9197
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501847_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501847_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501847_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501847_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501847_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501847_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:502095
original SHA-256: 11D66FE9EBFD318309ED62C0DF652832A857C566587C32027D33BD68790206BD
candidate SHA-256: 8B044B003A32332090D7B9FA1CBBDF055342B7605F5AC31056EA1D1496C1736E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:502303
original SHA-256: F6439249CC25519032BDE1DAB39875EF69727D195D4106B382E4EE6C4749B116
candidate SHA-256: 07651E16A89D3A4536BD2982FFD340052F825E1607FD6D7C5EDD8D19F3A3F99E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

