# 동일 입력 판독 연결: TASK_002

총괄이 실제 원문/후보 바이트·SHA와 순서 패킷 전체를 검산한 추가 계획이다.
아래 동일성 증명이 있는 ID만 적용한다. 원문 전문은 첫 문자부터 실제 END까지 실제 읽고,
candidate는 정확 바이트 동일성으로 연결하며 full_diff 프레임의 끝까지 읽는다.
이를 원문/후보 두 번의 독립 판독으로 기록하지 않는다. 새 수정 TXT는 전문 재열람과 전체 diff를 계속 확인한다.
TASK의 모든 ID는 각각 리뷰에 포함한다. READING_VIEWS는 경로 인덱스이며 전체 인덱스 EOF의 반복 판독은 불필요하다.
서로 다른 후보는 기존 전문/후보/전체diff와 모든 패킷을 그대로 읽는다.
기존 허용·금지·보호 경계와 다른 역할 접근 금지는 유지한다.
controls는 아래 정확 고정 reader 명령만 사용한다. 다른 역할은 아래 정확 cat 경로를 쓴다.

## expanded_train:1030334
original SHA-256: 3C0058EF1A6471D4E4EE290DA2543FCDAEFDB0CD6930F3B168346900D2A0676F
candidate SHA-256: 3C0058EF1A6471D4E4EE290DA2543FCDAEFDB0CD6930F3B168346900D2A0676F
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 3]
full_diff 프레임 패킷: [6, 6]
중복 후보만 포함해 생략 가능한 패킷: [4, 5]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1030334 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1030334 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1030334 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1030334 --packet 6 --piece 1
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1031252
original SHA-256: 6ED8B756D2FC7644A75B866EFC052CBBF2406C41B71E9986741A5BE5379406AF
candidate SHA-256: 6ED8B756D2FC7644A75B866EFC052CBBF2406C41B71E9986741A5BE5379406AF
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 3]
full_diff 프레임 패킷: [6, 6]
중복 후보만 포함해 생략 가능한 패킷: [4, 5]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1031252 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1031252 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1031252 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1031252 --packet 6 --piece 1
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1032552
original SHA-256: 4032917D03B362112CCC56D83CAC0A6B2DFCE68A7AA9897AA05852993D1A84EC
candidate SHA-256: 4032917D03B362112CCC56D83CAC0A6B2DFCE68A7AA9897AA05852993D1A84EC
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 1]
full_diff 프레임 패킷: [1, 1]
중복 후보만 포함해 생략 가능한 패킷: []
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1032552 --packet 1 --piece 1
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1038246
original SHA-256: AF5BA528B7B8C54EB2BF840E9747DA57EA94539F11582162AED8D56826F11F1D
candidate SHA-256: AF5BA528B7B8C54EB2BF840E9747DA57EA94539F11582162AED8D56826F11F1D
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 6]
full_diff 프레임 패킷: [12, 12]
중복 후보만 포함해 생략 가능한 패킷: [7, 8, 9, 10, 11]
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1038246 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1038246 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1038246 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1038246 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1038246 --packet 5 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1038246 --packet 6 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1038246 --packet 12 --piece 1
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

## expanded_train:1041401
original SHA-256: 66B5882BC74F16F77F6FF4A0891A0BC5D5A0FC8A195B30633100257DC13FD7AF
candidate SHA-256: 66B5882BC74F16F77F6FF4A0891A0BC5D5A0FC8A195B30633100257DC13FD7AF
실제 바이트 동일·모든 순서 패킷 재구성 일치.
원문 전문 프레임 패킷: [1, 2]
full_diff 프레임 패킷: [3, 3]
중복 후보만 포함해 생략 가능한 패킷: []
아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1041401 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1041401 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:1041401 --packet 3 --piece 1
```
리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.

