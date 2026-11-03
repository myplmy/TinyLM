# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:786139
original SHA-256: 46FE8AE70F6378EF617B46C690EC4A0630D3129116D0CA5B617AF1E254F1904F
candidate SHA-256: F23DCBB3DB2B97FF28C0869E83D459706E5B35F1D4D51C5E167181DBC4D299A6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:786333
original SHA-256: B141C80F549B8F1FCDE58F7AFD7CFBD37C6E014B73782A52219324488F256599
candidate SHA-256: B141C80F549B8F1FCDE58F7AFD7CFBD37C6E014B73782A52219324488F256599
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_025_counter_v1/reading_packets_v1/expanded_train_786333_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_025_counter_v1/reading_packets_v1/expanded_train_786333_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_025_counter_v1/reading_packets_v1/expanded_train_786333_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:786339
original SHA-256: 3965DC5AA052A30627EC8D8E0BB96196B89B512C99D79DAA371F5E802A191123
candidate SHA-256: 3965DC5AA052A30627EC8D8E0BB96196B89B512C99D79DAA371F5E802A191123
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_025_counter_v1/reading_packets_v1/expanded_train_786339_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_025_counter_v1/reading_packets_v1/expanded_train_786339_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_025_counter_v1/reading_packets_v1/expanded_train_786339_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:787377
original SHA-256: 28E1CEDAA29490268BF76E0BFABE3323DA1879CCBF13C6E6FD62D971C3E46FCA
candidate SHA-256: 28E1CEDAA29490268BF76E0BFABE3323DA1879CCBF13C6E6FD62D971C3E46FCA
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_025_counter_v1/reading_packets_v1/expanded_train_787377_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:788139
original SHA-256: 9D49FFDE09684414061A8C27235E061FB691C774CE952746FD327320F59234C1
candidate SHA-256: 9D49FFDE09684414061A8C27235E061FB691C774CE952746FD327320F59234C1
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_025_counter_v1/reading_packets_v1/expanded_train_788139_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

