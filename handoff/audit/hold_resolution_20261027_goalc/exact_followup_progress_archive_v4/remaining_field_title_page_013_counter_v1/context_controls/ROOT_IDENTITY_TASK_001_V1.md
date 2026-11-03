# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:271450
original SHA-256: 3EBDFC878EABA6016DE8B0D3BEECFF068AED84797A23777CCD14FC5810F139C7
candidate SHA-256: 3EBDFC878EABA6016DE8B0D3BEECFF068AED84797A23777CCD14FC5810F139C7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_013_packet_v1.py --source-id expanded_train:271450 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:271856
original SHA-256: 3B1B542374A50A868F7EF08DD0A53318D17F12891E2940A319CDCA0D9730B943
candidate SHA-256: FBD27B26F48E2BF497E3B09BA8832B87D02C7928D147604506FF1DADD907B990
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:272236
original SHA-256: 25D2E2119F7AC2E7786179EC4122DB3978C63002BFE798AF383FFBC572BF07DC
candidate SHA-256: E622029F8AF3D0BB5BDBD12FBCFD23D5AF244D114E1FFB757FB218D6CD179680
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:273826
original SHA-256: 6B4FE02DC89AF05B83F2B1B1F4FDA3D551099FCF33FC157380AA16697159D7E0
candidate SHA-256: 9838E2A5A73D0A455C0C7E17478014BBCD56CAC6A3C92CA5B60F5EFB04CF0C80
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:274253
original SHA-256: CF2799CD35170EB7E74E0C6CCCFE5F3525C46ADE57719364BF831F54A6582B63
candidate SHA-256: 1DA8BED670AC28E6CAADD5A1E5D3B95E8ECCD06DAEAD7A8B721618B3AA6BD768
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

