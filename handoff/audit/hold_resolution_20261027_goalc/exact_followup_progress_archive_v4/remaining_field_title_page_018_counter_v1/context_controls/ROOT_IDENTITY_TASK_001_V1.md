# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:485857
original SHA-256: 8942D0B5D23CD1C9D6D8B157F7C040333A5CF5304B2427F6B5DB39E98C48645E
candidate SHA-256: 8D1BD9A8DC2AE9D3E49433BFC16EEEFB442DA397EFBCA8B83FEC3173F5A4B394
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:485900
original SHA-256: D35A12478DBDC7493C647F2D91B878350489B4E2C6EA02A8298D0B5144EB5083
candidate SHA-256: 2549152CA66C35875BAE2B641A4F193DE4295679B606DBB58DB505C73C930EC5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:486095
original SHA-256: 6835AB8505E6F3CE0ED6BEBBA3BD93F1A78F562F28AC229F2CFF4594B9470697
candidate SHA-256: 964AD6902C0316B4E0F6B7FBC9776CBC3D0CEA3DF4336A7575DC9A6E7332EC3A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:486327
original SHA-256: A486D6BF0B97DBD5F83757A3DF42F33F0F5DE39EF2493FA081EB96E53C1DAEE4
candidate SHA-256: C85CD5F72DEEE1091E666A3D7B8C6D83ABE8BA7E1DD2E3361EB987C1E8B05384
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:486432
original SHA-256: B43F20D55453C97A1BD7E957E2BD7341F541DFE785184B450909D0FB5C0FE788
candidate SHA-256: B43F20D55453C97A1BD7E957E2BD7341F541DFE785184B450909D0FB5C0FE788
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_018_packet_v1.py --source-id expanded_train:486432 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_018_packet_v1.py --source-id expanded_train:486432 --packet 2 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

