# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1086436
original SHA-256: DA40951DAF4D660C84688DD1CA205F46E6B97265F3B7B3EC8E6ECD75338F6016
candidate SHA-256: DA40951DAF4D660C84688DD1CA205F46E6B97265F3B7B3EC8E6ECD75338F6016
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_079_packet_v1.py --source-id expanded_train:1086436 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_079_packet_v1.py --source-id expanded_train:1086436 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_079_packet_v1.py --source-id expanded_train:1086436 --packet 3 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1086685
original SHA-256: C066685742D6A73A91DCB712B11E0E46AA60FCC4116B4D243C1BB91CE4897A9A
candidate SHA-256: 3ACBF81E08766C33F675DEDDB132F7297ACDC23DA7F979895E3BD135B9F40230
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1087069
original SHA-256: 7FFCABF4894F39A9F03FE652C6E8BFBDFE328DB83408C55E13E40FBBC44F94DC
candidate SHA-256: 51CD1C21B9DD8FD995C8590C2D39C36F6525269A810FF772883440029B7E864A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1087107
original SHA-256: 56A05EC08B71D7EB439DF7AF78F1228674CCB2ADF51F127DDEF5DA938CD4B30E
candidate SHA-256: D931792A5C0AB49B1E4973EE11EC7EC9CDE8AD0E221A51CD12E2C13B40A1C021
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1087204
original SHA-256: 6D0926F4EFC4AE39324D5744716AAE9340A72D4F5482D9B514749D9D6BD26518
candidate SHA-256: 6D0926F4EFC4AE39324D5744716AAE9340A72D4F5482D9B514749D9D6BD26518
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_079_packet_v1.py --source-id expanded_train:1087204 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_079_packet_v1.py --source-id expanded_train:1087204 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_079_packet_v1.py --source-id expanded_train:1087204 --packet 4 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

