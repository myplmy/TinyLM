# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1219521
original SHA-256: 923387195A11A297EF6021CF3E0A2CD125331CAA9798153B1916C9A90FEBDA43
candidate SHA-256: 49515E16CF2585A9BF5B29CA68918C17DFE05EE423981517B11C51D1570856B3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1219805
original SHA-256: 48DB280C07B9611ED30031C67BBC7F656C2F31A96644292285272E14A60F44DD
candidate SHA-256: 820E18E375374CCD6D9748F0DA7FDEA393D6D6A74996F7DFE35C84EF4541762E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1220076
original SHA-256: A520714E60B058D1A2A09C08D8B538FEFB96570E0B2B222A8F5D918E255C0825
candidate SHA-256: 1E812C20D72FA36F912BD60C3F19937705D5D292CB9DBBD955AAD0E46F1C0003
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1220183
original SHA-256: 3DA8581CB540D047C5E7F1B2F2173FDEADB38E021E54FDF2602CCCB8B9F106BC
candidate SHA-256: 5E16E0F60E5DD2513F3F557087D58A7EF96E9F0496429F712E5781A124B7DF31
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1220963
original SHA-256: 793F868FDCBE4BFDDFDD8A90F24E580E53AB408DB53AE6C83F6B0C934806A3FC
candidate SHA-256: 793F868FDCBE4BFDDFDD8A90F24E580E53AB408DB53AE6C83F6B0C934806A3FC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_087_packet_v1.py --source-id expanded_train:1220963 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

