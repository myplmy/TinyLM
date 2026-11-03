# 정확 입력 전문 판독 연결 TASK_006

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:56154
original SHA-256: 6A7933C5F697402EA99B1BC0C03C3BD64311251FD38FE8746F5F48A70CFC5D3B
candidate SHA-256: 6A7933C5F697402EA99B1BC0C03C3BD64311251FD38FE8746F5F48A70CFC5D3B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_005_packet_v1.py --source-id expanded_train:56154 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:56455
original SHA-256: C33EB23A27F9121E0BA142D45CEEA79FD27D037B1689AC681F197EB7C23E4A12
candidate SHA-256: 0852D6C8707378BF7EF374EF54A4AD77930FC1BC2479712CC509259516F34474
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:57046
original SHA-256: DAC1819FBD972ABDF81B89A193F2231A4A937C7759DCEDEBB3377C807CA776B9
candidate SHA-256: DAC1819FBD972ABDF81B89A193F2231A4A937C7759DCEDEBB3377C807CA776B9
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_005_packet_v1.py --source-id expanded_train:57046 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:57995
original SHA-256: 8D3738DD11DF9450A41C29F8306EE60DE6B18F1D28A2CD0A4E8CBDDDDD64C720
candidate SHA-256: 8D3738DD11DF9450A41C29F8306EE60DE6B18F1D28A2CD0A4E8CBDDDDD64C720
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_005_packet_v1.py --source-id expanded_train:57995 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:57999
original SHA-256: A75F439F705F15984934BF41F2A2CC0279BEF1EF94B1CD8DE8F8F6CBED636209
candidate SHA-256: A75F439F705F15984934BF41F2A2CC0279BEF1EF94B1CD8DE8F8F6CBED636209
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_005_packet_v1.py --source-id expanded_train:57999 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_005_packet_v1.py --source-id expanded_train:57999 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_005_packet_v1.py --source-id expanded_train:57999 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_005_packet_v1.py --source-id expanded_train:57999 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_005_packet_v1.py --source-id expanded_train:57999 --packet 8 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

