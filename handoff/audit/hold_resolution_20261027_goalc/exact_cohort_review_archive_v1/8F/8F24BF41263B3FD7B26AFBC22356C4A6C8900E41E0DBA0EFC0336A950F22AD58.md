# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:149820
original SHA-256: 577BC1768679066976370E38B133DBEACA46A84E84ACDAA09B25541C6FBA8376
candidate SHA-256: 467AACDDEE68AE18C4AACC96EC3EFCD6FA4FAD2868B51DED46FD9449C86551D8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:150095
original SHA-256: 8285D2C897A9FDC282C74B219D87193B3886D0841D63E94575ED93637245114C
candidate SHA-256: 8285D2C897A9FDC282C74B219D87193B3886D0841D63E94575ED93637245114C
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_009_packet_v1.py --source-id expanded_train:150095 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_009_packet_v1.py --source-id expanded_train:150095 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_009_packet_v1.py --source-id expanded_train:150095 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_009_packet_v1.py --source-id expanded_train:150095 --packet 5 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:150248
original SHA-256: E74983A908C59D5673A84DD6FA26C904B58C590EEF945CE82800D8E35D5AC224
candidate SHA-256: E74983A908C59D5673A84DD6FA26C904B58C590EEF945CE82800D8E35D5AC224
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_009_packet_v1.py --source-id expanded_train:150248 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:150557
original SHA-256: 4FDA3D58CE82F263A48747916576186233CB0594BFCD2BC9CED246ABEEF5D379
candidate SHA-256: 18EE1485D95EAA59587A09A3FBA355BAC91285B31C79E7218FC3293371CD5D11
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:151305
original SHA-256: 9726DB6E9035C575E8807F96D29114A82AB4BE59CDF79DF254DBA61D678AC9A1
candidate SHA-256: 94A658FF34055E85AE9471BB7BD073DE8A081C4CAE74D89DC21121DB99FC55AF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

