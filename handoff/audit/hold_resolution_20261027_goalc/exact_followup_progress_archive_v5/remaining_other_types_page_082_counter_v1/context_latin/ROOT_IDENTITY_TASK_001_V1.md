# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1131006
original SHA-256: 56ACCA9CE9637C72C78EFB72205C5369E617DA2CFC7CFD5B46804C8579E624DE
candidate SHA-256: 56ACCA9CE9637C72C78EFB72205C5369E617DA2CFC7CFD5B46804C8579E624DE
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131006_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131006_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131006_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131006_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131006_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1131681
original SHA-256: BFA1D57334104186ACA73432B0CAE025EA60F69CC4FB80615E8387D6604A0B6C
candidate SHA-256: 0C6C069A0927A02CDFCDC7E0E2D8AB302760FF0E20D390F4F9B82EAD0DF74D2A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1131882
original SHA-256: 6A4F73023EDDB11034C7C41726D88E53E5F45FDD86DFE074702DD5E8C3D58E79
candidate SHA-256: 6A4F73023EDDB11034C7C41726D88E53E5F45FDD86DFE074702DD5E8C3D58E79
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131882_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131882_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131882_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1131892
original SHA-256: D71E43AA3E325D8412FA69488099D8478D6D1731CD13A284F7190AC713F8A52A
candidate SHA-256: D71E43AA3E325D8412FA69488099D8478D6D1731CD13A284F7190AC713F8A52A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_082_counter_v1/reading_packets_v1/expanded_train_1131892_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1132034
original SHA-256: 78941EB83C0E802BD899D081D40D4CD3E07BA3FB149AA3B114BF2458119B900F
candidate SHA-256: 079FE41137DC44E6E7174CD3C2A0BB518655B85D9F15D2C505511DB093E940E6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

