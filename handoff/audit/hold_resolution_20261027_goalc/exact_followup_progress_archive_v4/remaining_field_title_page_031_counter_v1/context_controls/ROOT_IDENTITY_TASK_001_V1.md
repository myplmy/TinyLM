# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1079197
original SHA-256: B21DFEAE467AB8554A092055D9C33B9E90FD9CD38EABE32F2103237790A10DC7
candidate SHA-256: B21DFEAE467AB8554A092055D9C33B9E90FD9CD38EABE32F2103237790A10DC7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_031_packet_v1.py --source-id expanded_train:1079197 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1079282
original SHA-256: 4F8BAB2C63C8400ED0F1664D7F496A11991E47F6723CD587DDDE1B92E7FC1566
candidate SHA-256: 01E27A2C848F00610FDA9736B25169B9F6A599615C99755476E0AEF59AEC41CF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1079669
original SHA-256: 85C3D453B9C099DEAA3446E2381CE2B8EC03D1D550AC67FCCC2A40F828117FB3
candidate SHA-256: 85C3D453B9C099DEAA3446E2381CE2B8EC03D1D550AC67FCCC2A40F828117FB3
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_031_packet_v1.py --source-id expanded_train:1079669 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1079857
original SHA-256: CA023E26813C75D2AA6667F95DE89739C3CEC563951E25EABE7C738725A94A9C
candidate SHA-256: D555CAB9C232DFB6E5C359F5BE64B620FF8238AEE130C90FD1E46AB5325F3419
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1080915
original SHA-256: 8DE5AFF999FA262E9DC848A66BB1944E943BEECB345AF6A679DD7D08ED019269
candidate SHA-256: 87DF3A4EAD9E5AA1F205107FFED34228BBADB8234E23C5A51603BFFFB6D1F6AB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

