# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:61964
original SHA-256: 5573807B1B7AAEA1D907372E94DC3A907546A5C01649014C84A4BD7337B47AE4
candidate SHA-256: 5573807B1B7AAEA1D907372E94DC3A907546A5C01649014C84A4BD7337B47AE4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_007_packet_v1.py --source-id expanded_train:61964 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:61969
original SHA-256: 3AF56526240EF0321D69BC3009C1BF24695A8216640E1E8BEA6B0359593ECE9B
candidate SHA-256: 3AF56526240EF0321D69BC3009C1BF24695A8216640E1E8BEA6B0359593ECE9B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_007_packet_v1.py --source-id expanded_train:61969 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:61970
original SHA-256: E4DCC14C4BEDE9DB6B8C3055BBAFCBF7B5D835E067D79776829D26C6E2E5AE46
candidate SHA-256: E4DCC14C4BEDE9DB6B8C3055BBAFCBF7B5D835E067D79776829D26C6E2E5AE46
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_007_packet_v1.py --source-id expanded_train:61970 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:61973
original SHA-256: B1FF9335081021A26993E5E56F769CD699E900AE91F88FE260F51338BBE2FA90
candidate SHA-256: B1FF9335081021A26993E5E56F769CD699E900AE91F88FE260F51338BBE2FA90
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_007_packet_v1.py --source-id expanded_train:61973 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:62206
original SHA-256: 22D68A05D41EC70E66BF8D0FB16A943DF6AE444F277B436A09424140C06623A4
candidate SHA-256: A15A4351A5B2CC9DE4FC407C0CF0FA4661535A09DBFAF64829137CB32FFE187A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

