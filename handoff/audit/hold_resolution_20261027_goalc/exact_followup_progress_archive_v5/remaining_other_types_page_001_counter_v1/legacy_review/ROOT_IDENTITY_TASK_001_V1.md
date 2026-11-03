# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:135
original SHA-256: 5ED89165304AD9770120DF764005858E4CE9ECEE8DFD6F207C5E6F4848C56174
candidate SHA-256: A46D66EAA1B64CBFFB1788393A448371C9AD016911570FF77A8A8BBDBABAD01F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1475
original SHA-256: CBED185630B2853AD77526D226D4F345863EACE63A66A811112D7EA22B080E3D
candidate SHA-256: CBED185630B2853AD77526D226D4F345863EACE63A66A811112D7EA22B080E3D
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1475_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1475_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1475_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1475_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1475_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1475_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1475_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1802
original SHA-256: 68A06AFFDA7F4488297A5490F05510AA12860A8E51E5406E4B18C7A753F3DFD1
candidate SHA-256: 68A06AFFDA7F4488297A5490F05510AA12860A8E51E5406E4B18C7A753F3DFD1
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1802_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1802_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1802_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1802_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1802_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_001_counter_v1/reading_packets_v1/expanded_train_1802_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1830
original SHA-256: 29E6FF228A73858FBA6142A0D4596A463A09F711E48E07DF2A8194541708EFE3
candidate SHA-256: 23214BA18A59E6B4C49B23C86B419BCA9E882F213994E2B251BB86FA844FFAB7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:2168
original SHA-256: 2B7F1EB171526E62D8CF88050BCA16D3F1194AF2D5FA121C1F8C27AE8B64073A
candidate SHA-256: 70632C84FA495EF78CBF368B4867CAAF8A0BDC944ADEA0C88FFB876FA002293C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

