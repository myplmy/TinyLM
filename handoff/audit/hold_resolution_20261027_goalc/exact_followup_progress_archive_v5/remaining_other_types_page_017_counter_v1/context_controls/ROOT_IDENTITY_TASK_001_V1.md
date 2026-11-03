# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:174998
original SHA-256: 0D2FE09B5DA7648F5460702D87252F25C8AAFBB6E27CA41033E7FA59FDEFA99B
candidate SHA-256: 0D2FE09B5DA7648F5460702D87252F25C8AAFBB6E27CA41033E7FA59FDEFA99B
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_017_packet_v1.py --source-id expanded_train:174998 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_017_packet_v1.py --source-id expanded_train:174998 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_017_packet_v1.py --source-id expanded_train:174998 --packet 3 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:175276
original SHA-256: C28270892C48803E7D2A23F8416C4D2E063740441862491B060205F8F44ADEB7
candidate SHA-256: BD1ED1FE1D423EBBD538CC6BF2AAF379D1CA53331C75DFD89F154496ADC0C3AA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:175352
original SHA-256: 26DF3BCBB34CC6389620BBCBCE8AB963C62247557A4286F0F63845982F0F256B
candidate SHA-256: 0012010F274E34AFC0C64405ED41B6187A343CA39D97B03F2101CDC327A1E293
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:175746
original SHA-256: 16838F001A27F0CE446BBC663CA2E130E2600DBE84EA00B95C89990CA4EDEBF5
candidate SHA-256: 16838F001A27F0CE446BBC663CA2E130E2600DBE84EA00B95C89990CA4EDEBF5
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_017_packet_v1.py --source-id expanded_train:175746 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_017_packet_v1.py --source-id expanded_train:175746 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_017_packet_v1.py --source-id expanded_train:175746 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_017_packet_v1.py --source-id expanded_train:175746 --packet 5 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:176097
original SHA-256: ED332F6D7FCE8596A2EB6BDCF4102A00C15EADF5BF84190618CF9F04A41F5D05
candidate SHA-256: E0B9D3636031D8C1D995DB82D9679A695A4625BB03274D579D449156544A1B04
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

