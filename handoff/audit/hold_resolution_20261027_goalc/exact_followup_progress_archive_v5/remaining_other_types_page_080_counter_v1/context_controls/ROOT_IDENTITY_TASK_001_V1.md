# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1101772
original SHA-256: DCCF67E185079F4206BB5D24B2D292717E600567D4F921EB6F31650F4B29867A
candidate SHA-256: CF7F41D721013A364A86ACBE8AC80671E4700CBE0601C1682A9DECF6393EA4F4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1102055
original SHA-256: B27075BA22631F95229376D9CD214B2E01DBB3F008BFED73CC3A32512FF48EFC
candidate SHA-256: C305F83C8FDF970EE91A4D4F0D78C461D12C5094F2A662D9C54CA5DDE59427E3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1102151
original SHA-256: 40AB1B78FFEA6092C4E9D285DFAB798EE64B6DA36437A55A42FCA6301F6A003D
candidate SHA-256: 40AB1B78FFEA6092C4E9D285DFAB798EE64B6DA36437A55A42FCA6301F6A003D
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_080_packet_v1.py --source-id expanded_train:1102151 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1102533
original SHA-256: 75462B7B0EF548BA14D26E9EF05BE946DFDED1D986D87B462084DDF4DF08D3CE
candidate SHA-256: 75462B7B0EF548BA14D26E9EF05BE946DFDED1D986D87B462084DDF4DF08D3CE
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_080_packet_v1.py --source-id expanded_train:1102533 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_080_packet_v1.py --source-id expanded_train:1102533 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_080_packet_v1.py --source-id expanded_train:1102533 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_080_packet_v1.py --source-id expanded_train:1102533 --packet 5 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1102704
original SHA-256: 662FD5DF185A257481D4FABC7AE3EBDD9589848993F1435F8D2ECF34B4CBBAAF
candidate SHA-256: EEE58CF42E9FBD6F96582C7BCBE1DE59162359679171B97E85C58B2817DCC933
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

