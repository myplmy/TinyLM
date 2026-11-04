# 정확 입력 전문 판독 연결 TASK_016

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:298574
original SHA-256: 3B573C97439F219EA474B36741B9E4A2A6ED2E3DB6203BC3B0D7E246D83BEE03
candidate SHA-256: 3B573C97439F219EA474B36741B9E4A2A6ED2E3DB6203BC3B0D7E246D83BEE03
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_013_counter_v1/reading_packets_v1/expanded_train_298574_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:298976
original SHA-256: FA28FC4383F2286F0F027CA734C1A4ED394F6FCDC7D601288DE2084B70CDC01A
candidate SHA-256: 42109FC59A9F3C62946DE63AA3DB7293541BE7860FDB6407B0E85717807FECDA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:300211
original SHA-256: 984B29EC41224A1743FBFCF75A17FBFF201DB9122167857E57B03EC87D9B2A1E
candidate SHA-256: 984B29EC41224A1743FBFCF75A17FBFF201DB9122167857E57B03EC87D9B2A1E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_013_counter_v1/reading_packets_v1/expanded_train_300211_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:300253
original SHA-256: D1606873AC189E1FFDB3C5A42C880389163318AD60928226E45CA2A4444F0F90
candidate SHA-256: 1D028C93BCC817ACCC24D49359CDEF3BF03513CFE298E986EB7EEE72AC02467B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:300339
original SHA-256: DAD8D6F1161775CF61330FF6DCB6EAB32623209AD7E0CFD697D69E02EDB620A5
candidate SHA-256: D2238E2F77694E5DB8BE2A7D3911AF46C95401761B89BE1015E574DB3F51FDBB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

