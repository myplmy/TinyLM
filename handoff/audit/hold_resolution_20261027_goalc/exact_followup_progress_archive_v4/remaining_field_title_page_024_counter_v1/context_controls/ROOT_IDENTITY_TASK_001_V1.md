# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:736038
original SHA-256: 996654C32ED016383FF5BAC4ACAE5CBA43967B0F07F66D75C5AC7DCABEF4B073
candidate SHA-256: 71D1902A5180B78910168515812AA4BE374EF37779DBB588D621B2554A27CE57
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:736317
original SHA-256: 9A50C25183883E67292D20C2168525CDE33B710DE9C93B3818050FB456D84523
candidate SHA-256: 9A50C25183883E67292D20C2168525CDE33B710DE9C93B3818050FB456D84523
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_024_packet_v1.py --source-id expanded_train:736317 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:736553
original SHA-256: 225A850ADC8F74A3A0C02098DAE8377AA654A85F7CA2B82B463860041BAEFC89
candidate SHA-256: BC3D277E04BD2757D78F8C22FF018E86B55BBCCDF84B3A8429FF515586DC7CD5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:736640
original SHA-256: FFCB6A7CA06308A15E21AEE2D0E9E0C63302BF99EB381C1A7CBE3601AEC41E4F
candidate SHA-256: 453BD85372F8AA075BB0CA454E0272FEF09B727C74235170AD300996D9B6D6C4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:737135
original SHA-256: BE056DCD49031DE4A597D20895654BD88A5AACE12D4C455EAF7C66B2DC9BBE2D
candidate SHA-256: 943B4D895470978A8DC12471E07949BBF3D16E0E7286C283B717E4B46C8E0B67
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

