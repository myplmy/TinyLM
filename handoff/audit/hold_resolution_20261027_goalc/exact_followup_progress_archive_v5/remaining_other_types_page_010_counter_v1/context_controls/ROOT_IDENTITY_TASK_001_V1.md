# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:100055
original SHA-256: 12DF5D977E242B66AA626801FE3A566C3034E42ADA60339AA4E1CEF4CC19257A
candidate SHA-256: 9FB7F596E4C1DD896337686013FA4BD57E648D676BD4CF2E2E087AA8B379F142
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:100198
original SHA-256: 4138EAFEA727D64CE0CB3B5756237BB974B38DE95F27F22480F52742AB435D1F
candidate SHA-256: C3A6D62FCACDC047C9FC28DF11BD0D8A16F40C37FA54DF7CD3F4C704EBA70EDF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:100505
original SHA-256: 28EA019986FB525DA084AB4C763CCF165BDAAD6D76FF8DD0984E1AB5C6C61139
candidate SHA-256: 6E83905080F0DEA9E1225A6C2A0AA70333937B685A1CAFA41E0483D1A13C6CAF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:100595
original SHA-256: 99717E492C24705418533AA7C271AFDA6389D2BC7EB7567FA853687A2B35A846
candidate SHA-256: 99717E492C24705418533AA7C271AFDA6389D2BC7EB7567FA853687A2B35A846
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_010_packet_v1.py --source-id expanded_train:100595 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:100791
original SHA-256: 142892AD8854FF0D95309BF5F899F87A418509092F0127D7EBB062D36D1256B5
candidate SHA-256: F671A1BD11C210DC8DBB3C5B97B325140C8B33F02C9D3E8FFBDB582A56B3C383
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

