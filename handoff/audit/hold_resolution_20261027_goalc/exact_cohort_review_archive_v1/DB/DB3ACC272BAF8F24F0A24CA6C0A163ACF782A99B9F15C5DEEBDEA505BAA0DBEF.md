# 정확 입력 전문 판독 연결 TASK_003

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:2482
original SHA-256: B09D81A5F683368C343CF371A42F3092B5EEAB735E9285234D112DBF70CD4209
candidate SHA-256: 12AC5ECCA2C17F3AF33897CAC0CEE7159D30012C136CE543D95C070A35B8D8C3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:2702
original SHA-256: E77916DFF044CD054AD551AA8F7399B1C5EED13961D0CD24DBCF3B2736F75D30
candidate SHA-256: E77916DFF044CD054AD551AA8F7399B1C5EED13961D0CD24DBCF3B2736F75D30
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_2702_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_2702_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_2702_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:3237
original SHA-256: 6A738268A657B383615AB1416F824B93638AB17D2A14F81E8736B863FA8A8144
candidate SHA-256: 6A738268A657B383615AB1416F824B93638AB17D2A14F81E8736B863FA8A8144
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_3237_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:3279
original SHA-256: 2A13C46565B2B06B205138579272AA010605F65DC2BFB0149E785240E203C8F2
candidate SHA-256: 2A13C46565B2B06B205138579272AA010605F65DC2BFB0149E785240E203C8F2
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_3279_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_3279_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:334
original SHA-256: 2EE938EA057648AD79FFD9E59DBBD53B55343C4BDDC795FD1FD216E5E2921A04
candidate SHA-256: F89E0EC33D39158A6B9BF0231D5F31EA3DB5B9F0025B3DF1E73C368C421FA106
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

