# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:608055
original SHA-256: 930F1795A32DB8D048697604D22C3EFAD1917266E5DE815A437FB707E2EF4597
candidate SHA-256: 930F1795A32DB8D048697604D22C3EFAD1917266E5DE815A437FB707E2EF4597
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608055_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:608150
original SHA-256: 814093571EEDE3ABB7FC8935C3417DE6B1064D9CF6E2D42D1115ECFCEC38788C
candidate SHA-256: 5210EA70E3D846CE53A1CA1B4E5CE8715486DAA91B4E2CB2D82057285EB9ED38
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:608282
original SHA-256: 1F2BCA87CDC405E5C0FD37A469958513A94A36C44B6C876498ADA0D720DB764B
candidate SHA-256: 1F2BCA87CDC405E5C0FD37A469958513A94A36C44B6C876498ADA0D720DB764B
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608282_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608282_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608282_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608282_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608282_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:608663
original SHA-256: EC5D50DDEF9A5688B4D1094BD4B659F495D5E1D1548157415070D4110776F169
candidate SHA-256: D19D3EB46EACF84209E01D3E9CA8B7208924246E7F738A77A87CB9623D388815
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:608782
original SHA-256: 021E8BB4C096CC3881D8A1F19D9BB5E55238080DFA069C63BAEA9A193F290F2E
candidate SHA-256: 021E8BB4C096CC3881D8A1F19D9BB5E55238080DFA069C63BAEA9A193F290F2E
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608782_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608782_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608782_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608782_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

