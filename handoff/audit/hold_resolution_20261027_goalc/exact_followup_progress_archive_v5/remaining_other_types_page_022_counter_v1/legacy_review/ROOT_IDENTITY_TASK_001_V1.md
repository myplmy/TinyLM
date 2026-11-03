# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:243959
original SHA-256: 2D6B8BB5D0918CF57BCA6D8ABC39BDE279B3FECC1557E9EFE5118B77E9E09F0D
candidate SHA-256: 2D6B8BB5D0918CF57BCA6D8ABC39BDE279B3FECC1557E9EFE5118B77E9E09F0D
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243959_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243959_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243959_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:244030
original SHA-256: 22F45B0DB2A22FFEE8B3F2559FFFE448777FC1A7720C0704D09585DDB431CB4D
candidate SHA-256: 22F45B0DB2A22FFEE8B3F2559FFFE448777FC1A7720C0704D09585DDB431CB4D
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244030_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244030_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244030_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244030_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244030_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244030_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:244041
original SHA-256: 7A6C329A8788947364C31F936313462F64119063D51404F4770A71E33331B384
candidate SHA-256: C46CDE95103676173BFAE2A92DF51D55BBE13E1733F25EB680B38EA3F739A7C5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:244289
original SHA-256: 68489D9EB4616EA69EBE6ACAE4BF551B9C91FDD9E6FC8DC9E8850661A924F413
candidate SHA-256: 9FD2DCAFAAB6448B7AB77D13F4D25B0F269DD619AF7C39E6FA142995BB468F63
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:244311
original SHA-256: FC32E8903E8889C66CD75867BB896E1F19853A62C8D609A89171BE066D465650
candidate SHA-256: 4FE4CB6777778E1F9D351E7154FAF6503A507851E064370C16190AFDB590E597
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

