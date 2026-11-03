# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:828622
original SHA-256: E116B65684F71191AD48D8D2F1265AB93C0BCF136A4D84780DCE67D43D6BACE5
candidate SHA-256: E116B65684F71191AD48D8D2F1265AB93C0BCF136A4D84780DCE67D43D6BACE5
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_064_packet_v1.py --source-id expanded_train:828622 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:828709
original SHA-256: 1C8B7830FFB079162B04FECAFA111BA8039C944E99503F2D8F029930FC5A5DEF
candidate SHA-256: 5DE3899E721BE386B88DFB71AB1F7E978F9AE3558F4D39C68DC04C6157E678BC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:828807
original SHA-256: 3611BB394ECC98402E0ACF370353D8102EC9AF817E31E08F4C529426F307FB83
candidate SHA-256: D8B9B1EE7EB424CD51CE6ACB008DC2B6448EB1D93C6FA78D4E315EFF9DC139CB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:828810
original SHA-256: 1967B3AD1FDF94EB5F0268ECE9ACB00A1F493F234AB524423BC731CE76FB6DDF
candidate SHA-256: D53C14436B7B252C930FF9885DAE3FC2C1CCB98E4AB0DD9FCE2956DF1F5F9E33
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:828880
original SHA-256: 38F03629C2257E57B985537C09F799C4E1844719496D8A0F88AEF6FC37671F21
candidate SHA-256: E1994AA89DA3E15268212C069B40EC5C7BBF91FD057C2F8EE7E3E28796E091A7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

