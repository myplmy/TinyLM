# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:401683
original SHA-256: FCA616E6ED7D9D896CF0AB13BE41356BE4E3E061AA18258577FC2A3B9A9A4AC9
candidate SHA-256: FCA616E6ED7D9D896CF0AB13BE41356BE4E3E061AA18258577FC2A3B9A9A4AC9
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_401683_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_401683_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_401683_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:404118
original SHA-256: 69A8F123F0291305F71CF36D98B48034D38CCD27959A23960C8EEC2BF0D8B6EB
candidate SHA-256: 058DE1183233B961332BBA54672223A3A30063D5A374951545F0D3FD53537FF2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:404324
original SHA-256: 510B4E635F9E37B0EF1A95B5E560098BE0D1301789DB6A49F0174E5D04D43B82
candidate SHA-256: 84E37DA1E4E063D57C67CB868F6BAAB1BA7FC3752F8A8E2EECC48AC4E016485C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:404732
original SHA-256: 8AEAAE74F256C39989615F717EF9A315CF338854DF9D1B15AC3A7DE68EAE2F03
candidate SHA-256: 8AEAAE74F256C39989615F717EF9A315CF338854DF9D1B15AC3A7DE68EAE2F03
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_404732_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_404732_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:404940
original SHA-256: 85795D66AE642754E9472EE8E2F50DA172DA9AF8A0E04330631B52A0C366F71F
candidate SHA-256: 85795D66AE642754E9472EE8E2F50DA172DA9AF8A0E04330631B52A0C366F71F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_404940_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_404940_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

