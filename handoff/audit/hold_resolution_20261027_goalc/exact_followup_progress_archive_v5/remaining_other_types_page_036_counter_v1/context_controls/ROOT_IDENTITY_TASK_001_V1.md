# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:431276
original SHA-256: D22286B2F045E2A063C4598396C315DCE27CFF1F87C8564706258843FFA532FC
candidate SHA-256: 98A51CABF1968F87F2B0A9B08DF20F040314C362EB1BE30A2B3E2383771C4913
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:431307
original SHA-256: EA507CB8C439DCC3138125378D0102A1027D2D357D60B5A004A43BADFB7496E2
candidate SHA-256: D0AE4CC3CBAF27F8251DA5530475B8DDE6E8DA14BA3FBAA1C850A46E4F469C0C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:431437
original SHA-256: B8FABAE69947537C0C1B3C230901E91ABB8ECCC68D642A1016799152E0598202
candidate SHA-256: B8FABAE69947537C0C1B3C230901E91ABB8ECCC68D642A1016799152E0598202
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_036_packet_v1.py --source-id expanded_train:431437 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_036_packet_v1.py --source-id expanded_train:431437 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_036_packet_v1.py --source-id expanded_train:431437 --packet 3 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:431469
original SHA-256: 43FBFC877222BD8F12C0AA10564C1357C9F0FB7093640A71AB0843AFB4DF0653
candidate SHA-256: 43FBFC877222BD8F12C0AA10564C1357C9F0FB7093640A71AB0843AFB4DF0653
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_036_packet_v1.py --source-id expanded_train:431469 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:431625
original SHA-256: 59B0E7A694A86BC8F0E48E55F0880480B2F6FB2B57CE2C3B97011EBF2F858D5E
candidate SHA-256: 2A1028F4FF6271A2B2C6B3A6077854D72DBB45C95B3B64CCC95F85851222585F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

