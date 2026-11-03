# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:350351
original SHA-256: 7167DBF86ABFB88552E6320792E92080CFDC7B5E9E8B7D1751F7078C4764EDA4
candidate SHA-256: 7167DBF86ABFB88552E6320792E92080CFDC7B5E9E8B7D1751F7078C4764EDA4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_015_packet_v1.py --source-id expanded_train:350351 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:350400
original SHA-256: 031AAEA1D7247D8BE02769A63CEE266DFC59F0B55958D322BAA2048A39CA7D99
candidate SHA-256: A0733FB836FD01DE5E88F99B28BED55327C2E59E876031A8C7C8600C369AD141
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:351019
original SHA-256: 0C11286A82FDE79489961406FDD8F74089E7C453E7E849EE2A3416E56DD7A1E6
candidate SHA-256: 9153F00526E0D62B1B060BD4232F5F9EDACCDEF32BE46DF4254A3A7440CF1EE7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:351215
original SHA-256: 714C0BFB94243673A5E291FB96B9D8338EF89737C7CF1113FA43D112A6930021
candidate SHA-256: 714C0BFB94243673A5E291FB96B9D8338EF89737C7CF1113FA43D112A6930021
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_015_packet_v1.py --source-id expanded_train:351215 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:351644
original SHA-256: 22D1E26CF9A6B3EEDE44CEC6642B27C6738CED1AC8BA7AD7F3742D9553B96661
candidate SHA-256: AE18FB5EAF7D29BDC756989121EE48A5D20346DFE500396537CDD9BB8BFEA27B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

