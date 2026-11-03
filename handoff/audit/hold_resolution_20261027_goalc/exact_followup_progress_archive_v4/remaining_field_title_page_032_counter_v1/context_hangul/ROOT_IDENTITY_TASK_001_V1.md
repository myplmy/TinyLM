# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1145557
original SHA-256: A7901B1D372F374B95FAD7B7263AF4C57B0A58CB0DD0E2BC9D1463BCAE4F23E0
candidate SHA-256: E6B78A13204A21093A65A1666881B530E01267BF3689C91F779DC79626248715
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1145591
original SHA-256: E7C4BA6D12E408A7C83843BBC4CF987BAB95484DFE786AF0CD3E3126144E3D62
candidate SHA-256: E7C4BA6D12E408A7C83843BBC4CF987BAB95484DFE786AF0CD3E3126144E3D62
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1145591_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1145591_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1145591_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1145732
original SHA-256: 9AF5E1DE0B9DE67A7F8788ED215C4E3170BF0C54135F5F448AB529F0F51A0B37
candidate SHA-256: 9AF5E1DE0B9DE67A7F8788ED215C4E3170BF0C54135F5F448AB529F0F51A0B37
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1145732_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1146441
original SHA-256: FC5B85B89DDF6E1C3F29A69C58FA502FE8E9FAB011D5DF0335D8616BC9D74190
candidate SHA-256: FC5B85B89DDF6E1C3F29A69C58FA502FE8E9FAB011D5DF0335D8616BC9D74190
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1146441_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1146773
original SHA-256: 0EFCC14DA544AC9342A6E7CDDE467DD957F46ABBDA798A830A865E7A1B636957
candidate SHA-256: 00CC501B86386B5704B648CEE42FEDBD4C52B445B961A1715F55E336FEB1C05F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

