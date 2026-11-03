# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:359222
original SHA-256: 19991291A4FA7EA06A882D3174B7F40F91E38611085E6DF10DDFA93B9D2B6CC4
candidate SHA-256: AE84DA677145E72D1A74971854ABE3B4D0D9B645ED32006EE2B1FE6FA200D569
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:359303
original SHA-256: A063D46C3AD02EDED26C7E3FEE157EFFCE3EE10005D084005E619F73FB5F39FC
candidate SHA-256: A063D46C3AD02EDED26C7E3FEE157EFFCE3EE10005D084005E619F73FB5F39FC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_031_counter_v1/reading_packets_v1/expanded_train_359303_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:359793
original SHA-256: 4B75A6A5EB6C5B6CF7E31805E58A72D8767C3CFE76C0ECE46DE5CA8FED7A3DF1
candidate SHA-256: 9CEB715504B2B5728CD74C340AC9DDA728403AE6CE0EBCAFC3DBFB4FDBC37098
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:359828
original SHA-256: 4FE880AE2F49338C569F34E2D484F75078E564ED34E942F91F2AC027A9597037
candidate SHA-256: 2671BA0FCDA885223D635EADE136DA4A59D58F6E16A1957CB903640CEAACC7C2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:359971
original SHA-256: 4ACF48BC59A239F9DADE89582B13F93D34F88F6EACB0A687728827013469E6CB
candidate SHA-256: 8B54E1D7325876D05B5F22F3EE7763B6058375001D4EF3979698A6AAD7F1D596
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

