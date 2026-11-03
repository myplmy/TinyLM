# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:100349
original SHA-256: 2C873BBC95D46D64455183F5DD926F7B4CF4CD42AA42E9DC3FB2EECE694B931A
candidate SHA-256: 2C873BBC95D46D64455183F5DD926F7B4CF4CD42AA42E9DC3FB2EECE694B931A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_007_packet_v1.py --source-id expanded_train:100349 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_007_packet_v1.py --source-id expanded_train:100349 --packet 2 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:101096
original SHA-256: 8F4A82B6C3F1E54556FB8C5E38AA9999FA8FC6D0AB96C90C933BF3747838D2B8
candidate SHA-256: 8F4A82B6C3F1E54556FB8C5E38AA9999FA8FC6D0AB96C90C933BF3747838D2B8
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_007_packet_v1.py --source-id expanded_train:101096 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:102080
original SHA-256: 630D872280A18406F4CE74DD2F46B6792867CF38899973108976DB234766057B
candidate SHA-256: 8CFB13DF36E3E65FB0B338DB8458D521B0A15A96E1124E71346F4F8A51985FF5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:102404
original SHA-256: 7DE147CCD207D2F1A60D05918507B1BB3F56F2D3FE898B35D65CC292B77969BB
candidate SHA-256: EE06B5763AFF4C968CD16A14D25E2695C0BBA07E07F2BE4FC3CC59F6D64E3863
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:102421
original SHA-256: 854D7496B39365F49376990C272D9ECFF566828A8C2E27D905538A530FA61396
candidate SHA-256: E69115CEECE3D9909AF084CC9E881B84716F879562615495C1AA656B65703D7F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

