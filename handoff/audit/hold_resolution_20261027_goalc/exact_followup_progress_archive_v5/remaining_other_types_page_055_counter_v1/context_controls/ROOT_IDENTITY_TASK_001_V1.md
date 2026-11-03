# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:703551
original SHA-256: 781D6F30C85CF721D46FD778F78A4A9E62E3B54EF5A4D7D0466DA6FE32107432
candidate SHA-256: 781D6F30C85CF721D46FD778F78A4A9E62E3B54EF5A4D7D0466DA6FE32107432
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703551 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703551 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703551 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703551 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703551 --packet 7 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:703579
original SHA-256: F27BC8D230806AC3A5F42F9164D9188DD61E818316450BF571055252D00406C2
candidate SHA-256: F27BC8D230806AC3A5F42F9164D9188DD61E818316450BF571055252D00406C2
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703579 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703579 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703579 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703579 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703579 --packet 5 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703579 --packet 6 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703579 --packet 12 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:703587
original SHA-256: 96930D3D911482A10EEF7F67597DCB13E2B9939B6EF19748FDF9B0AA420F0C0F
candidate SHA-256: 96930D3D911482A10EEF7F67597DCB13E2B9939B6EF19748FDF9B0AA420F0C0F
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703587 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703587 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703587 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703587 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703587 --packet 5 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:703587 --packet 10 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:704329
original SHA-256: 88A7F2652E412D0BD87A27925F1E581AE742185ACED5CA10EC249C6AE7905D64
candidate SHA-256: 65E2FE0C5E5E51A7F0299E5C504D4786E6334DB18092DDA4155DF0907F9BA3F3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:704372
original SHA-256: 05E5131FCE7FF7A30FF70DFD41D7BC0CE4A49DA7917251AA05A20286CC6F89D9
candidate SHA-256: 05E5131FCE7FF7A30FF70DFD41D7BC0CE4A49DA7917251AA05A20286CC6F89D9
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:704372 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:704372 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_055_packet_v1.py --source-id expanded_train:704372 --packet 3 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

