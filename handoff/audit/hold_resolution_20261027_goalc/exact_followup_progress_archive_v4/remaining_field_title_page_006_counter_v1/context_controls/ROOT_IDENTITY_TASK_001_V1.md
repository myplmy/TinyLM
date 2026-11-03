# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:71339
original SHA-256: 69BFDCE0F74A7A45D567383EDB203EE8223170A1B275ADEB203C836EA0EA2F65
candidate SHA-256: 86613089F83243E2C595567B54C0ADF8497D1DD5E1183E16E5E3849DC9D120EC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:71716
original SHA-256: 260A6EF6F685DAB2F6446E0CF264B42BC3FDEA9898AF45488E73D09D80369E9B
candidate SHA-256: 260A6EF6F685DAB2F6446E0CF264B42BC3FDEA9898AF45488E73D09D80369E9B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_006_packet_v1.py --source-id expanded_train:71716 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:71908
original SHA-256: 8A23588B48AC29D5DC7A68D9647CD0C93763E89414932E254FC746527101BF9F
candidate SHA-256: 8A23588B48AC29D5DC7A68D9647CD0C93763E89414932E254FC746527101BF9F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_006_packet_v1.py --source-id expanded_train:71908 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:72068
original SHA-256: 9B5F30EB258AEAB94D89FD5AF50134852686345F571C9743361633186ECFAD48
candidate SHA-256: EBB5D6DFC008F6B9A90FC947653DAB96038274CDA0F380BD2B2B69E735D6CFD2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:72109
original SHA-256: B4097D4763038D83CD9933F39D4DB7A3FE5DB5604EB87FF0E56B5CC4570E06D2
candidate SHA-256: 38EC0C0A29CD551204A8E9F394C797DA065A9ADC3F2FA4469309789A7B133EB8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

