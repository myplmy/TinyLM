# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:61963
original SHA-256: 7704A7E23A16D067CA56D3FF80D4396A394986EAD35F8F9C3756DE7FB7F676FD
candidate SHA-256: 7704A7E23A16D067CA56D3FF80D4396A394986EAD35F8F9C3756DE7FB7F676FD
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_61963_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:62072
original SHA-256: F89EB90A19F7D386A4C7A38CF509950550D1953010D40698B6778360DA4D8F99
candidate SHA-256: BF5923AD54A18430400D13FB1E86E364CD0C9C194AA775CAC1C97E0A5941E215
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:62110
original SHA-256: 2A5F5A2CD6ECDCB89BCEE6205C23F1F696C74712318150D474854D3DA2332BDF
candidate SHA-256: 2A5F5A2CD6ECDCB89BCEE6205C23F1F696C74712318150D474854D3DA2332BDF
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62110_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62110_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:62213
original SHA-256: 26BB57A40CA65EFA4A1E0490EBF10607D9ED302EA76DB767CABBD14DE91B790F
candidate SHA-256: 26BB57A40CA65EFA4A1E0490EBF10607D9ED302EA76DB767CABBD14DE91B790F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62213_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62213_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:62285
original SHA-256: B4B35978E4D412A5DF8501232F5667AD13902ADA4200010B1D0BDD2519E15FB6
candidate SHA-256: 93A9F14AD8297364B199EC9B48B8288586828F0982D8F3E45808B43C382CC649
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

