# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:212608
original SHA-256: E35B037BE020C00B65E3A68B371BAE332C639112660DB29F891FDA4FB994D60D
candidate SHA-256: D782A9544623BA9932CC4CFFD9D791E368F02F65254850FD1AE0B76105D7E7A4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:212658
original SHA-256: 66BDDC3FA698F9ECD3DEB643C56C16965F21A74957C5C037750D3AF0FB6C9A94
candidate SHA-256: 66BDDC3FA698F9ECD3DEB643C56C16965F21A74957C5C037750D3AF0FB6C9A94
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_011_counter_v1/reading_packets_v1/expanded_train_212658_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:213721
original SHA-256: 6CB65516DC17E24F7190DEF3924B5080E2B5205B41830100A0EE093694E27F08
candidate SHA-256: EF69082CD8255E16991626CC1F6836951ABC11EDD70B2FE3D6483E468B12235C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:213742
original SHA-256: 1265D8D9CDAB80A2C8677F3CD3E9E8A7A2253E4BD797195C90FDA15D8C57823C
candidate SHA-256: 760F9C5DC3154A51371ADE11EAA5F3FA24E927364E5DB7C5C0F1C447BB3FFFB6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:213873
original SHA-256: D9324BD556D3E984D95D2D46A0638128F9C4206CED3A4B531141E324141F8AE6
candidate SHA-256: 21BD2BB8D41DFEEB06E4C922D316C132F801CF960C8A5CC0ABFBBA6D27DC4C8F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

