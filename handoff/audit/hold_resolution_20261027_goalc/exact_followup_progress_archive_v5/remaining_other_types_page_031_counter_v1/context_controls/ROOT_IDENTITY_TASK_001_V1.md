# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:360036
original SHA-256: D0EB8DCAECD773B8C221C5BCBDF57EEAF73F28FE4B777880F1A6E931833F9E0D
candidate SHA-256: 50B528DED0FD6321C0CA03F63A3098A84D18E1BE9D41DDD5E62204331A376CED
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:360237
original SHA-256: 34A9D72C019C3974C5FB4452052E766E785030FE4EC0A8523B7B71745A87F319
candidate SHA-256: 8352B4C6CC9A68B5A9AFAFF757596487424B3D134D17621A3F5AB0B10F69DBCD
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:360294
original SHA-256: 800D091F69DCEF77D447AF4D4921C3D1B281A1DEDD20557C2F3CF0F519F278E3
candidate SHA-256: 800D091F69DCEF77D447AF4D4921C3D1B281A1DEDD20557C2F3CF0F519F278E3
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_031_packet_v1.py --source-id expanded_train:360294 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:360625
original SHA-256: 70A1297844A0E42E0057709A5BE82CC1902DE1BA2DE2D7A9EB7DD9A0E46064D3
candidate SHA-256: 065485D92097CE42FE50678526DA1E80713A8B01D1753FE0824F92DF9ABA514E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:361074
original SHA-256: 7306C2BB08E9451C233AAE22A6B47A6295D0FA64DBA4FC73D1CAB1E2962567C2
candidate SHA-256: 7306C2BB08E9451C233AAE22A6B47A6295D0FA64DBA4FC73D1CAB1E2962567C2
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5, 6]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_031_packet_v1.py --source-id expanded_train:361074 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_031_packet_v1.py --source-id expanded_train:361074 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_031_packet_v1.py --source-id expanded_train:361074 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_031_packet_v1.py --source-id expanded_train:361074 --packet 5 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_031_packet_v1.py --source-id expanded_train:361074 --packet 6 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

