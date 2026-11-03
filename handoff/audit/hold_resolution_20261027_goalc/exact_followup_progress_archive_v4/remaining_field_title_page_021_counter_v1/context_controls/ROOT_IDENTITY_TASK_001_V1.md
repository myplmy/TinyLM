# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:619468
original SHA-256: 798511349109F2BBFC4AB07EAC9512182E48FA33EEF5190E2693FE95C651D7A2
candidate SHA-256: 12F53C5F8F3C8541EC4E0B17E3387EB33ACD6C1BC92487ACED5E1C5E353585D0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:619536
original SHA-256: 864AF57C2105996173689BD5725D826BB58AEE460BF986AED1BBAB334E846208
candidate SHA-256: 994F94E931B71ED3219F0DBB4EDE1438E9AA39A50C795441872C51A044A7EF6F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:619611
original SHA-256: 3D64CDFFF6B8005C06F14A229031991D8D124F3F6414BE8539FEF902C43270F8
candidate SHA-256: F09DF14A242EE3E723A7052D64837BD2090806CA38AF6315E25BB43A46AB0760
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:619663
original SHA-256: 45A3791AD9B1F2D3AB178C62277F8AC8237A44BC12DD3246DFB95C57507FB1CA
candidate SHA-256: 45A3791AD9B1F2D3AB178C62277F8AC8237A44BC12DD3246DFB95C57507FB1CA
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_021_packet_v1.py --source-id expanded_train:619663 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:619911
original SHA-256: EB76EC8A6AB550692C7B41C3735D55A7B29FC506C248754545C6E57BA7124C11
candidate SHA-256: EB76EC8A6AB550692C7B41C3735D55A7B29FC506C248754545C6E57BA7124C11
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_021_packet_v1.py --source-id expanded_train:619911 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

