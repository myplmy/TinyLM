# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:126841
original SHA-256: EC1FAA06264C88DFFCEEE5036601CFBFF966705B8E139EB22D8997C3EB7FBB0F
candidate SHA-256: 0B1DF34113E4065ECB4B2F3E20446296F3F8DC6D9CF4A919BEA0BCF2AC2CA7C4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:126865
original SHA-256: 44EABC2083E64900FB4EDF130573092C162B3F332C87D9931242FFFEF643F765
candidate SHA-256: 44EABC2083E64900FB4EDF130573092C162B3F332C87D9931242FFFEF643F765
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126865_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:126930
original SHA-256: 47D8DF65C1BDD19517F9281250B4C171700611F4D8F23164E100C33DC3DEEEA2
candidate SHA-256: 47D8DF65C1BDD19517F9281250B4C171700611F4D8F23164E100C33DC3DEEEA2
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126930_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126930_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126930_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:126975
original SHA-256: 94E225226E6CB33AA143CFD7F3EB35D06483BFC0F7BEF584FD6CE3164A188F53
candidate SHA-256: 5AF989B2E48FC71E4450B86B6F7548C84E2EA0DFA74E25E897BF569AA5EFD778
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:127027
original SHA-256: 543A8C84CA08B85484569CE42A26BE973DECDF3DA8FD0513718A78988739B601
candidate SHA-256: 543A8C84CA08B85484569CE42A26BE973DECDF3DA8FD0513718A78988739B601
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127027_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127027_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127027_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127027_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

