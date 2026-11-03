# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:103795
original SHA-256: 95BB1E2BDD6D90CED6C3A854B02ADFEB5744399947EC7E7BC0B8291F18F6E516
candidate SHA-256: 95BB1E2BDD6D90CED6C3A854B02ADFEB5744399947EC7E7BC0B8291F18F6E516
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_011_packet_v1.py --source-id expanded_train:103795 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:103802
original SHA-256: 1ECD4F69D1E7C33B6EC586332E38DC5C390125BEDB70B34C0F34B2BEEC99094C
candidate SHA-256: 1ECD4F69D1E7C33B6EC586332E38DC5C390125BEDB70B34C0F34B2BEEC99094C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_011_packet_v1.py --source-id expanded_train:103802 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:103809
original SHA-256: DA335D1C1790D422FBDFADA44048C08068CFAD835B352444556549C2934ACC6F
candidate SHA-256: DA335D1C1790D422FBDFADA44048C08068CFAD835B352444556549C2934ACC6F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_011_packet_v1.py --source-id expanded_train:103809 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:103825
original SHA-256: 4CB7417AB69530BC64A5993476A241FE5B8D72E671E959503B3DD46156A1C2BC
candidate SHA-256: 13B26D57DB3A649033BD2F939D9E9351ABF16892622B34AF89F5AA55653645E2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:103872
original SHA-256: 58445D4FC7E92EBEBBA80D639D64936FE6310BF27AE87F2776646177CF107DC7
candidate SHA-256: 9FB3DBAD17EFAD930AABAD504A254F5E3F6E8B4F57C63D7E17FD66401933001A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

