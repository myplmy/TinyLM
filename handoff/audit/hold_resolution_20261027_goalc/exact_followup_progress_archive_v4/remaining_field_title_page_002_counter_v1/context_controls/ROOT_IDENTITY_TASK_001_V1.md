# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:10301
original SHA-256: 2A077F31ECCDC70E8AA061FAD4FA2F889166366D38CAD8FEC2CC61BCAC773B12
candidate SHA-256: 308EE65D4B8499B50D5395E10EC95239C026415881C6F297B4EB28D1BAF6D1DB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10307
original SHA-256: A83422B94A6CC6012A3B21A44591EC1146A0F3D6FE63C316B9A7F82B149F5B8E
candidate SHA-256: 2440FBA4438A9190EE3F2DCC6531866785FF0CD853E1DA5977E3B826BFE2CBE5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10566
original SHA-256: 51F0F1E7DB10020FF709B1DBF338E381E075C1DEFC35B0DBA9720E9AF594A9ED
candidate SHA-256: 51F0F1E7DB10020FF709B1DBF338E381E075C1DEFC35B0DBA9720E9AF594A9ED
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_002_packet_v1.py --source-id expanded_train:10566 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:11255
original SHA-256: 32E7A607F330249E89E5B64D9054B9D2FF1F7583EDBE13A91975C8245671E7AA
candidate SHA-256: 32E7A607F330249E89E5B64D9054B9D2FF1F7583EDBE13A91975C8245671E7AA
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_002_packet_v1.py --source-id expanded_train:11255 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_002_packet_v1.py --source-id expanded_train:11255 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_002_packet_v1.py --source-id expanded_train:11255 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_002_packet_v1.py --source-id expanded_train:11255 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_002_packet_v1.py --source-id expanded_train:11255 --packet 8 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:11363
original SHA-256: DE0D6BB41731E36A1005252ADCE1E08C80C1E72BB83B198E13B5D95C5AB12D0A
candidate SHA-256: 47E7243A5B27D338A129284AEC83E55F860506CC92A7F2F05E379507B2A27657
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

