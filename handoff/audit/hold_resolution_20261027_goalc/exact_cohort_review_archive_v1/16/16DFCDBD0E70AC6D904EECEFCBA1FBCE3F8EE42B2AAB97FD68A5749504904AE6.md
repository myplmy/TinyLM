# 정확 입력 전문 판독 연결 TASK_011

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:5363
original SHA-256: 139A77559272BCDE0517EED4790E2E9996FE7F4456B29C936E8FC4D2E230FA96
candidate SHA-256: E39B562D2A95F09B392C3269011EDD98FFA0EE3FC4C5637B669AFC2D50F8F218
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:5365
original SHA-256: 14FDCDEFE647E102C6C305ED62FEBFC4BCA356FEFD4C6EE4F42E639153727DD4
candidate SHA-256: 14FDCDEFE647E102C6C305ED62FEBFC4BCA356FEFD4C6EE4F42E639153727DD4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_5365_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:5374
original SHA-256: 8ED1BD158CB4B996334A2EB9FE03F8B8542D416BC06CA5A3C9B1F51F47DDDE1F
candidate SHA-256: C9774346237C1DB05609EED52852FF64F4E53616602A42E205BD3F0FC54D72F2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:5375
original SHA-256: 6AD32066EB2618A478F5B5045BEEB1746960D96974C84032EAC25E6C411CBF9D
candidate SHA-256: 66331FF3D1F6C06F12C984841680190A5FE0BA28D6BBEA967A33ADA0D06B4C4A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:5383
original SHA-256: 990603A9BD16843E8EFAB74FD0C62EFD36005CFE704215A834948EB705A739F7
candidate SHA-256: 990603A9BD16843E8EFAB74FD0C62EFD36005CFE704215A834948EB705A739F7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_5383_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

