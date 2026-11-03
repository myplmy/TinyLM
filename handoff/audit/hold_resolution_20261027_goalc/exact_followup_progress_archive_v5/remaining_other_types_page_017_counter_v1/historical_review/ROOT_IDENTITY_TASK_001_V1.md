# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:174775
original SHA-256: 18D7E1F0085A311C442E960C9F6E3EB45288458DB2D5B49D1F61F188A122BB05
candidate SHA-256: 18D7E1F0085A311C442E960C9F6E3EB45288458DB2D5B49D1F61F188A122BB05
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_174775_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_174775_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_174775_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_174775_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:174847
original SHA-256: F6D6233E8D49EAED6322001B408E0119EE8B0A1D196842A01E41993D83FAA2F0
candidate SHA-256: 210D2E4777BB0BE81E10CEEA2ED4AFCFF20DF5E445BB235F95085EBD31E0DF28
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:174928
original SHA-256: 1D0B7BD248AAB22E4A019E493D583A955FE6E8CEA86B93E50E6DA84AF7D752A8
candidate SHA-256: DFA58574D423A98E8BB0BA12A33A6AA54260A73328D4AA5F0E21D7631A36F942
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:175156
original SHA-256: 5A70CA321945FB999175B266E3CEF33BE058C82D8D002092CD22016EB9F1B9E4
candidate SHA-256: 5A70CA321945FB999175B266E3CEF33BE058C82D8D002092CD22016EB9F1B9E4
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_175156_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_175156_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_175156_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_175156_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:175191
original SHA-256: EA2E99914B045C7A8BCDCBA701FDA01B2EA16B6B5D689EDC1749CF2C4BF3802E
candidate SHA-256: EA2E99914B045C7A8BCDCBA701FDA01B2EA16B6B5D689EDC1749CF2C4BF3802E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_175191_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_175191_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_017_counter_v1/reading_packets_v1/expanded_train_175191_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

