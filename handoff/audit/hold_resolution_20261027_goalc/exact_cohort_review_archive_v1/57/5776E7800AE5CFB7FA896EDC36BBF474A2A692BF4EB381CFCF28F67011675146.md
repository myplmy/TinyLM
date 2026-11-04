# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:241084
original SHA-256: D6CC58F0A9594BF0CB2E4D0D30835DF979CE567BACE1D22A21D3E6194800DE4C
candidate SHA-256: F1D4AD577C3A48D3E4BC86A514D806AA7AA4F49E0042D37AF29A3512C80E5EA3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:241317
original SHA-256: 0C0CA0C868492A7A24F3C3AF56FE217BE7BFBA4083E08974838BF403DEA40F6B
candidate SHA-256: 0C0CA0C868492A7A24F3C3AF56FE217BE7BFBA4083E08974838BF403DEA40F6B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_012_packet_v1.py --source-id expanded_train:241317 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_012_packet_v1.py --source-id expanded_train:241317 --packet 2 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:243234
original SHA-256: 6EF359DF1A03151999AD247AAC6AF262093DC97366B7E35C91B12892DDEA446F
candidate SHA-256: 6EF359DF1A03151999AD247AAC6AF262093DC97366B7E35C91B12892DDEA446F
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_012_packet_v1.py --source-id expanded_train:243234 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_012_packet_v1.py --source-id expanded_train:243234 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_012_packet_v1.py --source-id expanded_train:243234 --packet 3 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:244048
original SHA-256: 41D8AB42CF819FE7301FEFD6B2E8A90EC9904FC7CD2950450EFF546B58C59FE1
candidate SHA-256: 14E04770360297B99F5C43E618AD6644CDD2020626DE8811906AAF3B2A96547B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:244095
original SHA-256: 28E43DB6F537661383E4DFC85C3CA17F3A1B81E0876250DC2E530F8A78C63BC4
candidate SHA-256: 28E43DB6F537661383E4DFC85C3CA17F3A1B81E0876250DC2E530F8A78C63BC4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_012_packet_v1.py --source-id expanded_train:244095 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

