# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:546653
original SHA-256: F8B13D6E678BFEC9ADD863FE694E2C5F644414A2194AFCDAB2CFBB7A592D0527
candidate SHA-256: BE9463624EF17935A94944E9E101A99DA5FDFAFD52A7D309DCEF85331120B5C1
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:546761
original SHA-256: F546F1EBE4F1BB5CDC78EF9218388A5597F9D334438EE3704F5FF877830D5AF0
candidate SHA-256: E7BFEEC67B345FED963395A223AA481E27CF202C75A5F289F4184C1629795CC5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:546982
original SHA-256: 75EDAC053D1CE74CDA4C14F0E2482BFBA4CB4D27EB7C7DD96119E068943E1591
candidate SHA-256: 061313F87E025BA45E5A7E42AF6F85BF49DBD658A2A439F54FD25FD0A506DD56
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:547203
original SHA-256: BDC66528333CB56ED8B34AC49C43B36D0BADDB3CDDD8606C6B168C688A3A8C26
candidate SHA-256: 98C2ECF0BAEC214555B3AB12C62B5A3EBE9134F9D82B81275F63BD555CA8740B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:547329
original SHA-256: C8830510B6A171C7870944B993975A772B54C5F4F5E9A57FB3FA1A1005671FA5
candidate SHA-256: C8830510B6A171C7870944B993975A772B54C5F4F5E9A57FB3FA1A1005671FA5
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_044_packet_v1.py --source-id expanded_train:547329 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

